"""Typed models for RYSE SmartBridge data.

These mirror the bridge's own representation faithfully. In particular,
``position`` uses the bridge's native scale, which is the *inverse* of Home
Assistant's cover convention:

* ``0``   = fully open (observed on real hardware, 2026-11)
* ``100`` = fully closed

Consumers that need Home Assistant semantics (100 = open) should invert.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any


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


@dataclass(slots=True)
class Gear:
    """A single shade (RYSE calls them "gears")."""

    id: str
    name: str
    position: int
    position_state: GearState
    online: bool
    battery: int | None = None  # power_level, 0-100
    speed: int | None = None
    gear_type: int | None = None
    power_type: int | None = None
    obstacle_detection: int | None = None
    machine_state: int | None = None
    fw_version: str | None = None
    hw_version: str | None = None
    msp_fw_version: str | None = None
    serial_number: str | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def is_moving(self) -> bool:
        """Whether the gear is currently in motion."""
        return self.online and self.position_state is not GearState.IDLE

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
    app_version: str | None
    local_security_enable: bool
    gears: list[Gear] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    def gear(self, gear_id: str) -> Gear | None:
        """Return the gear with ``gear_id``, or ``None``."""
        return next((g for g in self.gears if g.id == gear_id), None)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Device:
        return cls(
            id=str(data["dvc_id"]),
            name=str(data.get("dvc_name", "RYSE SmartBridge")),
            mac=_opt_str(data.get("dvc_mac")),
            ip=_opt_str(data.get("dvc_ip")),
            online=bool(data.get("dvc_online", True)),
            fw_version=_opt_str(data.get("dvc_fw_version")),
            hw_version=_opt_str(data.get("dvc_hw_version")),
            app_version=_opt_str(data.get("dvc_app_version")),
            local_security_enable=bool(data.get("local_security_enable", False)),
            gears=[Gear.from_dict(g) for g in data.get("gears", []) if g.get("id")],
            raw=data,
        )


def _opt_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _opt_str(value: Any) -> str | None:
    return str(value) if value is not None else None
