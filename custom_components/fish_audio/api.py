"""Async client for the official Fish Audio API."""

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import AsyncGenerator, Mapping
import logging
from typing import Any

from aiohttp import (
    ClientConnectionError,
    ClientResponse,
    ClientSession,
    ClientTimeout,
    ClientWSTimeout,
    WSMsgType,
)
import async_timeout
import msgpack  # type: ignore[import-untyped]

from .const import (
    API_BASE_URL,
    API_WS_URL,
    CONF_AUDIO_FORMAT,
    CONF_LATENCY,
    CONF_LANGUAGE,
    CONF_MODEL,
    CONF_PITCH,
    CONF_SAMPLE_RATE,
    CONF_SPEED,
    CONF_VOICE,
    CONF_VOLUME,
    DEFAULT_AUDIO_FORMAT,
    DEFAULT_LATENCY,
    DEFAULT_LANGUAGE,
    DEFAULT_MODEL,
    DEFAULT_PITCH,
    DEFAULT_SAMPLE_RATE,
    DEFAULT_SPEED,
    DEFAULT_VOLUME,
    MAX_RETRIES,
    MP3_BITRATE,
    OPUS_BITRATE,
    RATE_LIMIT_REQUESTS,
    RATE_LIMIT_WINDOW,
    REQUEST_TIMEOUT,
    RETRY_BASE_DELAY,
    STREAM_TIMEOUT,
    SUPPORTED_LANGUAGES,
)
from .exceptions import (
    FishAudioAuthenticationError,
    FishAudioRateLimit,
    FishAudioServerError,
    FishAudioTimeout,
    FishAudioValidationError,
)
from .helpers import Voice, option_value

_LOGGER = logging.getLogger(__name__)


class FishAudioAPI:
    """Small production client for Fish Audio Cloud."""

    def __init__(
        self,
        session: ClientSession,
        api_key: str,
        *,
        base_url: str = API_BASE_URL,
    ) -> None:
        """Initialize the API client."""
        self._session = session
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._request_times: deque[float] = deque()
        self._rate_lock = asyncio.Lock()

    @property
    def user_agent(self) -> str:
        """Return a descriptive client identifier."""
        return "Home Assistant Fish Audio custom component"

    async def async_validate(self) -> str:
        """Validate the API key and return a stable account identifier."""
        _LOGGER.debug("Validating Fish Audio API key")
        data = await self._request_json("GET", "/wallet/self/api-credit")
        user_id = data.get("user_id") or data.get("_id")
        return str(user_id or "fish-audio-account")

    async def async_list_voices(
        self,
        *,
        self_only: bool = False,
        language: str | None = None,
        title: str | None = None,
        page_size: int = 50,
    ) -> list[Voice]:
        """List available Fish Audio voices."""
        params: dict[str, Any] = {
            "page_size": page_size,
            "page_number": 1,
            "sort_by": "task_count",
            "self": "true" if self_only else "false",
        }
        if language:
            params["language"] = language
        if title:
            params["title"] = title

        voices: list[Voice] = []
        while True:
            data = await self._request_json("GET", "/model", params=params)
            for item in data.get("items", []):
                voice_id = str(item.get("_id") or item.get("id") or "")
                if not voice_id:
                    continue
                languages = tuple(
                    str(lang) for lang in item.get("languages", []) if lang
                )
                voices.append(
                    Voice(
                        id=voice_id,
                        title=str(item.get("title") or voice_id),
                        languages=languages,
                        task_count=int(item.get("task_count") or 0),
                    )
                )
            if not data.get("has_more"):
                break
            params["page_number"] += 1
        _LOGGER.debug("Loaded %s Fish Audio voices", len(voices))
        return voices

    async def async_list_models(self) -> list[str]:
        """List supported TTS backend models."""
        return [DEFAULT_MODEL, "s1"]

    async def async_list_languages(self) -> list[str]:
        """List languages exposed to Home Assistant."""
        return SUPPORTED_LANGUAGES

    async def async_generate_audio(
        self,
        text: str,
        options: Mapping[str, Any],
    ) -> bytes:
        """Generate speech using the official HTTP TTS endpoint."""
        audio_format = str(
            option_value(options, CONF_AUDIO_FORMAT, DEFAULT_AUDIO_FORMAT)
        )
        model = str(option_value(options, CONF_MODEL, DEFAULT_MODEL))
        payload = self._tts_payload(text, options)
        _LOGGER.debug(
            "Generating Fish Audio TTS audio: model=%s voice=%s language=%s format=%s",
            model,
            payload.get("reference_id"),
            option_value(options, CONF_LANGUAGE, DEFAULT_LANGUAGE),
            audio_format,
        )
        return await self._request_bytes(
            "POST",
            "/v1/tts",
            headers={"model": model, "Content-Type": "application/json"},
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )

    async def async_stream_audio(
        self,
        message_gen: AsyncGenerator[str],
        options: Mapping[str, Any],
    ) -> AsyncGenerator[bytes]:
        """Stream TTS audio using Fish Audio's official WebSocket endpoint."""
        model = str(option_value(options, CONF_MODEL, DEFAULT_MODEL))
        payload = self._tts_payload("", options)
        headers = self._headers({"model": model})
        timeout = ClientWSTimeout(ws_receive=STREAM_TIMEOUT, ws_close=STREAM_TIMEOUT)
        await self._respect_rate_limit()
        _LOGGER.debug("Opening Fish Audio streaming TTS WebSocket")
        try:
            async with self._session.ws_connect(
                API_WS_URL,
                headers=headers,
                timeout=timeout,
                autoping=True,
            ) as ws:
                await ws.send_bytes(
                    msgpack.packb({"event": "start", "request": payload})
                )
                async for chunk in message_gen:
                    if chunk:
                        await ws.send_bytes(
                            msgpack.packb({"event": "text", "text": chunk})
                        )
                await ws.send_bytes(msgpack.packb({"event": "flush"}))
                await ws.send_bytes(msgpack.packb({"event": "stop"}))

                async with async_timeout.timeout(STREAM_TIMEOUT):
                    async for msg in ws:
                        if msg.type == WSMsgType.BINARY:
                            event = msgpack.unpackb(msg.data, raw=False)
                        elif msg.type == WSMsgType.TEXT:
                            event = msg.json()
                        elif msg.type in (WSMsgType.CLOSED, WSMsgType.CLOSE):
                            break
                        elif msg.type == WSMsgType.ERROR:
                            raise FishAudioServerError("Streaming connection failed")
                        else:
                            continue

                        event_type = event.get("event")
                        if event_type == "audio":
                            audio = event.get("audio")
                            if isinstance(audio, bytes):
                                yield audio
                        elif event_type == "finish":
                            if event.get("reason") == "error":
                                raise FishAudioServerError(
                                    "Fish Audio streaming failed"
                                )
                            break
        except asyncio.TimeoutError as exc:
            raise FishAudioTimeout("Fish Audio streaming request timed out") from exc
        except ClientConnectionError as exc:
            raise FishAudioServerError(
                "Could not connect to Fish Audio streaming"
            ) from exc

    async def async_download_audio(
        self,
        text: str,
        options: Mapping[str, Any],
    ) -> bytes:
        """Generate and download audio bytes."""
        return await self.async_generate_audio(text, options)

    def _tts_payload(self, text: str, options: Mapping[str, Any]) -> dict[str, Any]:
        """Build a documented Fish Audio TTS request payload."""
        audio_format = str(
            option_value(options, CONF_AUDIO_FORMAT, DEFAULT_AUDIO_FORMAT)
        )
        payload: dict[str, Any] = {
            "text": text,
            "prosody": {
                "speed": float(option_value(options, CONF_SPEED, DEFAULT_SPEED)),
                "volume": float(option_value(options, CONF_VOLUME, DEFAULT_VOLUME)),
                "normalize_loudness": True,
            },
            "chunk_length": 300,
            "normalize": True,
            "format": audio_format,
            "latency": str(option_value(options, CONF_LATENCY, DEFAULT_LATENCY)),
            "max_new_tokens": 1024,
            "repetition_penalty": 1.2,
            "min_chunk_length": 50,
            "condition_on_previous_chunks": True,
            "early_stop_threshold": 1,
        }
        voice = str(option_value(options, CONF_VOICE, "")).strip()
        if voice:
            payload["reference_id"] = voice
        pitch = float(option_value(options, CONF_PITCH, DEFAULT_PITCH))
        if pitch:
            payload["prosody"]["pitch"] = pitch
        sample_rate = option_value(options, CONF_SAMPLE_RATE, DEFAULT_SAMPLE_RATE)
        if sample_rate:
            payload["sample_rate"] = int(sample_rate)
        if audio_format == "mp3":
            payload["mp3_bitrate"] = MP3_BITRATE
        if audio_format == "opus":
            payload["opus_bitrate"] = OPUS_BITRATE
        return payload

    def _headers(self, extra: Mapping[str, str] | None = None) -> dict[str, str]:
        """Return authenticated request headers."""
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "User-Agent": self.user_agent,
        }
        if extra:
            headers.update(extra)
        return headers

    async def _request_json(
        self, method: str, path: str, **kwargs: Any
    ) -> dict[str, Any]:
        """Request JSON and validate the response type."""
        response = await self._request(method, path, **kwargs)
        try:
            data = await response.json(content_type=None)
        except Exception as exc:
            raise FishAudioValidationError("Fish Audio returned invalid JSON") from exc
        if not isinstance(data, dict):
            raise FishAudioValidationError("Fish Audio returned an unexpected response")
        return data

    async def _request_bytes(self, method: str, path: str, **kwargs: Any) -> bytes:
        """Request bytes from Fish Audio."""
        response = await self._request(method, path, **kwargs)
        return await response.read()

    async def _request(self, method: str, path: str, **kwargs: Any) -> ClientResponse:
        """Perform an authenticated Fish Audio request with retries."""
        headers = self._headers(kwargs.pop("headers", None))
        timeout = ClientTimeout(total=float(kwargs.pop("timeout", REQUEST_TIMEOUT)))
        url = f"{self._base_url}{path}"
        for attempt in range(MAX_RETRIES):
            await self._respect_rate_limit()
            try:
                response = await self._session.request(
                    method,
                    url,
                    headers=headers,
                    timeout=timeout,
                    **kwargs,
                )
            except asyncio.TimeoutError as exc:
                if attempt == MAX_RETRIES - 1:
                    raise FishAudioTimeout("Fish Audio request timed out") from exc
                await self._sleep_before_retry(attempt)
                continue
            except ClientConnectionError as exc:
                if attempt == MAX_RETRIES - 1:
                    raise FishAudioServerError(
                        "Could not connect to Fish Audio"
                    ) from exc
                await self._sleep_before_retry(attempt)
                continue

            if response.status < 400:
                return response
            error_message = await self._error_message(response)
            response.release()
            if response.status == 401:
                raise FishAudioAuthenticationError(error_message)
            if response.status == 429:
                if attempt < MAX_RETRIES - 1:
                    await self._sleep_before_retry(attempt)
                    continue
                raise FishAudioRateLimit(error_message)
            if response.status >= 500:
                if attempt < MAX_RETRIES - 1:
                    await self._sleep_before_retry(attempt)
                    continue
                raise FishAudioServerError(error_message)
            raise FishAudioValidationError(error_message)
        raise FishAudioServerError("Fish Audio request failed")

    async def _error_message(self, response: ClientResponse) -> str:
        """Extract a concise Fish Audio error message."""
        try:
            data = await response.json(content_type=None)
        except Exception:
            text = await response.text()
            return text or f"Fish Audio returned HTTP {response.status}"
        if isinstance(data, dict):
            return str(data.get("message") or data.get("detail") or data)
        return f"Fish Audio returned HTTP {response.status}"

    async def _sleep_before_retry(self, attempt: int) -> None:
        """Sleep using exponential backoff."""
        delay = RETRY_BASE_DELAY * (2**attempt)
        _LOGGER.debug("Retrying Fish Audio request in %.1f seconds", delay)
        await asyncio.sleep(delay)

    async def _respect_rate_limit(self) -> None:
        """Apply a conservative local request limit."""
        loop = asyncio.get_running_loop()
        async with self._rate_lock:
            now = loop.time()
            while (
                self._request_times and now - self._request_times[0] > RATE_LIMIT_WINDOW
            ):
                self._request_times.popleft()
            if len(self._request_times) >= RATE_LIMIT_REQUESTS:
                delay = RATE_LIMIT_WINDOW - (now - self._request_times[0])
                _LOGGER.debug(
                    "Fish Audio local rate limit sleeping for %.1f seconds", delay
                )
                await asyncio.sleep(max(delay, 0))
            self._request_times.append(loop.time())
