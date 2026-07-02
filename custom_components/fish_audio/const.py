"""Constants for the Fish Audio integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "fish_audio"
NAME = "Fish Audio"
MANUFACTURER = "Fish Audio"

PLATFORMS: list[Platform] = [Platform.TTS]

API_BASE_URL = "https://api.fish.audio"
API_WS_URL = "wss://api.fish.audio/v1/tts/live"
API_KEYS_URL = "https://fish.audio/app/api-keys/"
SIGNUP_URL = "https://fish.audio/"

CONF_API_KEY = "api_key"
CONF_VOICE = "voice"
CONF_MODEL = "model"
CONF_LANGUAGE = "language"
CONF_SPEED = "speed"
CONF_PITCH = "pitch"
CONF_VOLUME = "volume"
CONF_STREAMING = "streaming"
CONF_AUDIO_FORMAT = "audio_format"
CONF_LATENCY = "latency"
CONF_SAMPLE_RATE = "sample_rate"
CONF_USER_ID = "user_id"

DEFAULT_MODEL = "s2-pro"
DEFAULT_LANGUAGE = "pt-BR"
DEFAULT_SPEED = 1.0
DEFAULT_PITCH = 0.0
DEFAULT_VOLUME = 0.0
DEFAULT_STREAMING = True
DEFAULT_AUDIO_FORMAT = "mp3"
DEFAULT_LATENCY = "balanced"
DEFAULT_SAMPLE_RATE = 44100

TTS_MODELS = ["s1", "s2-pro"]
LATENCY_OPTIONS = ["low", "balanced", "normal"]
AUDIO_FORMATS = ["mp3", "wav", "pcm", "opus"]
MP3_BITRATE = 128
OPUS_BITRATE = -1000

SUPPORTED_LANGUAGES = [
    "ar",
    "de-DE",
    "en",
    "en-US",
    "es-ES",
    "fr-FR",
    "it-IT",
    "ja-JP",
    "ko-KR",
    "pt-BR",
    "ru-RU",
    "zh-CN",
    "zh-TW",
]

REQUEST_TIMEOUT = 60
STREAM_TIMEOUT = 120
MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0
RATE_LIMIT_REQUESTS = 6
RATE_LIMIT_WINDOW = 60.0

CACHE_DIR = "fish_audio"
DIAGNOSTIC_REDACT = {CONF_API_KEY}
