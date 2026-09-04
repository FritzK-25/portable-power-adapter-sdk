"""Generic Home Assistant MQTT Discovery publisher for any PowerAdapter."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Protocol

import portalocker

from .adapter import PowerAdapter
from .model import Metric, TelemetryHealth, TelemetrySnapshot


class MQTTClient(Protocol):
    def publish(self, topic: str, payload: str | None = None, qos: int = 0, retain: bool = False): ...


@contextmanager
def publisher_lock(directory: Path):
    """Prevent two local bridge processes from publishing the same device state."""
    directory.mkdir(parents=True, exist_ok=True)
    lock = portalocker.Lock(str(directory / "portable-power-publisher.lock"), timeout=0)
    try:
        lock.acquire()
    except portalocker.exceptions.LockException:
        raise RuntimeError("A portable-power MQTT publisher is already running.") from None
    try:
        yield
    finally:
        lock.release()


class HomeAssistantMQTTPublisher:
    """Publish an adapter as one Home Assistant MQTT Discovery device."""

    def __init__(self, adapter: PowerAdapter, client: MQTTClient, *, topic_prefix: str = "portable_power"):
        self.adapter = adapter
        self.client = client
        self.topic_prefix = topic_prefix.rstrip("/")
        self.base = f"{self.topic_prefix}/{adapter.device.id}"
        self._metrics = {metric.key: metric for metric in adapter.metrics}
        if len(self._metrics) != len(adapter.metrics):
            raise ValueError("Metric keys must be unique.")

    @property
    def state_topic(self) -> str:
        return f"{self.base}/state"

    @property
    def availability_topic(self) -> str:
        return f"{self.base}/availability"

    @property
    def telemetry_topic(self) -> str:
        return f"{self.base}/telemetry"

    def discovery_topic(self, metric: Metric) -> str:
        return f"homeassistant/sensor/portable_power_{self.adapter.device.id}/{metric.key}/config"

    def discovery_payload(self, metric: Metric) -> dict:
        config = {
            "name": metric.name,
            "unique_id": f"portable_power_{self.adapter.device.id}_{metric.key}",
            "object_id": f"portable_power_{metric.key}",
            "state_topic": self.state_topic,
            "value_template": (
                "{% if value_json." + metric.key + " is defined and value_json." + metric.key
                + " is not none %}{{ value_json." + metric.key + " }}{% endif %}"
            ),
            "availability_mode": "all",
            "availability": [
                {"topic": self.availability_topic},
                {"topic": self.telemetry_topic},
            ],
            "device": {
                "identifiers": [f"portable_power_{self.adapter.device.id}"],
                "name": self.adapter.device.name,
                "manufacturer": self.adapter.device.manufacturer,
                "model": self.adapter.device.model,
            },
            "origin": {"name": "Portable Power Adapter SDK", "sw_version": "0.1.0"},
        }
        if metric.unit:
            config["unit_of_measurement"] = metric.unit
        if metric.device_class:
            config["device_class"] = metric.device_class
        if metric.state_class:
            config["state_class"] = metric.state_class
        if metric.diagnostic:
            config["entity_category"] = "diagnostic"
        return config

    def announce(self) -> None:
        for metric in self._metrics.values():
            self.client.publish(self.discovery_topic(metric), json.dumps(self.discovery_payload(metric)), qos=1, retain=True)
        self.client.publish(self.availability_topic, "online", qos=1, retain=True)

    def payload(self, snapshot: TelemetrySnapshot) -> dict:
        values = {key: None for key in self._metrics}
        if snapshot.health is TelemetryHealth.LIVE:
            for key, value in snapshot.values.items():
                metric = self._metrics.get(key)
                if metric is None:
                    continue
                values[key] = round(value, metric.precision) if isinstance(value, float) and metric.precision is not None else value
        values["collector_state"] = snapshot.health.value
        values["observed_at"] = snapshot.observed_at.astimezone(timezone.utc).isoformat()
        return values

    def publish(self, snapshot: TelemetrySnapshot) -> None:
        self.client.publish(self.state_topic, json.dumps(self.payload(snapshot), allow_nan=False), qos=0, retain=True)
        live = snapshot.health is TelemetryHealth.LIVE
        self.client.publish(self.telemetry_topic, "online" if live else "offline", qos=1, retain=True)

    def publish_current(self) -> TelemetrySnapshot:
        snapshot = self.adapter.snapshot()
        self.publish(snapshot)
        return snapshot

    def shutdown(self) -> None:
        self.client.publish(self.availability_topic, "offline", qos=1, retain=True)
        self.adapter.close()
