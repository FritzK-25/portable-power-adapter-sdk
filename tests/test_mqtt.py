from __future__ import annotations

import json
from pathlib import Path

import pytest

from portable_power_sdk.demo import DemoAdapter
from portable_power_sdk.mqtt import HomeAssistantMQTTPublisher, publisher_lock


class FakeClient:
    def will_set(self, topic, payload, qos=0, retain=False):
        self.will = (topic, payload, qos, retain)

    def __init__(self):
        self.published = []

    def publish(self, topic, payload=None, qos=0, retain=False):
        self.published.append((topic, payload, qos, retain))


def test_discovery_uses_stable_ids_and_two_availability_topics():
    publisher = HomeAssistantMQTTPublisher(DemoAdapter(), FakeClient())
    metric = DemoAdapter.metrics[0]
    payload = publisher.discovery_payload(metric)
    assert payload["unique_id"] == "portable_power_example_a1b2c3d4e5f6_main_soc"
    assert len(payload["availability"]) == 2
    assert payload["device_class"] == "battery"


def test_live_payload_rounds_soc_to_a_tenth():
    client = FakeClient()
    publisher = HomeAssistantMQTTPublisher(DemoAdapter(), client)
    publisher.publish_current()
    payload = json.loads(client.published[0][1])
    assert payload["main_soc"] == 78.9
    assert payload["collector_state"] == "live"
    assert client.published[1][1] == "online"


def test_publisher_lock_rejects_second_process(tmp_path: Path):
    with publisher_lock(tmp_path):
        with pytest.raises(RuntimeError, match="already running"):
            with publisher_lock(tmp_path):
                pass


@pytest.mark.parametrize("key", ["main_soc", "input-power", "123", "items"])
def test_discovery_renders_every_supported_key(key):
    from jinja2 import Environment
    from portable_power_sdk.model import Metric
    publisher = HomeAssistantMQTTPublisher(DemoAdapter(), FakeClient())
    template = Environment().from_string(publisher.discovery_payload(Metric(key, key))["value_template"])
    assert template.render(value_json={key: 42}) == "42"
    assert template.render(value_json={key: None}) == ""
    assert template.render(value_json={}) == ""


def test_failure_marks_telemetry_offline():
    class BrokenAdapter(DemoAdapter):
        def snapshot(self):
            raise RuntimeError("upstream failed")
    client = FakeClient()
    publisher = HomeAssistantMQTTPublisher(BrokenAdapter(), client)
    with pytest.raises(RuntimeError, match="upstream failed"):
        publisher.publish_current()
    assert client.published[-1] == (publisher.telemetry_topic, "offline", 1, True)


def test_silent_publisher_has_will_and_expiry_without_retained_measurements():
    client = FakeClient()
    publisher = HomeAssistantMQTTPublisher(DemoAdapter(), client, expire_after=30)
    assert client.will == (publisher.availability_topic, "offline", 1, True)
    assert publisher.discovery_payload(DemoAdapter.metrics[0])["expire_after"] == 30
    publisher.announce()
    assert client.published[0] == (publisher.telemetry_topic, "offline", 1, True)
    assert client.published[1] == (publisher.state_topic, "", 1, True)
    publisher.publish_current()
    assert client.published[-2][2:] == (1, False)


def test_old_live_snapshot_is_unavailable():
    from datetime import datetime, timedelta, timezone
    from portable_power_sdk.model import TelemetryHealth, TelemetrySnapshot
    client = FakeClient()
    publisher = HomeAssistantMQTTPublisher(DemoAdapter(), client)
    publisher.publish(TelemetrySnapshot(datetime.now(timezone.utc) - timedelta(minutes=5),
                                        TelemetryHealth.LIVE, {"main_soc": 80}))
    assert json.loads(client.published[-2][1])["main_soc"] is None
    assert client.published[-1][1] == "offline"


def test_invalid_measurement_marks_telemetry_offline():
    from datetime import datetime, timezone
    from portable_power_sdk.model import TelemetryHealth, TelemetrySnapshot
    client = FakeClient()
    publisher = HomeAssistantMQTTPublisher(DemoAdapter(), client)
    with pytest.raises(ValueError):
        publisher.publish(TelemetrySnapshot(datetime.now(timezone.utc), TelemetryHealth.LIVE,
                                            {"main_soc": float("nan")}))
    assert client.published[-1][1] == "offline"
