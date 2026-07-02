"""Helper utilities for the Fish Audio integration."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant

from .const import (
    CACHE_DIR,
    CONF_AUDIO_FORMAT,
    CONF_LANGUAGE,
    CONF_MODEL,
    CONF_PITCH,
    CONF_SPEED,
    CONF_VOICE,
    CONF_VOLUME,
    DEFAULT_AUDIO_FORMAT,
    DEFAULT_LANGUAGE,
    DEFAULT_MODEL,
    DEFAULT_PITCH,
    DEFAULT_SPEED,
    DEFAULT_VOLUME,
)


@dataclass(slots=True, frozen=True)
class Voice:
    """Fish Audio voice model."""

    id: str
    title: str
    languages: tuple[str, ...]
    task_count: int = 0

    @property
    def label(self) -> str:
        """Return a user-facing selector label."""
        suffix = f" ({self.task_count} uses)" if self.task_count else ""
        return f"{self.title}{suffix}"


def option_value(
    options: Mapping[str, Any],
    key: str,
    default: Any,
) -> Any:
    """Return an option value, preserving explicit falsey values."""
    return options[key] if key in options else default


def cache_key(message: str, options: Mapping[str, Any]) -> str:
    """Return a stable cache key for a Fish Audio synthesis request."""
    payload = {
        "text": message,
        "voice": option_value(options, CONF_VOICE, ""),
        "language": option_value(options, CONF_LANGUAGE, DEFAULT_LANGUAGE),
        "model": option_value(options, CONF_MODEL, DEFAULT_MODEL),
        "speed": option_value(options, CONF_SPEED, DEFAULT_SPEED),
        "pitch": option_value(options, CONF_PITCH, DEFAULT_PITCH),
        "volume": option_value(options, CONF_VOLUME, DEFAULT_VOLUME),
        "format": option_value(options, CONF_AUDIO_FORMAT, DEFAULT_AUDIO_FORMAT),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256(raw.encode("utf-8")).hexdigest()


def cache_path(hass: HomeAssistant, key: str, audio_format: str) -> Path:
    """Return the cache file path for generated audio."""
    return Path(hass.config.path(CACHE_DIR)) / f"{key}.{audio_format}"


async def async_read_cache(
    hass: HomeAssistant,
    key: str,
    audio_format: str,
) -> bytes | None:
    """Read cached audio from disk."""
    path = cache_path(hass, key, audio_format)

    def _read() -> bytes | None:
        if not path.is_file():
            return None
        return path.read_bytes()

    return await hass.async_add_executor_job(_read)


async def async_write_cache(
    hass: HomeAssistant,
    key: str,
    audio_format: str,
    audio: bytes,
) -> None:
    """Write generated audio to disk cache."""
    path = cache_path(hass, key, audio_format)

    def _write() -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(audio)

    await hass.async_add_executor_job(_write)
