"""Typed models for RYSE SmartBridge data.

These mirror the bridge's own representation faithfully. In particular,
``position`` uses the bridge's native scale, which is the *inverse* of Home
Assistant's cover convention:

* ``0``   = fully open (observed on real hardware, 2026-11)
* ``100`` = fully closed

Consumers that need Home Assistant semantics (100 = open) should invert.

``speed`` is also in the bridge's native scale (40-100). The RYSE app shows
0-100%; use :func:`speed_to_percent` and :func:`percent_to_speed` to convert.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

#: Lowest and highest speed the bridge accepts (bridge scale).
SPEED_MIN = 40
SPEED_MAX = 100


def speed_to_percent(speed: int) -> int:
    """Convert a bridge speed (40-100) to the RYSE app's percentage (0-100).

    Linear over the bridge range, rounded down the way the app displays it:
    40 -> 0, 41 -> 1, 46 -> 10, 70 -> 50, 100 -> 100.
    """
    speed = max(SPEED_MIN, min(SPEED_MAX, int(speed)))
    return (speed - SPEED_MIN) * 100 // (SPEED_MAX - SPEED_MIN)


def percent_to_speed(percent: int) -> int:
    """Convert an app percentage (0-100) to a bridge speed (40-100).

    The bridge has only 61 speed values for 101 percentages, so not every
    percentage survives a round trip (for example 2% is sent as 41, which
    reads back as 1%).
    """
    percent = max(0, min(100, int(percent)))
    return SPEED_MIN + (percent * 6 + 5) // 10


class GearState(IntEnum):
    """Movement state reported by a gear (``position_state``).

    Values observed on firmware 5.3.2:

    * ``IDLE``    (0) — stopped / settled.
    * ``OPENING`` (1) — moving toward position 0.
    * ``CLOSING`` (2) — moving toward position 100.

    A gear that is offline may report a stale non-idle value, so check
    :attr:`Gear.online` before trusting it.
    """

    IDLE = 0
    OPENING = 1
    CLOSING = 2

    @classmethod
    def _missing_(cls, value: object) -> GearState:
        # Be forgiving about unknown values from other firmware.
        return cls.IDLE


class PowerType(IntEnum):
    """How a gear is currently powered (``power_type``).

    These meanings are inferred from observed changes on one gear as its power
    source was swapped (battery -> AC adapter -> USB charger); RYSE does not
    document them.
    """

    UNKNOWN = -1
    AC_ADAPTER = 0
    USB_CHARGER = 1
    BATTERY = 2

    @classmethod
    def _missing_(cls, value: object) -> PowerType:
        return cls.UNKNOWN


@dataclass(slots=True)
class Gear:
    """A single shade (RYSE calls them "gears")."""

    id: str
    name: str
    position: int
    position_state: GearState
    online: bool
    battery: int | None = None  # power_level, 0-100
    speed: int | None = None  # bridge scale, 40-100
    gear_type: int | None = None
    power_type: int | None = None
    obstacle_detection: int | None = None
    machine_state: int | None = None
    fw_version: str | None = None
    hw_version: str | None = None
    msp_fw_version: str | None = None
    serial_number: str | None = None
    stats: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def is_moving(self) -> bool:
        """Whether the gear is currently in motion."""
        return self.online and self.position_state is not GearState.IDLE

    @property
    def speed_percent(self) -> int | None:
        """Speed on the RYSE app's 0-100% scale, or ``None`` if unknown."""
        return speed_to_percent(self.speed) if self.speed is not None else None

    @property
    def obstacle_detection_enabled(self) -> bool | None:
        """Whether obstacle detection is on, or ``None`` if unknown."""
        if self.obstacle_detection is None:
            return None
        return bool(self.obstacle_detection)

    @property
    def power_source(self) -> PowerType | None:
        """How the gear is powered, or ``None`` if the bridge didn't say."""
        if self.power_type is None:
            return None
        return PowerType(self.power_type)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Gear:
        return cls(
            id=str(data["id"]),
            name=str(data.get("name", data["id"])),
            position=int(data.get("position", 0)),
            position_state=GearState(int(data.get("position_state", 0))),
            online=bool(data.get("online", False)),
            battery=_opt_int(data.get("power_level")),
            speed=_opt_int(data.get("speed")),
            gear_type=_opt_int(data.get("gear_type")),
            power_type=_opt_int(data.get("power_type")),
            obstacle_detection=_opt_int(data.get("obstacle_detection")),
            machine_state=_opt_int(data.get("machine_state")),
            fw_version=_opt_str(data.get("fw_version")),
            hw_version=_opt_str(data.get("hw_version")),
            msp_fw_version=_opt_str(data.get("msp_fw_version")),
            serial_number=_opt_str(data.get("serial_number")),
            stats=dict(data.get("stats") or {}),
            raw=data,
        )


@dataclass(slots=True)
class Device:
    """A RYSE SmartBridge and the gears attached to it."""

    id: str
    name: str
    mac: str | None
    ip: str | None
    online: bool
    fw_version: str | None
    hw_version: str | None
    #: Versions of the bridge's internal components, e.g. ``{"lua": "5.2.0"}``.
    app_versions: dict[str, str]
    local_security_enable: bool
    ifttt_enable: bool = False
    #: Which interface the bridge uses to reach the network, e.g. ``"Ethernet"``.
    wan_iface: str | None = None
    timezone_city: str | None = None
    timezone_posix: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    gears: list[Gear] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def app_version(self) -> str | None:
        """The bridge's main (lua) component version, if reported."""
        return self.app_versions.get("lua")

    def gear(self, gear_id: str) -> Gear | None:
        """Return the gear with ``gear_id``, or ``None``."""
        return next((g for g in self.gears if g.id == gear_id), None)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Device:
        tz = data.get("dvc_timezone2") or {}
        versions = data.get("dvc_app_version")
        return cls(
            id=str(data["dvc_id"]),
            name=str(data.get("dvc_name", "RYSE SmartBridge")),
            mac=_opt_str(data.get("dvc_mac")),
            ip=_opt_str(data.get("dvc_ip")),
            online=bool(data.get("dvc_online", True)),
            fw_version=_opt_str(data.get("dvc_fw_version")),
            hw_version=_opt_str(data.get("dvc_hw_version")),
            app_versions=(
                {str(k): str(v) for k, v in versions.items()}
                if isinstance(versions, dict)
                else {}
            ),
            local_security_enable=bool(data.get("local_security_enable", False)),
            ifttt_enable=bool(data.get("ifttt_enable", False)),
            wan_iface=_opt_str(data.get("dvc_wan_iface")),
            timezone_city=_opt_str(tz.get("dvc_tz_city")),
            timezone_posix=_opt_str(tz.get("dvc_tz_posix")),
            latitude=_opt_float(tz.get("dvc_latitude")),
            longitude=_opt_float(tz.get("dvc_longitude")),
            gears=[Gear.from_dict(g) for g in data.get("gears", []) if g.get("id")],
            raw=data,
        )


def _opt_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _opt_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _opt_str(value: Any) -> str | None:
    return str(value) if value is not None else None
