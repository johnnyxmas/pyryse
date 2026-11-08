# Changelog

## 0.2.0

- `RyseBridge.async_get_device()` now fetches the detailed
  `/lua/device/<dvc_id>` endpoint instead of the sparse list endpoint, so
  `Gear.battery`, `Gear.fw_version`, `Gear.hw_version`, `Gear.serial_number`
  and the device's own `fw_version`/`hw_version`/`mac` are populated.
  Verified against real hardware (battery 60-73%, per-gear firmware/hardware
  versions).
- The bridge's `dvc_id` is resolved once (from the list endpoint, which needs
  no id) and cached; subsequent calls do not re-fetch it.
- No change to the public method signatures or the position-inversion
  behaviour; existing code continues to work, now with richer `Gear`/`Device`
  objects.

## 0.1.0

- Initial release: `RyseBridge` with `async_get_device`, `async_get_gears`,
  `async_get_position`, `async_set_position`. Typed `Device`/`Gear`/`GearState`
  models, optional serial-based auth, typed exceptions.
