"""The stable, vendor-neutral data model exposed by every adapter."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from numbers import Real
import re
from typing import Mapping


DEVICE_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{2,63}$")


class TelemetryHealth(StrEnum):
    """Whether measurements can be treated as current."""

    LIVE = "live"
    STALE = "stale"
    OFFLINE = "offline"
    ERROR = "error"


@dataclass(frozen=True)
class DeviceDescriptor:
    """Public device metadata. ``id`` must never contain a serial or MAC address."""

    id: str
    name: str
    manufacturer: str = "Portable power"
    model: str = "Unknown"

    def __post_init__(self) -> None:
        if not DEVICE_ID.fullmatch(self.id):
            raise ValueError("Device IDs must be opaque lowercase identifiers, 3-64 characters long.")


@dataclass(frozen=True)
class Metric:
    """One normalized measurement published through MQTT Discovery."""

    key: str
    name: str
    unit: str = ""
    device_class: str = ""
    state_class: str = ""
    precision: int | None = None
    diagnostic: bool = False

    def __post_init__(self) -> None:
        if not DEVICE_ID.fullmatch(self.key):
            raise ValueError("Metric keys must be lowercase identifiers, 3-64 characters long.")
        if self.precision is not None and self.precision < 0:
            raise ValueError("Metric precision cannot be negative.")


@dataclass(frozen=True)
class TelemetrySnapshot:
    """A single adapter observation, ready for a publisher to serialize."""

    observed_at: datetime
    health: TelemetryHealth
    values: Mapping[str, Real | str | bool | None] = field(default_factory=dict)
    detail: str = ""

    def __post_init__(self) -> None:
        if self.observed_at.tzinfo is None:
            raise ValueError("Snapshot timestamps must include a timezone.")
