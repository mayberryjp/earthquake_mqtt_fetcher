from const import CONST_MQTT_HOST,CONST_MQTT_PASSWORD,CONST_MQTT_USERNAME,PREFECTURE_JSON
import paho.mqtt.client as mqtt
import json

# def on_connect(client, userdata, flags, rc):
#     print(f"Connected with result code {rc}")
#     # Publish the message when connected
#     client.publish(topic, serialized_message)

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

    def to_json(self):
        return {
            "name": self.name,
            "device_class": self.device_class,
            "state_topic": self.state_topic,
            "unique_id": self.unique_id,
            "device": self.device
        }

with open(PREFECTURE_JSON,encoding="utf8") as f:
    PREFECTURE_LIST=json.load(f)


# Create MQTT client
client = mqtt.Client()
client.username_pw_set(CONST_MQTT_USERNAME,CONST_MQTT_PASSWORD)
client.connect( CONST_MQTT_HOST, 1883)


for prefecture in PREFECTURE_LIST:
    print(f"Iterating prefecture {prefecture["name"]}")
    
    prefecture_sensor=JapanEarthquakeSensors(prefecture["name"])
    # Convert dictionary to JSON string
    serialized_message = json.dumps(prefecture_sensor.to_json())
    print(f"Sending sensor -> {serialized_message}")
   # client.publish(f"homeassistant/sensor/japan_earthquake_{prefecture["name"].lower()}/config", payload=serialized_message, qos=0, retain=True)
    #client.publish(f"homeassistant/sensor/japan_earthquake_{prefecture["name"].lower()}/state", payload=0, qos=0, retain=False)

any_prefecture_sensor=JapanEarthquakeSensors("Any")
serialized_message = json.dumps(any_prefecture_sensor.to_json())
print(f"Sending sensor -> {serialized_message}")
client.publish(f"homeassistant/sensor/japan_earthquake_any/config", payload=serialized_message, qos=0, retain=True)
client.publish(f"homeassistant/sensor/japan_earthquake_any/state", payload=0, qos=0, retain=False)

# Disconnect the client after publishing
client.disconnect()