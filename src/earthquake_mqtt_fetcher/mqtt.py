from __future__ import annotations

from collections.abc import Iterable

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

from earthquake_mqtt_fetcher.config import settings
from earthquake_mqtt_fetcher.logging import get_logger

log = get_logger("mqtt")

Message = tuple[str, str | int, bool]


def publish(messages: Iterable[Message]) -> None:
    client = mqtt.Client(CallbackAPIVersion.VERSION2)
    client.username_pw_set(settings.mqtt_username, settings.mqtt_password)
    try:
        client.connect(settings.mqtt_host, settings.mqtt_port)
    except OSError:
        log.exception("Error connecting to MQTT broker %s:%s", settings.mqtt_host, settings.mqtt_port)
        return
    client.loop_start()
    try:
        for topic, payload, retain in messages:
            try:
                result = client.publish(topic, payload=payload, qos=2, retain=retain)
                result.wait_for_publish()
                if result.rc != mqtt.MQTT_ERR_SUCCESS:
                    log.error("Failed to publish to %s (rc=%s)", topic, result.rc)
            except (ValueError, RuntimeError):
                log.exception("Error publishing to %s", topic)
    finally:
        client.loop_stop()
        try:
            client.disconnect()
        except OSError:
            log.exception("Error disconnecting from MQTT broker")
