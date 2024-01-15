import json
import requests
import paho.mqtt.client as mqtt
import logging
import sys
import pytz
import uuid
import os
import time
from datetime import datetime
import sqlite3
import re

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                        format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')
from const import CONST_MQTT_HOST,CONST_MQTT_PASSWORD,CONST_MQTT_USERNAME,JSON_LASTMODIFIED_TEXT_FILE,JSON_EARTHQUAKE_TEXT_FILE, SEND_MQTT, LOAD_FILE, RESET_EVERY_RUN, PREFECTURE_JSON, DATABASE

def record_new_earthquake(new_earthquake: str):
    with open(JSON_EARTHQUAKE_TEXT_FILE, "w") as file:
        file.write(new_earthquake)

def get_last_seen_earthquake():
    # Reading the string back from the file
    with open(JSON_EARTHQUAKE_TEXT_FILE, "r") as file:
        read_string = file.read()
    if read_string == None:
        return 0
    else:
        return read_string

def record_new_modified(new_modified: str):
    with open(JSON_LASTMODIFIED_TEXT_FILE, "w") as file:
        file.write(new_modified)

def get_last_modified():
    # Reading the string back from the file
    with open(JSON_LASTMODIFIED_TEXT_FILE, "r") as file:
        read_string = file.read()
    return read_string

def remove_non_numeric(input_str):
    return re.sub(r'\D', '', input_str)

def initialize():
    if RESET_EVERY_RUN==1:
        os.remove(JSON_LASTMODIFIED_TEXT_FILE)
        os.remove(JSON_EARTHQUAKE_TEXT_FILE)



    try:
        # Attempt to open the file in read mode
        with open(JSON_LASTMODIFIED_TEXT_FILE, "r"):
            pass  # If successful, do nothing
    except FileNotFoundError:
        # If the file doesn't exist, create it
        with open(JSON_LASTMODIFIED_TEXT_FILE, "w") as file:
            file.write("")
    try:
        # Attempt to open the file in read mode
        with open(JSON_EARTHQUAKE_TEXT_FILE, "r"):
            pass  # If successful, do nothing
    except FileNotFoundError:
        # If the file doesn't exist, create it
        with open(JSON_EARTHQUAKE_TEXT_FILE, "w") as file:
            file.write("")

def check_last_modified():

    json_url = "https://www.jma.go.jp/bosai/quake/data/list.json"

    # Fetch JSON data from the URL
    last_modified_response = requests.head(json_url,timeout=10)

    last_modified = get_last_modified()

    if last_modified != last_modified_response.headers['Last-Modified']:
        logger.info(f"There's been new earthquakes. Previous last modified: {last_modified} New Last Modified: {last_modified_response.headers['Last-Modified']} ")
        record_new_modified(last_modified_response.headers['Last-Modified'])
        return True
    else:
        logger.info(f"No new earthquakes recently last modified response is {last_modified_response.headers['Last-Modified']}")
        return False


def fetch_and_send_new_earthquakes():

    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()
    json_url = "https://www.jma.go.jp/bosai/quake/data/list.json"

    with open(PREFECTURE_JSON,encoding="utf8") as f:
        PREFECTURE_LIST=json.load(f)

    if LOAD_FILE==1:
        with open("test.json",encoding="utf8") as f:
            quake_list=json.load(f)
    else:
        earthquake_list_response = requests.get(json_url,timeout=10)
        quake_list = json.loads(earthquake_list_response.text)

    last_earthquake_ctt = get_last_seen_earthquake()

    filtered_quakes = [obj for obj in quake_list if obj["ctt"] > last_earthquake_ctt]

    new_earthquake_count = len(filtered_quakes)
    logger.info(f"New earthquake count {new_earthquake_count}")

    filtered_quakes.reverse()

    if new_earthquake_count > 0:
        for quake in filtered_quakes:
            new_quake={}
            for property in ("eid","mag","maxi","en_anm","ctt","rdt","at"):
                new_quake["jma_" + property] = quake[property]
            for prefecture_int in quake["int"]:
                prefecture_name = [obj for obj in PREFECTURE_LIST if obj["iso_code"] == prefecture_int["code"]]
                new_quake["prefecture_name"] = prefecture_name[0]["name"]
                new_quake["prefecture_maxi"] = prefecture_int["maxi"]
                new_quake["mqtt_timestamp"] = str(datetime.now(pytz.timezone('Asia/Tokyo')).isoformat())
                new_quake["mqtt_uuid"] = str(uuid.uuid4())
                new_quake["source"] = json_url
                new_quake["issued_to_mqtt_delay"] = (datetime.now(pytz.timezone('Asia/Tokyo')) - datetime.fromisoformat(new_quake["jma_rdt"])).total_seconds()
                new_quake["jma_observed_to_issued_delay"] = (datetime.fromisoformat(new_quake["jma_rdt"]) - datetime.fromisoformat(new_quake["jma_at"])).total_seconds()
                if SEND_MQTT==1:
                    send_to_mqtt(new_quake)
                cursor.execute('INSERT OR IGNORE INTO earthquakes (eid, arrival_timestamp) VALUES (?, ?)', (new_quake["jma_eid"], new_quake["jma_at"]))
                cursor.execute(f'UPDATE earthquakes set json_timestamp= ? where eid = ?', (new_quake["mqtt_timestamp"], new_quake["jma_eid"]) )
            logger.info(f'Updating ctt from {last_earthquake_ctt} to {quake["ctt"]}')
            record_new_earthquake(quake["ctt"])

    connection.commit()
    connection.close()     

def send_to_mqtt(quake):
    client = mqtt.Client()
    client.username_pw_set(CONST_MQTT_USERNAME,CONST_MQTT_PASSWORD)
    client.connect( CONST_MQTT_HOST, 1883)
    payload = json.dumps(quake)
    logger.info(f"New earthquake details -> {payload}")
    client.publish(f"earthquake/{quake["prefecture_name"].lower()}", payload=payload, qos=0, retain=False)
    client.publish(f"homeassistant/sensor/japan_earthquake_{quake["prefecture_name"].lower()}/state", payload=int(float(remove_non_numeric(quake["prefecture_maxi"]))), qos=0, retain=False)
    client.publish(f"homeassistant/sensor/japan_earthquake_{quake["prefecture_name"].lower()}/state", payload=0, qos=0, retain=False)
    client.disconnect() 

if __name__ == "__main__":
    initialize()
    while True:
        has_been_modified = check_last_modified()
        if (has_been_modified):
            fetch_and_send_new_earthquakes()
        time.sleep(30)