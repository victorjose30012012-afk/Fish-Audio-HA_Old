"""Options flow for the Fish Audio integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlowResult, OptionsFlow
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    AUDIO_FORMATS,
    CONF_AUDIO_FORMAT,
    CONF_LANGUAGE,
    CONF_LATENCY,
    CONF_MODEL,
    CONF_PITCH,
    CONF_SAMPLE_RATE,
    CONF_SPEED,
    CONF_STREAMING,
    CONF_VOICE,
    DEFAULT_AUDIO_FORMAT,
    DEFAULT_LANGUAGE,
    DEFAULT_LATENCY,
    DEFAULT_MODEL,
    DEFAULT_PITCH,
    DEFAULT_SAMPLE_RATE,
    DEFAULT_SPEED,
    DEFAULT_STREAMING,
    DEFAULT_VOLUME,
    LATENCY_OPTIONS,
    SUPPORTED_LANGUAGES,
    TTS_MODELS,
    CONF_VOLUME,
)


class FishAudioOptionsFlow(OptionsFlow):
    """Handle options for Fish Audio."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize the options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Manage Fish Audio options."""
        errors: dict[str, str] = {}
        options = {**self._defaults(), **self._config_entry.options}

        if user_input is not None and not errors:
            return self.async_create_entry(title="", data=user_input)
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_VOICE, default=options.get(CONF_VOICE, "")
                ): TextSelector(
                    TextSelectorConfig(
                        type=TextSelectorType.TEXT,
                    )
                ),
                vol.Required(
                    CONF_MODEL,
                    default=options.get(CONF_MODEL, DEFAULT_MODEL),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            SelectOptionDict(value=model, label=model)
                            for model in TTS_MODELS
                        ],
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(
                    CONF_LANGUAGE,
                    default=options.get(CONF_LANGUAGE, DEFAULT_LANGUAGE),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            SelectOptionDict(value=lang, label=lang)
                            for lang in SUPPORTED_LANGUAGES
                        ],
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(
                    CONF_SPEED,
                    default=options.get(CONF_SPEED, DEFAULT_SPEED),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=0.5,
                        max=2.0,
                        step=0.05,
                        mode=NumberSelectorMode.SLIDER,
                    )
                ),
                vol.Required(
                    CONF_PITCH,
                    default=options.get(CONF_PITCH, DEFAULT_PITCH),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=-12,
                        max=12,
                        step=0.5,
                        mode=NumberSelectorMode.SLIDER,
                    )
                ),
                vol.Required(
                    CONF_VOLUME,
                    default=options.get(CONF_VOLUME, DEFAULT_VOLUME),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=-20,
                        max=20,
                        step=0.5,
                        mode=NumberSelectorMode.SLIDER,
                    )
                ),
                vol.Required(
                    CONF_STREAMING,
                    default=options.get(CONF_STREAMING, DEFAULT_STREAMING),
                ): BooleanSelector(),
                vol.Required(
                    CONF_AUDIO_FORMAT,
                    default=options.get(CONF_AUDIO_FORMAT, DEFAULT_AUDIO_FORMAT),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            SelectOptionDict(value=fmt, label=fmt)
                            for fmt in AUDIO_FORMATS
                        ],
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(
                    CONF_LATENCY,
                    default=options.get(CONF_LATENCY, DEFAULT_LATENCY),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            SelectOptionDict(value=latency, label=latency)
                            for latency in LATENCY_OPTIONS
                        ],
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_SAMPLE_RATE,
                    default=options.get(CONF_SAMPLE_RATE, DEFAULT_SAMPLE_RATE),
                ): vol.All(
                    vol.Coerce(int), vol.In([8000, 16000, 24000, 32000, 44100, 48000])
                ),
            }
        )
        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
        )

    def _defaults(self) -> dict[str, Any]:
        """Return default options."""
        return {
            CONF_VOICE: "",
            CONF_MODEL: DEFAULT_MODEL,
            CONF_LANGUAGE: DEFAULT_LANGUAGE,
            CONF_SPEED: DEFAULT_SPEED,
            CONF_PITCH: DEFAULT_PITCH,
            CONF_VOLUME: DEFAULT_VOLUME,
            CONF_STREAMING: DEFAULT_STREAMING,
            CONF_AUDIO_FORMAT: DEFAULT_AUDIO_FORMAT,
            CONF_LATENCY: DEFAULT_LATENCY,
            CONF_SAMPLE_RATE: DEFAULT_SAMPLE_RATE,
        }
