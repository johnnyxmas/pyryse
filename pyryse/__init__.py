"""pyryse — local client for RYSE SmartShade via the RYSE SmartBridge."""

from __future__ import annotations

from .bridge import DEFAULT_COMMAND_INTERVAL, RyseBridge
from .exceptions import (
    RyseConnectionError,
    RyseError,
    RyseNotFoundError,
    RyseResponseError,
)
from .models import (
    SPEED_MAX,
    SPEED_MIN,
    WIFI_SECURITY,
    Device,
    Gear,
    GearState,
    PowerType,
    WifiNetwork,
    WifiStatus,
    percent_to_speed,
    speed_to_percent,
)

__all__ = [
    "RyseBridge",
    "DEFAULT_COMMAND_INTERVAL",
    "Device",
    "Gear",
    "GearState",
    "PowerType",
    "SPEED_MIN",
    "SPEED_MAX",
    "WIFI_SECURITY",
    "WifiNetwork",
    "WifiStatus",
    "speed_to_percent",
    "percent_to_speed",
    "RyseError",
    "RyseConnectionError",
    "RyseResponseError",
    "RyseNotFoundError",
]

__version__ = "0.5.0"
