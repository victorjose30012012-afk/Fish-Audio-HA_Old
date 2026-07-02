"""Exceptions for the Fish Audio integration."""

from __future__ import annotations


class FishAudioError(Exception):
    """Base exception for Fish Audio errors."""


class FishAudioAuthenticationError(FishAudioError):
    """Raised when authentication fails."""


class FishAudioRateLimit(FishAudioError):
    """Raised when Fish Audio rate limits a request."""


class FishAudioTimeout(FishAudioError):
    """Raised when a Fish Audio request times out."""


class FishAudioServerError(FishAudioError):
    """Raised when Fish Audio returns a server error."""


class FishAudioValidationError(FishAudioError):
    """Raised when Fish Audio rejects request data."""
