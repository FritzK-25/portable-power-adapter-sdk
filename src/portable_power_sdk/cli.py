"""Inspect the SDK contract without connecting to a real device or broker."""
from __future__ import annotations

import argparse
import json

from .demo import DemoAdapter
from .mqtt import HomeAssistantMQTTPublisher


class PrintClient:
    def will_set(self, topic, payload, qos=0, retain=False):
        pass

    def publish(self, topic, payload=None, qos=0, retain=False):
        print(json.dumps({"topic": topic, "payload": json.loads(payload) if payload and payload.startswith("{") else payload,
                          "qos": qos, "retain": retain}, indent=2))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Portable Power Adapter SDK demo")
    parser.add_argument("command", choices=("describe", "demo"))
    args = parser.parse_args(argv)
    publisher = HomeAssistantMQTTPublisher(DemoAdapter(), PrintClient())
    if args.command == "describe":
        for metric in DemoAdapter.metrics:
            print(json.dumps(publisher.discovery_payload(metric), indent=2))
    else:
        publisher.publish_current()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
