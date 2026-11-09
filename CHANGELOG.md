# Changelog

## 0.4.2

- **Fix:** moving several shades at once could leave one behind. The bridge
  silently drops a command when several arrive together: it returns `200`,
  but that shade never moves. Seen with four shades from Home Assistant, where
  each attempt missed a different one. `RyseBridge` now sends commands (all
  POST requests) one at a time, at least `command_interval` seconds apart.
- Added the `command_interval` argument to `RyseBridge` (default
  `DEFAULT_COMMAND_INTERVAL`, 0.5 s, verified with four shades). `0` keeps
  commands one at a time with no gap. Reads (GET) are not throttled.

## 0.4.0

- Added Wi-Fi support (the bridge runs Wi-Fi and Ethernet at once, so these
  work over a wired connection): `async_get_wifi_status`, `async_wifi_scan` and
  `async_set_wifi_config`, with `WifiStatus`, `WifiNetwork` and the
  `WIFI_SECURITY` set. `WifiNetwork.security` summarises the encryption object
  as `Open`/`WPA2`/`WPA2/WPA3`/etc., and `quality_percent` normalises the link
  quality. The read endpoint returns only the current connection (SSID,
  connected, IP) - the bridge does not expose the stored password.
- `docs/PROTOCOL.md` documents the real `wifiscan` and `wificonf` response
  shapes.

## 0.3.0

- Added `async_get_speed`, `async_set_speed`, `async_get_speed_percent` and
  `async_set_speed_percent`. Speed is 40-100 on the bridge and 0-100% in the
  RYSE app; `speed_to_percent` and `percent_to_speed` convert, using the
  mapping verified against the app. `async_set_speed` raises `ValueError`
  outside 40-100.
- Added `async_get_obstacle_detection` and `async_set_obstacle_detection`.
- Added the `PowerType` enum and `Gear.power_source`, plus
  `Gear.speed_percent`, `Gear.obstacle_detection_enabled` and `Gear.stats`.
- `Device` now carries `app_versions`, `ifttt_enable`, `wan_iface`,
  `timezone_city`, `timezone_posix`, `latitude` and `longitude`.
- **Fix:** `Device.app_version` used to hold the Python repr of a dictionary,
  because the bridge reports a dictionary of component versions. The full
  dictionary is now `Device.app_versions`, and `app_version` returns the main
  (`lua`) component's version.
- Documented in `docs/PROTOCOL.md`: the settings endpoints, the settle delay,
  power-type values, and that routines are not exposed locally.

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
