"""Implement this protocol to add a vendor without changing the MQTT layer."""
from __future__ import annotations

from typing import Protocol, Sequence

from .model import DeviceDescriptor, Metric, TelemetrySnapshot


class PowerAdapter(Protocol):
    """Read-only adapter contract.

    An adapter handles vendor-specific transport, authorization, and decoding.
    It returns normalized metrics; the SDK owns MQTT Discovery and availability.
    """

    @property
    def device(self) -> DeviceDescriptor: ...

    @property
    def metrics(self) -> Sequence[Metric]: ...

    def snapshot(self) -> TelemetrySnapshot: ...

    def close(self) -> None: ...
