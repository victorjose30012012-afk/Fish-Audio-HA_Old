"""The Fish Audio integration."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
import shutil

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import FishAudioAPI
from .const import CACHE_DIR, CONF_API_KEY, DOMAIN, PLATFORMS
from .exceptions import FishAudioAuthenticationError, FishAudioError

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class FishAudioData:
    """Runtime data for the Fish Audio integration."""

    api: FishAudioAPI


type FishAudioConfigEntry = ConfigEntry[FishAudioData]


async def async_setup_entry(hass: HomeAssistant, entry: FishAudioConfigEntry) -> bool:
    """Set up Fish Audio from a config entry."""
    api = FishAudioAPI(
        async_get_clientsession(hass),
        entry.data[CONF_API_KEY],
    )
    try:
        await api.async_validate()
    except FishAudioAuthenticationError as exc:
        raise ConfigEntryAuthFailed("Invalid Fish Audio API key") from exc
    except FishAudioError as exc:
        raise ConfigEntryNotReady(f"Could not connect to Fish Audio: {exc}") from exc

    entry.runtime_data = FishAudioData(api=api)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    if not hass.services.has_service(DOMAIN, "clear_cache"):
        hass.services.async_register(DOMAIN, "clear_cache", _async_clear_cache)
        entry.async_on_unload(lambda: hass.services.async_remove(DOMAIN, "clear_cache"))
    _LOGGER.debug("Fish Audio integration loaded")
    return True


async def _async_update_listener(
    hass: HomeAssistant,
    entry: FishAudioConfigEntry,
) -> None:
    """Reload Fish Audio when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: FishAudioConfigEntry) -> bool:
    """Unload a Fish Audio config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_clear_cache(call: ServiceCall) -> None:
    """Clear generated Fish Audio audio cache."""
    hass: HomeAssistant = call.hass
    cache_dir = Path(hass.config.path(CACHE_DIR))

    def _clear() -> None:
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)

    await hass.async_add_executor_job(_clear)
