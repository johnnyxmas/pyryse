# pyryse

Local (no-cloud) async Python client for [RYSE SmartShade](https://helloryse.com)
motorized shades, driven through a RYSE **SmartBridge** over its LAN HTTP API.

Built to back the Home Assistant integration
[`ha-ryse-local`](https://github.com/johnnyxmas/ha-ryse-local), but usable on its
own. Not affiliated with or endorsed by RYSE; "RYSE", "SmartBridge" and
"SmartShade" are trademarks of their owner.

## Install

```sh
pip install pyryse
```

## Usage

```python
import aiohttp
from pyryse import RyseBridge

async def main():
    async with aiohttp.ClientSession() as session:
        bridge = RyseBridge("192.168.0.123", session)
        device = await bridge.async_get_device()
        for gear in device.gears:
            print(gear.name, gear.position, gear.position_state.name,
                  gear.online, gear.battery)

        # Move a shade. Bridge scale: 0 = open, 100 = closed.
        await bridge.async_set_position(device.gears[0].id, 0)   # open
```

If your bridge has local security enabled, pass the serial:
`RyseBridge(host, session, serial="...")`.

## Position convention

The bridge's `position` is the **inverse** of Home Assistant's cover scale:

* `0` = fully open
* `100` = fully closed

`pyryse` reports the bridge's native values unchanged; invert in your consumer
if you need HA semantics. See [`docs/PROTOCOL.md`](docs/PROTOCOL.md) for the full
reverse-engineered API.

## Per-gear settings

Speed and obstacle detection are per shade.

```python
from pyryse import PowerType

gear_id = device.gears[0].id

# Speed, on the RYSE app's 0-100% scale.
await bridge.async_set_speed_percent(gear_id, 10)
print(await bridge.async_get_speed_percent(gear_id))

# Obstacle detection.
await bridge.async_set_obstacle_detection(gear_id, True)
print(await bridge.async_get_obstacle_detection(gear_id))

# Read-only helpers on a Gear from async_get_device():
gear = device.gears[0]
gear.speed_percent                 # app percentage, or None
gear.obstacle_detection_enabled    # bool, or None
gear.power_source is PowerType.BATTERY
```

- **Speed:** the bridge accepts 40-100, and the app shows 0-100% over that
  range (`app % = (bridge - 40) / 60 * 100`). `async_set_speed` takes the raw
  bridge value and raises `ValueError` outside 40-100, since the bridge answers
  with a bare HTTP 405. `speed_to_percent` and `percent_to_speed` convert. Not
  every percentage survives a round trip: the bridge has 61 values for 101
  percentages.
- **Power type:** `PowerType.BATTERY` (2), `AC_ADAPTER` (0) and `USB_CHARGER`
  (1). These are inferred from watching one shade's power source change; RYSE
  doesn't document them. Unrecognised values give `PowerType.UNKNOWN`.
- **Timing:** settings take a few seconds to apply, so a read right after a
  write may show the old value.

**Routines** (the app's name for scenes) are not available through the local
API. Their endpoints are not known.

## License

MIT
