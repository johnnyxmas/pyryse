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

## Other endpoints (not used by pyryse)

The setup page also uses `GET /lua/device/<dvc_id>/wifiscan` and
`POST /lua/device/<dvc_id>/wificonf` for Wi-Fi provisioning. pyryse does not
touch these.
