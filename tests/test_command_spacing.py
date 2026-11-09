"""Commands (POSTs) to one bridge are serialised and spaced out.

The bridge silently drops a command when several arrive at once: it answers
200 but one shade never moves. These tests pin the client-side fix.
"""

from __future__ import annotations

import asyncio
import time

import aiohttp
import pytest
from aioresponses import CallbackResult, aioresponses

from pyryse import RyseBridge, RyseResponseError

HOST = "192.168.0.123"
DVC = "xd7JZVuNW"
LIST_URL = f"http://{HOST}/lua/device"
LIST_PAYLOAD = [{"dvc_name": "RYSE SmartBridge", "dvc_id": DVC, "gears": []}]
GEARS = ["c34ae8d8c52b", "fa79e73b5448", "c8f8f985eefb", "d1bf12f4ab24"]


def position_url(gear: str) -> str:
    return f"http://{HOST}/lua/device/{DVC}/gear/{gear}/position"


@pytest.fixture
async def session():
    async with aiohttp.ClientSession() as s:
        yield s


class Recorder:
    """Mock bridge handler that records timing and overlap of requests."""

    def __init__(self, work: float = 0.02, status: int = 200) -> None:
        self.work = work
        self.status = status
        self.in_flight = 0
        self.max_in_flight = 0
        self.starts: list[float] = []
        self.ends: list[float] = []

    async def handle(self, url, **kwargs) -> CallbackResult:
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        self.starts.append(time.monotonic())
        await asyncio.sleep(self.work)
        self.ends.append(time.monotonic())
        self.in_flight -= 1
        return CallbackResult(status=self.status, body="")


async def test_concurrent_commands_are_sent_one_at_a_time_and_spaced(session):
    rec = Recorder()
    with aioresponses() as m:
        m.get(LIST_URL, payload=LIST_PAYLOAD, repeat=True)
        for gear in GEARS:
            m.post(position_url(gear), callback=rec.handle)
        bridge = RyseBridge(HOST, session, command_interval=0.1)
        await asyncio.gather(
            *(bridge.async_set_position(gear, 100) for gear in GEARS)
        )

    assert len(rec.starts) == len(GEARS)
    assert rec.max_in_flight == 1
    # Each command starts at least command_interval after the previous ended.
    for prev_end, start in zip(rec.ends[:-1], rec.starts[1:], strict=True):
        assert start - prev_end >= 0.09


async def test_zero_interval_still_serialises(session):
    rec = Recorder()
    with aioresponses() as m:
        m.get(LIST_URL, payload=LIST_PAYLOAD, repeat=True)
        for gear in GEARS:
            m.post(position_url(gear), callback=rec.handle)
        bridge = RyseBridge(HOST, session, command_interval=0)
        await asyncio.gather(
            *(bridge.async_set_position(gear, 0) for gear in GEARS)
        )

    assert len(rec.starts) == len(GEARS)
    assert rec.max_in_flight == 1


async def test_reads_are_not_throttled(session):
    with aioresponses() as m:
        m.get(LIST_URL, payload=LIST_PAYLOAD, repeat=True)
        m.post(position_url(GEARS[0]), status=200, body="")
        m.get(
            position_url(GEARS[0]),
            payload={"position": 0, "position_state": 0},
        )
        bridge = RyseBridge(HOST, session, command_interval=5)
        await bridge.async_set_position(GEARS[0], 0)
        started = time.monotonic()
        await bridge.async_get_position(GEARS[0])
        elapsed = time.monotonic() - started

    assert elapsed < 1


async def test_failed_command_still_counts_for_spacing(session):
    failing = Recorder(status=500)
    ok = Recorder()
    with aioresponses() as m:
        m.get(LIST_URL, payload=LIST_PAYLOAD, repeat=True)
        m.post(position_url(GEARS[0]), callback=failing.handle)
        m.post(position_url(GEARS[1]), callback=ok.handle)
        bridge = RyseBridge(HOST, session, command_interval=0.1)
        with pytest.raises(RyseResponseError):
            await bridge.async_set_position(GEARS[0], 0)
        await bridge.async_set_position(GEARS[1], 0)

    assert ok.starts[0] - failing.ends[0] >= 0.09


def test_negative_interval_rejected():
    with pytest.raises(ValueError):
        RyseBridge(HOST, None, command_interval=-1)  # type: ignore[arg-type]
