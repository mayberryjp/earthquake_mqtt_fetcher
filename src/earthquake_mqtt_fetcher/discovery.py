from __future__ import annotations

import json
from typing import Any

from earthquake_mqtt_fetcher import mqtt, prefectures
from earthquake_mqtt_fetcher.config import settings
from earthquake_mqtt_fetcher.logging import configure_logging, get_logger

log = get_logger("discovery")

DEVICE: dict[str, Any] = {
    "identifiers": ["japan_earthquake"],
    "name": "Japan Earthquake Intensity",
    "manufacturer": "Japan Meteorological Agency",
    "model": "Seismic Intensity (shindo)",
}


def _config_payload(name: str) -> dict[str, Any]:
    slug = name.lower()
    return {
        "name": f"Japan Earthquake {name}",
        "state_topic": f"homeassistant/sensor/japan_earthquake_{slug}/state",
        "unique_id": f"japan_earthquake_{slug}",
        "object_id": f"japan_earthquake_{slug}",
        "unit_of_measurement": "shindo",
        "state_class": "measurement",
        "icon": "mdi:pulse",
        "device": DEVICE,
        "qos": 2,
    }


def build_messages() -> list[mqtt.Message]:
    names = [str(pref["name"]) for pref in prefectures.load_prefectures()]
    names.append("Any")
    messages: list[mqtt.Message] = []
    for name in names:
        slug = name.lower()
        config_topic = f"homeassistant/sensor/japan_earthquake_{slug}/config"
        state_topic = f"homeassistant/sensor/japan_earthquake_{slug}/state"
        messages.append((config_topic, json.dumps(_config_payload(name)), True))
        messages.append((state_topic, 0, True))
    return messages


def main() -> None:
    configure_logging(settings.log_level)
    messages = build_messages()
    log.info("Publishing %s Home Assistant discovery messages", len(messages))
    mqtt.publish(messages)


if __name__ == "__main__":
    main()
