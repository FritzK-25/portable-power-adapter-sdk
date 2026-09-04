# MQTT contract

This contract lets an adapter create a portable-power device in Home Assistant
using MQTT Discovery.

## Topic layout

```text
homeassistant/sensor/portable_power_<device_id>/<entity_key>/config
portable_power/<device_id>/state
portable_power/<device_id>/availability
portable_power/<device_id>/telemetry
```

`<device_id>` must be a stable non-identifying value, for example the first
12 characters of a SHA-256 digest held only by the adapter. Do not use a serial
number or a Bluetooth address.

## Availability

The adapter publishes retained `online` or `offline` to `availability` for its
own process health. It publishes retained `online` only while it has current
telemetry to `telemetry`.

Measurements must require both topics. This keeps a device visible for diagnosis
while preventing old power or charge readings from looking current.

## State payload

Publish JSON to the retained state topic. Omit unavailable measurements or set
them to `null`; discovery value templates should then emit an empty state.

```json
{
  "main_soc": 78.9,
  "input_power_w": 0,
  "output_power_w": 193,
  "collector_state": "recording"
}
```

Charge level defaults to one decimal place. An adapter may expose a precision
setting, but should avoid high-precision binary floating-point output.

## Minimum entities

| Key | Unit | Home Assistant class |
|---|---:|---|
| `main_soc` | `%` | `battery`, `measurement` |
| `input_power_w` | `W` | `power`, `measurement` |
| `output_power_w` | `W` | `power`, `measurement` |
| `collector_state` | — | diagnostic sensor |

Optional entities include battery temperature, fault status, frame timestamp,
and energy totals. Mark undocumented vendor codes as diagnostic.
