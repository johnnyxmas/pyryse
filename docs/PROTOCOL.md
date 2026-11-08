# RYSE SmartBridge local HTTP API

Reverse-engineered from a RYSE SmartBridge (bridge firmware ~2023, SmartShade
firmware `5.3.2`) by observing its own setup web page, its responses, and one
capture of the RYSE iOS app controlling a shade over the LAN. Documented here
for interoperability; no RYSE code or documentation was used.

All endpoints are plain HTTP on port 80. When the bridge's local-security
option is **off** (the default — there is no app toggle to enable it), no
authentication is required. When on, requests carry an `Authorization: <serial>`
header.

## Endpoints

### `GET /lua/device`
Returns a one-element JSON array; element 0 is the device object.

### `GET /lua/device/<dvc_id>`
Returns the device object directly. Device fields:

| field | meaning |
|---|---|
| `dvc_id` | bridge id (used in all gear paths) |
| `dvc_name`, `dvc_mac`, `dvc_ip` | identity / addressing |
| `dvc_online` | bridge online |
| `dvc_fw_version`, `dvc_hw_version`, `dvc_app_version` | versions |
| `local_security_enable` | whether auth is required (observed `false`) |
| `dvc_timezone2` | `{dvc_tz_city, dvc_tz_posix, dvc_longitude, dvc_latitude, ...}` |
| `gears` | array of gear objects |

Gear fields: `id`, `name`, `position` (0-100), `position_state`, `online`,
`power_level` (battery %), `speed`, `gear_type`, `power_type`,
`obstacle_detection`, `machine_state`, `fw_version`, `hw_version`,
`msp_fw_version`, `serial_number`, `stats`.

### `GET /lua/device/<dvc_id>/gear/<gear_id>/position`
Returns `{"position_state": N, "position": N}`.

### `POST /lua/device/<dvc_id>/gear/<gear_id>/position`
Body `{"position": 0-100}`. Moves the gear. Returns `200` with an empty body.

## Semantics

**Position** (bridge-native, the inverse of Home Assistant's cover scale):

* `0` = fully **open**
* `100` = fully **closed**

**`position_state`:**

* `0` = idle / settled
* `1` = moving toward `0` (opening)
* `2` = moving toward `100` (closing)

An **offline** gear (`online: false`) may report a stale non-idle
`position_state` and a stale `position`; trust `online` first.

The motor is slow and reports intermediate positions as it travels, so poll
after issuing a move rather than assuming it completes immediately.

## Error behaviour

| condition | status |
|---|---|
| unknown gear id | `400` |
| unknown device id | `405` |
| wrong body key (e.g. `pos`) / non-numeric position | `405` |
| malformed JSON body | `500` (parsed before routing) |

## Per-gear settings (verified 2026-11-08, firmware 5.3.2)

| setting | read | write | notes |
|---|---|---|---|
| `speed` (0-100 %) | `GET .../gear/<id>/speed` -> `{"speed":N}` | `POST .../gear/<id>/speed` body `{"speed":N}` | Accepted bridge range is 40-100; writes of 0, 10, 20, 39 and 150 are rejected with 405. The app's percentage is linear over that range: app % = (bridge - 40) / 60 * 100, so bridge = 40 + 0.6 * app %. Verified against the app: bridge 40 = 0%, 41 = 1%, 70 = 50%, 100 = 100%. Each gear has its own value. |
| `obstacle_detection` (on/off) | `GET .../gear/<id>/obstacle_detection` -> `{"obstacle_detection":N}` | `POST .../gear/<id>/obstacle_detection` body `{"obstacle_detection":0\|1}` | Accepted 0 and 1. |

**Settings apply after a delay of a few seconds.** A read immediately after a
write can return the previous value. Poll before concluding a write failed.

Per the RYSE app's behaviour (not independently verified here): on firmware
before 5.0.2, setting `speed` above 66 % disables obstacle detection. All gears
here run 5.3.2, so this rule was not tested.

## Other gear and device fields

- `power_type`: 2 on every gear. Battery is the likely meaning, since gears report
  `power_level`, but this is unconfirmed.
- `machine_state`: 3 on every gear, unchanged across the sweep. Meaning unknown.
- `gear_type`: 2 on every gear. Meaning unknown.
- `stats`: `{"gear_not_found": 0}` on every gear.
- `ifttt_enable`: false. `dvc_wan_iface`: "Ethernet". Read-only in this pass.
- `dvc_app_version`: bnrf 5.2.15, homekit 4.2.6, lua/mqttc/nrfi 5.2.0.

## Routines (scenes): not found locally

About 15 guessed GET paths (`routines`, `scenes`, `routine`, `routinelist`,
`automation`, `action`, and variants under the device and `/lua/`) all return
405. The setup page's own JavaScript uses only `/lua/device`, `wifiscan` and
`wificonf`. Routines are probably stored and run by the app or the cloud.
Confirming this needs a capture of the app creating and running a routine.

## Other endpoints (not used by pyryse)

The setup page also uses `GET /lua/device/<dvc_id>/wifiscan` and
`POST /lua/device/<dvc_id>/wificonf` for Wi-Fi provisioning. pyryse does not
touch these.
