# Security and privacy

## Public-repository rules

Do not commit:

- MQTT usernames, passwords, hostnames, IP addresses, or TLS material;
- cloud tokens, API keys, account IDs, or device-pairing data;
- device serial numbers, Bluetooth MAC addresses, or raw captures;
- SQLite recordings, exports, screenshots, or logs from a live installation;
- real local paths, such as `C:\Users\<name>\...`.

Use placeholders such as `<broker-host>`, `<device-id>`, and `<mqtt-user>` in
documentation. A device ID should be a one-way hash or a deliberately invented
example; never derive it from a serial number shown in a public artifact.

## MQTT permissions

Create a dedicated broker account per adapter. Limit it to its own state,
availability, and Home Assistant discovery topics. Do not grant administrative
or wildcard write permissions.

## Control policy

This kit is telemetry-only. A future control extension must document its command
allowlist, authentication model, confirmation behavior, and observed device
acknowledgements before it is accepted.

## Reporting a vulnerability

Please report suspected credential exposure or unsafe publishing behavior
privately to the repository maintainer. Do not open a public issue containing a
token, serial number, capture, or database.
