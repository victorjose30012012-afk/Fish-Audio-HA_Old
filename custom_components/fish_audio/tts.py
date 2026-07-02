"""TTS platform for the Fish Audio integration."""

from __future__ import annotations

from collections.abc import AsyncGenerator
import logging
from typing import Any

from homeassistant.components.tts import (
    TTSAudioRequest,
    TTSAudioResponse,
    TextToSpeechEntity,
    TtsAudioType,
)
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import FishAudioConfigEntry
from .const import (
    CONF_AUDIO_FORMAT,
    CONF_LANGUAGE,
    CONF_MODEL,
    CONF_STREAMING,
    CONF_VOICE,
    DEFAULT_AUDIO_FORMAT,
    DEFAULT_LANGUAGE,
    DEFAULT_MODEL,
    DEFAULT_STREAMING,
    DOMAIN,
    MANUFACTURER,
    NAME,
    SUPPORTED_LANGUAGES,
)
from .exceptions import (
    FishAudioAuthenticationError,
    FishAudioError,
    FishAudioRateLimit,
    FishAudioValidationError,
)
from .helpers import async_read_cache, async_write_cache, cache_key

_LOGGER = logging.getLogger(__name__)
PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass,
    entry: FishAudioConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Fish Audio TTS entity."""
    async_add_entities([FishAudioTTSEntity(entry)])


class FishAudioTTSEntity(TextToSpeechEntity):
    """Fish Audio TTS entity."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_unique_id = f"{DOMAIN}_tts"
    _attr_supported_options = [
        CONF_VOICE,
        CONF_MODEL,
        CONF_AUDIO_FORMAT,
        CONF_STREAMING,
    ]

    def __init__(self, entry: FishAudioConfigEntry) -> None:
        """Initialize the Fish Audio TTS entity."""
        self._entry = entry
        self._api = entry.runtime_data.api
        self._attr_unique_id = f"{entry.entry_id}_tts"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            manufacturer=MANUFACTURER,
            name=NAME,
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def supported_languages(self) -> list[str]:
        """Return supported languages."""
        return SUPPORTED_LANGUAGES

    @property
    def default_language(self) -> str:
        """Return the default language."""
        return str(self._entry.options.get(CONF_LANGUAGE, DEFAULT_LANGUAGE))

    @property
    def default_options(self) -> dict[str, Any]:
        """Return default TTS options."""
        return dict(self._entry.options)

    async def async_get_tts_audio(
        self,
        message: str,
        language: str,
        options: dict[str, Any],
    ) -> TtsAudioType:
        """Load TTS audio from Fish Audio."""
        synthesis_options = self._merged_options(language, options)
        audio_format = str(
            synthesis_options.get(CONF_AUDIO_FORMAT, DEFAULT_AUDIO_FORMAT)
        )
        key = cache_key(message, synthesis_options)

        cached = await async_read_cache(self.hass, key, audio_format)
        if cached is not None:
            _LOGGER.debug("Fish Audio cache hit for %s", key)
            return audio_format, cached

        _LOGGER.debug("Fish Audio cache miss for %s", key)
        try:
            audio = await self._api.async_generate_audio(message, synthesis_options)
        except FishAudioValidationError as exc:
            raise ServiceValidationError(str(exc)) from exc
        except FishAudioAuthenticationError as exc:
            raise HomeAssistantError("Fish Audio authentication failed") from exc
        except FishAudioRateLimit as exc:
            raise HomeAssistantError("Fish Audio rate limit exceeded") from exc
        except FishAudioError as exc:
            raise HomeAssistantError(f"Fish Audio TTS failed: {exc}") from exc

        await async_write_cache(self.hass, key, audio_format, audio)
        return audio_format, audio

    async def async_stream_tts_audio(
        self,
        request: TTSAudioRequest,
    ) -> TTSAudioResponse:
        """Generate speech from an incoming text stream."""
        synthesis_options = self._merged_options(request.language, request.options)
        audio_format = str(
            synthesis_options.get(CONF_AUDIO_FORMAT, DEFAULT_AUDIO_FORMAT)
        )
        if not synthesis_options.get(CONF_STREAMING, DEFAULT_STREAMING):
            message = await _collect_message(request.message_gen)
            audio = await self.async_get_tts_audio(
                message,
                request.language,
                request.options,
            )
            extension, data = audio
            if extension is None or data is None:
                raise HomeAssistantError("Fish Audio returned no audio")

            async def _single() -> AsyncGenerator[bytes]:
                yield data

            return TTSAudioResponse(extension=extension, data_gen=_single())

        async def _stream() -> AsyncGenerator[bytes]:
            try:
                async for chunk in self._api.async_stream_audio(
                    request.message_gen,
                    synthesis_options,
                ):
                    yield chunk
            except FishAudioValidationError as exc:
                raise ServiceValidationError(str(exc)) from exc
            except FishAudioError as exc:
                raise HomeAssistantError(f"Fish Audio streaming failed: {exc}") from exc

        return TTSAudioResponse(extension=audio_format, data_gen=_stream())

    def _merged_options(
        self,
        language: str | None,
        options: dict[str, Any],
    ) -> dict[str, Any]:
        """Merge config entry options, service options, and request language."""
        merged = dict(self._entry.options)
        merged.update(options)
        merged[CONF_LANGUAGE] = language or merged.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)
        merged.setdefault(CONF_MODEL, DEFAULT_MODEL)
        merged.setdefault(CONF_AUDIO_FORMAT, DEFAULT_AUDIO_FORMAT)
        voice = str(merged.get(CONF_VOICE, "")).strip()
        merged[CONF_VOICE] = voice
        return merged


async def _collect_message(message_gen: AsyncGenerator[str]) -> str:
    """Collect a streaming message into one string."""
    chunks: list[str] = []
    async for chunk in message_gen:
        chunks.append(chunk)
    return "".join(chunks)
