"""A runnable fake adapter for development, tests, and documentation."""
from __future__ import annotations

from datetime import datetime, timezone

from .model import DeviceDescriptor, Metric, TelemetryHealth, TelemetrySnapshot


class DemoAdapter:
    device = DeviceDescriptor("example_a1b2c3d4e5f6", "Portable Power Example", "Example vendor", "Example station")
    metrics = (
        Metric("main_soc", "Main battery SOC", "%", "battery", "measurement", precision=1),
        Metric("input_power_w", "Input power", "W", "power", "measurement", precision=0),
        Metric("output_power_w", "Output power", "W", "power", "measurement", precision=0),
    )

    def snapshot(self) -> TelemetrySnapshot:
        return TelemetrySnapshot(
            observed_at=datetime.now(timezone.utc),
            health=TelemetryHealth.LIVE,
            values={"main_soc": 78.89179992675781, "input_power_w": 0.0, "output_power_w": 193.0},
        )

    def close(self) -> None:
        pass
