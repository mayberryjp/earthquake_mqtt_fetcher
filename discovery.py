from const import CONST_MQTT_HOST,CONST_MQTT_PASSWORD,CONST_MQTT_USERNAME,PREFECTURE_JSON
import paho.mqtt.client as mqtt
import json

class JapanEarthquakeSensors:
    def __init__(self, name):
        self.name = name
        self.device_class = None
        self.state_topic = f"homeassistant/sensor/japan_earthquake_{name.lower()}/state"
        self.unique_id = f"japan_earthquake_{name.lower()}"
        self.device = {
            "identifiers": [f"japan_earthquake_{name.lower()}"],
            "name": "Japan Prefecture Earthquake Intensity"
        }
        self.qos = 2  # Add this line to specify QoS level

    def to_json(self):
        return {
            "name": self.name,
            "device_class": self.device_class,
            "state_topic": self.state_topic,
            "unique_id": self.unique_id,
            "device": self.device,
            "qos": self.qos  # Add this line to include QoS in the discovery message
        }

with open(PREFECTURE_JSON, encoding="utf8") as f:
    PREFECTURE_LIST = json.load(f)

# Create MQTT client
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
client.username_pw_set(CONST_MQTT_USERNAME, CONST_MQTT_PASSWORD)
client.connect(CONST_MQTT_HOST, 1883)

# Start the loop for background network processing
client.loop_start()

# Publish prefecture data
for prefecture in PREFECTURE_LIST:
    print(f"Iterating prefecture {prefecture['name']}")
    
    prefecture_sensor = JapanEarthquakeSensors(prefecture["name"])
    # Convert dictionary to JSON string
    serialized_message = json.dumps(prefecture_sensor.to_json())
    print(f"Sending sensor -> {serialized_message}")
    
    # Publish and wait for QoS 2 handshake to complete
    ret = client.publish(f"homeassistant/sensor/japan_earthquake_{prefecture['name'].lower()}/config", payload=serialized_message, qos=2, retain=True)
    ret.wait_for_publish()
    
    ret = client.publish(f"homeassistant/sensor/japan_earthquake_{prefecture['name'].lower()}/state", payload=0, qos=2, retain=True)
    ret.wait_for_publish()

# Publish "Any" prefecture data
any_prefecture_sensor = JapanEarthquakeSensors("Any")
serialized_message = json.dumps(any_prefecture_sensor.to_json())
print(f"Sending sensor -> {serialized_message}")

ret = client.publish(f"homeassistant/sensor/japan_earthquake_any/config", payload=serialized_message, qos=2, retain=True)
ret.wait_for_publish()

ret = client.publish(f"homeassistant/sensor/japan_earthquake_any/state", payload=0, qos=2, retain=True)
ret.wait_for_publish()

# Stop the loop and disconnect
client.loop_stop()