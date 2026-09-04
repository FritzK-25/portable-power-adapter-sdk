# Contributing

Contributions should improve the portable-power MQTT contract, Home Assistant
examples, documentation, or public-safety checks.

Before opening a pull request:

1. Run `python scripts/public_safety_check.py`.
2. Confirm all IDs, hosts, and values are fabricated or generic.
3. Add a short note describing the device class, telemetry source, and whether
   the adapter is read-only.
4. Do not add proprietary protocol dumps or source code unless you have clear
   permission and its license is compatible with MIT.

Use issues for proposals to add vendors or entity types. Attach sanitized MQTT
discovery JSON, not captures or recordings.
