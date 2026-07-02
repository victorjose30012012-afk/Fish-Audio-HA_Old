"""Diagnostics support for Fish Audio."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import async_get as async_get_device_registry
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry

from . import FishAudioConfigEntry
from .const import DIAGNOSTIC_REDACT, DOMAIN


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: FishAudioConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    device_registry = async_get_device_registry(hass)
    entity_registry = async_get_entity_registry(hass)
    devices = [
        {
            "id": device.id,
            "name": device.name,
            "identifiers": list(device.identifiers),
        }
        for device in device_registry.devices.values()
        if any(identifier[0] == DOMAIN for identifier in device.identifiers)
    ]
    entities = [
        {
            "entity_id": entity.entity_id,
            "unique_id": entity.unique_id,
            "platform": entity.platform,
        }
        for entity in entity_registry.entities.values()
        if entity.platform == DOMAIN
    ]
    return {
        "entry": {
            "entry_id": entry.entry_id,
            "version": entry.version,
            "minor_version": entry.minor_version,
            "title": entry.title,
            "data": _redact(entry.data),
            "options": entry.options,
        },
        "devices": devices,
        "entities": entities,
    }


def _redact(data: Mapping[str, Any]) -> dict[str, Any]:
    """Redact sensitive diagnostics data."""
    return {
        key: "**REDACTED**" if key in DIAGNOSTIC_REDACT else value
        for key, value in data.items()
    }
