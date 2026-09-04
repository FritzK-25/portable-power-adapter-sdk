from __future__ import annotations

import json
from pathlib import Path

import pytest

from portable_power_sdk.demo import DemoAdapter
from portable_power_sdk.mqtt import HomeAssistantMQTTPublisher, publisher_lock


class FakeClient:
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
