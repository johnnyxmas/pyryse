"""Tests for pyryse against a mocked bridge."""

from __future__ import annotations

import aiohttp
import pytest
from aioresponses import aioresponses

from pyryse import (
    Device,
    GearState,
    RyseBridge,
    RyseConnectionError,
    RyseNotFoundError,
)

HOST = "192.168.0.123"
DVC = "xd7JZVuNW"
LIST_URL = f"http://{HOST}/lua/device"
DETAIL_URL = f"http://{HOST}/lua/device/{DVC}"

# The list endpoint (`GET /lua/device`) is sparse: just enough to find dvc_id
# and get a quick read of each gear's position/online state.
LIST_PAYLOAD = [
    {
        "dvc_name": "RYSE SmartBridge",
        "dvc_id": DVC,
        "gears": [
            {"id": "c34ae8d8c52b", "name": "2", "position": 0,
             "position_state": 0, "online": True},
            {"id": "f4e324d59c02", "name": "1", "position": 54,
             "position_state": 2, "online": False},
        ],
    }
]

# The detailed endpoint (`GET /lua/device/<dvc_id>`) carries everything,
# including battery (power_level), firmware/hardware versions and serials.
DETAIL_PAYLOAD = {
    "dvc_name": "RYSE SmartBridge",
    "dvc_id": DVC,
    "dvc_mac": "d0:16:f0:20:64:89",
    "dvc_ip": HOST,
    "dvc_online": True,
    "dvc_fw_version": "1.2.3",
    "local_security_enable": False,
    "gears": [
        {
            "id": "c34ae8d8c52b",
            "name": "2",
            "position": 0,
            "position_state": 0,
            "online": True,
            "power_level": 64,
            "fw_version": "5.3.2",
            "serial_number": "SECRET",
        },
        {
            "id": "f4e324d59c02",
            "name": "1",
            "position": 54,
            "position_state": 2,
            "online": False,
        },
    ],
}


@pytest.fixture
async def session():
    async with aiohttp.ClientSession() as s:
        yield s


async def test_get_device_parses(session):
    with aioresponses() as m:
        m.get(LIST_URL, payload=LIST_PAYLOAD)
        m.get(DETAIL_URL, payload=DETAIL_PAYLOAD)
        bridge = RyseBridge(HOST, session)
        device = await bridge.async_get_device()

    assert isinstance(device, Device)
    assert device.id == DVC
    assert bridge.device_id == DVC
    assert len(device.gears) == 2

    g2 = device.gear("c34ae8d8c52b")
    assert g2 is not None
    assert g2.name == "2"
    assert g2.position == 0
    assert g2.position_state is GearState.IDLE
    assert g2.online is True
    assert g2.battery == 64
    assert g2.is_moving is False

    offline = device.gear("f4e324d59c02")
    assert offline.online is False
    # offline gear reports a stale non-idle state; is_moving must still be False
    assert offline.position_state is GearState.CLOSING
    assert offline.is_moving is False


async def test_device_id_is_cached_after_first_fetch(session):
    """A second async_get_device() must not re-hit the list endpoint."""
    with aioresponses() as m:
        m.get(LIST_URL, payload=LIST_PAYLOAD)
        m.get(DETAIL_URL, payload=DETAIL_PAYLOAD)
        m.get(DETAIL_URL, payload=DETAIL_PAYLOAD)  # second detail fetch
        bridge = RyseBridge(HOST, session)
        await bridge.async_get_device()
        await bridge.async_get_device()

        list_calls = [k for k in m.requests if str(k[1]) == LIST_URL]
    assert len(list_calls) == 1


async def test_set_position_clamps_and_posts(session):
    with aioresponses() as m:
        m.get(LIST_URL, payload=LIST_PAYLOAD)
        url = f"http://{HOST}/lua/device/{DVC}/gear/c34ae8d8c52b/position"
        m.post(url, status=200, body="")
        bridge = RyseBridge(HOST, session)
        await bridge.async_set_position("c34ae8d8c52b", 150)  # out of range

        post_calls = [
            calls for key, calls in m.requests.items() if key[0] == "POST"
        ]
    assert post_calls, "no POST was issued"
    # value clamped to 100
    assert post_calls[0][0].kwargs["json"] == {"position": 100}


async def test_authorization_header_sent_with_serial(session):
    with aioresponses() as m:
        m.get(LIST_URL, payload=LIST_PAYLOAD)
        m.get(DETAIL_URL, payload=DETAIL_PAYLOAD)
        bridge = RyseBridge(HOST, session, serial="MY-SERIAL")
        await bridge.async_get_device()

        headers_seen = [
            calls[0].kwargs["headers"] for calls in m.requests.values()
        ]
    assert all(h == {"Authorization": "MY-SERIAL"} for h in headers_seen)


async def test_bad_gear_raises_not_found(session):
    with aioresponses() as m:
        m.get(LIST_URL, payload=LIST_PAYLOAD)
        url = f"http://{HOST}/lua/device/{DVC}/gear/deadbeef/position"
        m.get(url, status=400)
        bridge = RyseBridge(HOST, session)
        with pytest.raises(RyseNotFoundError):
            await bridge.async_get_position("deadbeef")


async def test_connection_error(session):
    with aioresponses() as m:
        m.get(
            LIST_URL,
            exception=aiohttp.ClientConnectionError("boom"),
        )
        bridge = RyseBridge(HOST, session)
        with pytest.raises(RyseConnectionError):
            await bridge.async_get_device()
