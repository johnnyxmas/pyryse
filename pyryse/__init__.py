"""pyryse — local client for RYSE SmartShade via the RYSE SmartBridge."""

from __future__ import annotations

from .bridge import RyseBridge
from .exceptions import (
    RyseConnectionError,
    RyseError,
    RyseNotFoundError,
    RyseResponseError,
)
from .models import (
    SPEED_MAX,
    SPEED_MIN,
    Device,
    Gear,
    GearState,
    PowerType,
    percent_to_speed,
    speed_to_percent,
)

__all__ = [
    "RyseBridge",
    "Device",
    "Gear",
    "GearState",
    "PowerType",
    "SPEED_MIN",
    "SPEED_MAX",
    "speed_to_percent",
    "percent_to_speed",
    "RyseError",
    "RyseConnectionError",
    "RyseResponseError",
    "RyseNotFoundError",
]

__version__ = "0.3.0"
