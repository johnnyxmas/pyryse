"""Exceptions for pyryse."""

from __future__ import annotations


class RyseError(Exception):
    """Base error for all pyryse failures."""


class RyseConnectionError(RyseError):
    """Raised when the bridge cannot be reached (network error or timeout)."""


class RyseResponseError(RyseError):
    """Raised when the bridge returns an unexpected HTTP status or body."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class RyseNotFoundError(RyseResponseError):
    """Raised when a device or gear id is not known to the bridge."""
