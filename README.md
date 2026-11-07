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
            print(gear.name, gear.position, gear.position_state.name, gear.online)

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

## License

MIT
