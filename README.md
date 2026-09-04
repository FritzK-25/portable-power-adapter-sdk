# Portable Power Home Assistant Bridge Kit

A local-first, vendor-neutral kit for presenting portable power telemetry in
Home Assistant through MQTT Discovery.

This repository contains a documented MQTT contract, safe example payloads, a
low-state-of-charge automation blueprint, and checks that keep credentials,
recordings, serial numbers, and machine-specific paths out of public commits.
It does **not** contain Bluetooth protocol code, cloud credentials, or a device
controller.

## What this solves

Portable power stations expose data through different mechanisms: Bluetooth,
vendor cloud APIs, or vendor MQTT brokers. An adapter reads one of those sources
and publishes a consistent, local MQTT device:

```text
device or cloud adapter -> MQTT Discovery -> Home Assistant device/entities
```

The adapter owns vendor-specific access. This kit defines what it should publish
and supplies Home Assistant-ready examples.

## Design principles

- **Local-first:** the broker is on the user's network; adapters publish outbound.
- **Safe by default:** telemetry is read-only. Device controls are out of scope.
- **No stale measurements:** a live-telemetry availability topic makes readings
  unavailable when the upstream source goes silent.
- **Stable discovery:** hashed, non-identifying device IDs avoid serial numbers in
  MQTT topics and Home Assistant entity IDs.
- **Useful precision:** charge level is published to one decimal place by default.

## Quick start

1. Configure Home Assistant's MQTT integration and a broker user dedicated to
   the adapter.
2. Have an adapter publish the retained discovery configuration in
   [`examples/discovery-main-soc.json`](examples/discovery-main-soc.json).
3. Publish the state JSON in [`examples/state.json`](examples/state.json) to
   `portable_power/<device_id>/state`.
4. Publish retained `online`/`offline` values to both availability topics shown
   in the discovery example.
5. Import [`blueprints/automation/portable_power_low_soc.yaml`](blueprints/automation/portable_power_low_soc.yaml)
   if you want a generic low-charge alert.

See [the MQTT contract](docs/MQTT-CONTRACT.md) and [security guide](SECURITY.md)
before connecting a real device.

## Adapter projects

Adapters should stay in their own projects because their device protocols,
licenses, and credentials differ. This kit is designed to work with adapters
that publish Home Assistant MQTT Discovery payloads, including local Bluetooth
recorders and vendor-supported MQTT sources.

If you build an adapter, use this contract and open an issue with a sanitized
discovery payload and entity list. Never attach a raw database, MQTT password,
serial number, cloud token, or Bluetooth capture.

## Before publishing changes

Run:

```powershell
python scripts/public_safety_check.py
```

The check rejects common secret formats, private Windows paths, database files,
and likely device identifiers. It is intentionally conservative: review any
reported match rather than weakening the check blindly.

## Scope

This repository is a Home Assistant interoperability kit, not an official
integration for EcoFlow, Jackery, or any other manufacturer. Product names are
used only to describe compatibility discussions.

## License

The original documentation, examples, and blueprint in this repository are
licensed under the [MIT License](LICENSE).
