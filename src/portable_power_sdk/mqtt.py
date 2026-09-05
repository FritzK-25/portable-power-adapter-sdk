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
    def will_set(self, topic: str, payload: str, qos: int = 0, retain: bool = False): ...

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

    def __init__(self, adapter: PowerAdapter, client: MQTTClient, *, topic_prefix: str = "portable_power",
                 expire_after: int = 90):
        """Construct before connecting the MQTT client so its last will takes effect."""
        if isinstance(expire_after, bool) or not isinstance(expire_after, int) or expire_after <= 0:
            raise ValueError("expire_after must be a positive integer number of seconds.")
        self.expire_after = expire_after
        self.adapter = adapter
        self.client = client
        self.topic_prefix = topic_prefix.rstrip("/")
        self.base = f"{self.topic_prefix}/{adapter.device.id}"
        self._metrics = {metric.key: metric for metric in adapter.metrics}
        if len(self._metrics) != len(adapter.metrics):
            raise ValueError("Metric keys must be unique.")
        self.client.will_set(self.availability_topic, "offline", qos=1, retain=True)

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
        key = json.dumps(metric.key)
        value = f"value_json[{key}]"
        config = {
            "name": metric.name,
            "unique_id": f"portable_power_{self.adapter.device.id}_{metric.key}",
            "object_id": f"portable_power_{metric.key}",
            "state_topic": self.state_topic,
            "expire_after": self.expire_after,
            "value_template": (
                "{% if " + key + " in value_json and " + value
                + " is not none %}{{ " + value + " }}{% endif %}"
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
        # Invalidate old sessions and remove state retained by earlier SDK versions.
        self.client.publish(self.telemetry_topic, "offline", qos=1, retain=True)
        self.client.publish(self.state_topic, "", qos=1, retain=True)
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
        age = (datetime.now(timezone.utc) - snapshot.observed_at).total_seconds()
        if snapshot.health is TelemetryHealth.LIVE and not 0 <= age < self.expire_after:
            snapshot = TelemetrySnapshot(snapshot.observed_at, TelemetryHealth.STALE)
        try:
            encoded = json.dumps(self.payload(snapshot), allow_nan=False)
        except Exception:
            self.client.publish(self.telemetry_topic, "offline", qos=1, retain=True)
            raise
        # Retained measurements replayed after an HA restart would reset expiry.
        self.client.publish(self.state_topic, encoded, qos=1, retain=False)
        live = snapshot.health is TelemetryHealth.LIVE
        self.client.publish(self.telemetry_topic, "online" if live else "offline", qos=1, retain=True)

    def publish_current(self) -> TelemetrySnapshot:
        try:
            snapshot = self.adapter.snapshot()
        except Exception:
            self.client.publish(self.telemetry_topic, "offline", qos=1, retain=True)
            raise
        self.publish(snapshot)
        return snapshot

    def shutdown(self) -> None:
        self.client.publish(self.availability_topic, "offline", qos=1, retain=True)
        self.adapter.close()
