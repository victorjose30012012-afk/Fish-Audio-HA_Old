"""Config flow for the Fish Audio integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_API_KEY
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import FishAudioAPI
from .const import API_KEYS_URL, DOMAIN, NAME, SIGNUP_URL
from .exceptions import FishAudioAuthenticationError, FishAudioError
from .options_flow import FishAudioOptionsFlow

_LOGGER = logging.getLogger(__name__)


class FishAudioConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Fish Audio."""

    VERSION = 1
    MINOR_VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry: Any) -> FishAudioOptionsFlow:
        """Create the options flow."""
        return FishAudioOptionsFlow(config_entry)

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()
            api = FishAudioAPI(async_get_clientsession(self.hass), api_key)
            try:
                user_id = await api.async_validate()
            except FishAudioAuthenticationError:
                errors["base"] = "invalid_auth"
            except FishAudioError as exc:
                _LOGGER.debug("Fish Audio validation failed: %s", exc)
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected Fish Audio validation failure")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(user_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=NAME,
                    data={CONF_API_KEY: api_key},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_API_KEY): str}),
            errors=errors,
            description_placeholders={
                "api_keys_url": API_KEYS_URL,
                "signup_url": SIGNUP_URL,
            },
        )
