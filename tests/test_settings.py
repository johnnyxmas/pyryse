"""Tests for per-gear settings, the speed scale and the extra model fields."""

from __future__ import annotations

import aiohttp
import pytest
from aioresponses import aioresponses

from pyryse import (
    SPEED_MAX,
    SPEED_MIN,
    Device,
    Gear,
    PowerType,
    RyseBridge,
    RyseResponseError,
    percent_to_speed,
    speed_to_percent,
)

HOST = "192.168.0.123"
DVC = "xd7JZVuNW"
GEAR = "c34ae8d8c52b"
LIST_URL = f"http://{HOST}/lua/device"
BASE = f"http://{HOST}/lua/device/{DVC}/gear/{GEAR}"
LIST_PAYLOAD = [{"dvc_id": DVC, "gears": []}]


@pytest.fixture
async def session():
    async with aiohttp.ClientSession() as s:
        yield s


def _posts(m):
    """Every POST call in order; aioresponses groups repeats under one key."""
    return [
        [call]
        for key, calls in m.requests.items()
        if key[0] == "POST"
        for call in calls
    ]


# Pairs verified against the RYSE app on real hardware (2026-11-08).
@pytest.mark.parametrize(
    ("bridge", "app"), [(40, 0), (41, 1), (46, 10), (70, 50), (100, 100)]
)
def test_speed_scale_matches_the_app(bridge, app):
    assert speed_to_percent(bridge) == app


@pytest.mark.parametrize(
    ("app", "bridge"), [(0, 40), (1, 41), (10, 46), (50, 70), (100, 100)]
)
def test_percent_to_speed_matches_the_app(app, bridge):
    assert percent_to_speed(app) == bridge


def test_scale_clamps_out_of_range():
    assert percent_to_speed(-5) == SPEED_MIN
    assert percent_to_speed(500) == SPEED_MAX
    assert speed_to_percent(0) == 0
    assert speed_to_percent(999) == 100


def test_every_bridge_speed_survives_a_round_trip():
    # Every value the bridge can hold must map to a percentage and back to a
    # value that displays as the same percentage.
    for speed in range(SPEED_MIN, SPEED_MAX + 1):
        percent = speed_to_percent(speed)
        assert speed_to_percent(percent_to_speed(percent)) == percent


async def test_get_speed(session):
    with aioresponses() as m:
        m.get(LIST_URL, payload=LIST_PAYLOAD)
        m.get(f"{BASE}/speed", payload={"speed": 46})
        bridge = RyseBridge(HOST, session)
        assert await bridge.async_get_speed(GEAR) == 46


async def test_get_speed_percent(session):
    with aioresponses() as m:
        m.get(LIST_URL, payload=LIST_PAYLOAD)
        m.get(f"{BASE}/speed", payload={"speed": 70})
        bridge = RyseBridge(HOST, session)
        assert await bridge.async_get_speed_percent(GEAR) == 50


async def test_set_speed_posts_the_value(session):
    with aioresponses() as m:
        m.get(LIST_URL, payload=LIST_PAYLOAD)
        m.post(f"{BASE}/speed", status=200, body="")
        bridge = RyseBridge(HOST, session)
        await bridge.async_set_speed(GEAR, 70)
        assert _posts(m)[0][0].kwargs["json"] == {"speed": 70}


@pytest.mark.parametrize("bad", [0, 10, 39, 101, 150])
async def test_set_speed_rejects_out_of_range_without_calling_the_bridge(
    session, bad
):
    with aioresponses() as m:
        bridge = RyseBridge(HOST, session)
        with pytest.raises(ValueError, match="between 40 and 100"):
            await bridge.async_set_speed(GEAR, bad)
        assert not m.requests


async def test_set_speed_percent_converts_and_clamps(session):
    with aioresponses() as m:
        m.get(LIST_URL, payload=LIST_PAYLOAD)
        m.post(f"{BASE}/speed", status=200, body="")
        m.post(f"{BASE}/speed", status=200, body="")
        bridge = RyseBridge(HOST, session)
        await bridge.async_set_speed_percent(GEAR, 10)
        await bridge.async_set_speed_percent(GEAR, -20)
        sent = [c[0].kwargs["json"] for c in _posts(m)]
    assert {"speed": 46} in sent
    assert {"speed": 40} in sent


async def test_obstacle_detection_get(session):
    with aioresponses() as m:
        m.get(LIST_URL, payload=LIST_PAYLOAD)
        m.get(f"{BASE}/obstacle_detection", payload={"obstacle_detection": 1})
        m.get(f"{BASE}/obstacle_detection", payload={"obstacle_detection": 0})
        bridge = RyseBridge(HOST, session)
        assert await bridge.async_get_obstacle_detection(GEAR) is True
        assert await bridge.async_get_obstacle_detection(GEAR) is False


@pytest.mark.parametrize(("enabled", "sent"), [(True, 1), (False, 0)])
async def test_obstacle_detection_set(session, enabled, sent):
    with aioresponses() as m:
        m.get(LIST_URL, payload=LIST_PAYLOAD)
        m.post(f"{BASE}/obstacle_detection", status=200, body="")
        bridge = RyseBridge(HOST, session)
        await bridge.async_set_obstacle_detection(GEAR, enabled)
        assert _posts(m)[0][0].kwargs["json"] == {"obstacle_detection": sent}


async def test_unexpected_speed_response_raises(session):
    with aioresponses() as m:
        m.get(LIST_URL, payload=LIST_PAYLOAD)
        m.get(f"{BASE}/speed", payload={"nope": 1})
        bridge = RyseBridge(HOST, session)
        with pytest.raises(RyseResponseError):
            await bridge.async_get_speed(GEAR)


def test_power_type_values_and_unknown():
    assert PowerType(2) is PowerType.BATTERY
    assert PowerType(0) is PowerType.AC_ADAPTER
    assert PowerType(1) is PowerType.USB_CHARGER
    assert PowerType(7) is PowerType.UNKNOWN


def test_gear_helpers():
    gear = Gear.from_dict(
        {
            "id": GEAR,
            "name": "2",
            "position": 0,
            "position_state": 0,
            "online": True,
            "speed": 46,
            "obstacle_detection": 1,
            "power_type": 1,
            "stats": {"gear_not_found": 0},
        }
    )
    assert gear.speed_percent == 10
    assert gear.obstacle_detection_enabled is True
    assert gear.power_source is PowerType.USB_CHARGER
    assert gear.stats == {"gear_not_found": 0}


def test_gear_helpers_when_fields_missing():
    gear = Gear.from_dict({"id": GEAR, "name": "2"})
    assert gear.speed_percent is None
    assert gear.obstacle_detection_enabled is None
    assert gear.power_source is None


def test_device_extra_fields():
    device = Device.from_dict(
        {
            "dvc_id": DVC,
            "dvc_app_version": {"lua": "5.2.0", "homekit": "4.2.6"},
            "dvc_wan_iface": "Ethernet",
            "ifttt_enable": False,
            "dvc_timezone2": {
                "dvc_tz_city": "Chicago,_IL,_United_States",
                "dvc_tz_posix": "CST+6CDT,M3.2.0,M11.1.0",
                "dvc_latitude": 41.9,
                "dvc_longitude": -87.7,
            },
            "gears": [],
        }
    )
    assert device.app_versions == {"lua": "5.2.0", "homekit": "4.2.6"}
    assert device.app_version == "5.2.0"
    assert device.wan_iface == "Ethernet"
    assert device.timezone_city == "Chicago,_IL,_United_States"
    assert device.latitude == 41.9


def test_device_without_version_dict():
    device = Device.from_dict({"dvc_id": DVC, "gears": []})
    assert device.app_versions == {}
    assert device.app_version is None


from pyryse import WIFI_SECURITY, WifiNetwork, WifiStatus  # noqa: E402

WIFICONF_URL = f"http://{HOST}/lua/device/{DVC}/wificonf"
WIFISCAN_URL = f"http://{HOST}/lua/device/{DVC}/wifiscan"


async def test_get_wifi_status(session):
    with aioresponses() as m:
        m.get(LIST_URL, payload=LIST_PAYLOAD)
        m.get(WIFICONF_URL, payload={
            "ssid": "LabNet", "connected": True, "ipv4address": "192.168.0.123"})
        bridge = RyseBridge(HOST, session)
        status = await bridge.async_get_wifi_status()
    assert isinstance(status, WifiStatus)
    assert status.ssid == "LabNet"
    assert status.connected is True
    assert status.ip_address == "192.168.0.123"


def test_wifi_status_never_exposes_a_password_in_repr():
    # The read endpoint has no password field; repr must stay safe regardless.
    status = WifiStatus.from_dict({"ssid": "x", "connected": True})
    assert "password" not in repr(status).lower()


async def test_wifi_scan_parses_results(session):
    with aioresponses() as m:
        m.get(LIST_URL, payload=LIST_PAYLOAD)
        m.get(WIFISCAN_URL, payload={"results": [
            {"ssid": "A", "bssid": "B8:9", "channel": 6, "signal": -55,
             "quality": 35, "quality_max": 70,
             "encryption": {"enabled": True, "wpa": [2, 3],
                            "authentication": ["psk", "sae"], "ciphers": ["ccmp"]}},
            {"ssid": "B", "encryption": {"enabled": False}},
        ]})
        bridge = RyseBridge(HOST, session)
        nets = await bridge.async_wifi_scan()
    assert [n.ssid for n in nets] == ["A", "B"]
    assert isinstance(nets[0], WifiNetwork)
    assert nets[0].channel == 6
    assert nets[0].signal == -55
    assert nets[0].security == "WPA2/WPA3"
    assert nets[0].quality_percent == 50
    assert nets[1].security == "Open"


async def test_wifi_scan_tolerates_empty(session):
    with aioresponses() as m:
        m.get(LIST_URL, payload=LIST_PAYLOAD)
        m.get(WIFISCAN_URL, payload={"results": []})
        bridge = RyseBridge(HOST, session)
        assert await bridge.async_wifi_scan() == []


async def test_set_wifi_config_builds_body(session):
    with aioresponses() as m:
        m.get(LIST_URL, payload=LIST_PAYLOAD)
        m.post(WIFICONF_URL, status=200, body="")
        bridge = RyseBridge(HOST, session)
        await bridge.async_set_wifi_config(
            "LabNet", password="pw", security="WPA2")
        body = [c[0].kwargs["json"] for c in _posts(m)][0]
    assert body == {"ssid": "LabNet", "key": "pw", "security": "WPA2"}


async def test_set_wifi_config_minimal_body(session):
    with aioresponses() as m:
        m.get(LIST_URL, payload=LIST_PAYLOAD)
        m.post(WIFICONF_URL, status=200, body="")
        bridge = RyseBridge(HOST, session)
        await bridge.async_set_wifi_config("Open")
        assert [c[0].kwargs["json"] for c in _posts(m)][0] == {"ssid": "Open"}


async def test_set_wifi_config_rejects_bad_security(session):
    with aioresponses() as m:
        bridge = RyseBridge(HOST, session)
        with pytest.raises(ValueError, match="security must be one of"):
            await bridge.async_set_wifi_config("x", security="WEP")
        assert not m.requests


def test_wifi_security_values():
    assert "WPA2" in WIFI_SECURITY
    assert "None" in WIFI_SECURITY
    assert "WEP" not in WIFI_SECURITY
