"""Async client for the RYSE SmartBridge local HTTP API."""

from __future__ import annotations

import asyncio
from typing import Any

import aiohttp

from .exceptions import (
    RyseConnectionError,
    RyseNotFoundError,
    RyseResponseError,
)
from .models import Device, Gear

DEFAULT_TIMEOUT = 10.0


class RyseBridge:
    """Talks to a RYSE SmartBridge over its local HTTP API (no cloud).

    Parameters
    ----------
    host:
        The bridge's IP address or hostname on the LAN.
    session:
        An ``aiohttp.ClientSession`` to use for requests.
    serial:
        Optional credential. The bridge only requires it when its local
        security option is enabled; when set it is sent as the
        ``Authorization`` header on every request.
    timeout:
        Per-request timeout in seconds.
    """

    def __init__(
        self,
        host: str,
        session: aiohttp.ClientSession,
        *,
        serial: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self._host = host
        self._session = session
        self._serial = serial
        self._timeout = timeout
        self._device_id: str | None = None

    @property
    def device_id(self) -> str | None:
        """The bridge's ``dvc_id``, known after the first fetch."""
        return self._device_id

    async def async_get_device(self) -> Device:
        """Fetch the bridge and all its gears with full detail.

        Uses the detailed ``/lua/device/<dvc_id>`` endpoint, which includes
        battery (``power_level``) and firmware fields. The device id is
        resolved once from the list endpoint and cached.
        """
        dvc = await self._ensure_device_id()
        data = await self._request("GET", f"/lua/device/{dvc}")
        if not isinstance(data, dict) or "dvc_id" not in data:
            raise RyseResponseError("Unexpected device response")
        return Device.from_dict(data)

    async def async_get_gears(self) -> list[Gear]:
        """Convenience: just the gears from :meth:`async_get_device`."""
        return (await self.async_get_device()).gears

    async def async_get_position(self, gear_id: str) -> Gear:
        """Fetch one gear's position via the per-gear endpoint.

        Returns a sparse :class:`Gear` carrying ``position`` and
        ``position_state`` (the endpoint reports only those two fields).
        """
        dvc = await self._ensure_device_id()
        data = await self._request(
            "GET", f"/lua/device/{dvc}/gear/{gear_id}/position"
        )
        if not isinstance(data, dict) or "position" not in data:
            raise RyseResponseError("Unexpected position response")
        return Gear.from_dict({"id": gear_id, **data})

    async def async_set_position(self, gear_id: str, position: int) -> None:
        """Move a gear to ``position`` (0-100, bridge scale: 0 open, 100 closed).

        Values are clamped into range.
        """
        dvc = await self._ensure_device_id()
        position = max(0, min(100, int(position)))
        await self._request(
            "POST",
            f"/lua/device/{dvc}/gear/{gear_id}/position",
            json={"position": position},
        )

    async def _ensure_device_id(self) -> str:
        """Resolve and cache the bridge's ``dvc_id``.

        Uses the list endpoint (``/lua/device``), which does not require a
        known id, so this never recurses into :meth:`async_get_device`.
        """
        if self._device_id is not None:
            return self._device_id
        data = await self._request("GET", "/lua/device")
        if isinstance(data, list):
            if not data:
                raise RyseResponseError("Empty /lua/device response")
            data = data[0]
        if not isinstance(data, dict) or "dvc_id" not in data:
            raise RyseResponseError("Unexpected /lua/device response")
        self._device_id = str(data["dvc_id"])
        return self._device_id

    async def _request(
        self, method: str, path: str, *, json: dict[str, Any] | None = None
    ) -> Any:
        url = f"http://{self._host}{path}"
        headers = {"Authorization": self._serial} if self._serial else None
        try:
            async with asyncio.timeout(self._timeout):
                resp = await self._session.request(
                    method, url, json=json, headers=headers
                )
                if resp.status in (400, 404):
                    raise RyseNotFoundError(
                        f"{method} {path} -> {resp.status}", status=resp.status
                    )
                if resp.status >= 400:
                    raise RyseResponseError(
                        f"{method} {path} -> {resp.status}", status=resp.status
                    )
                # Position POST returns an empty/non-JSON body on success.
                if method == "POST" and json is not None:
                    return None
                return await resp.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError) as err:
            raise RyseConnectionError(f"{method} {path} failed: {err}") from err
