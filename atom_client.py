import json
import requests
import paho.mqtt.client as mqtt
import logging
import sys
import pytz
import uuid
import os
import feedparser
import xmltodict
import time
import sqlite3
from datetime import datetime, timedelta
from random import randrange
import re

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                        format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')
from const import CONST_MQTT_HOST,CONST_MQTT_PASSWORD,CONST_MQTT_USERNAME,ATOM_LASTMODIFIED_TEXT_FILE,ATOM_EARTHQUAKE_TEXT_FILE, SEND_MQTT, LOAD_FILE, RESET_EVERY_RUN, PREFECTURE_JSON, DATABASE, VERSION, SQLLITE_TIMEOUT

def record_new_earthquake(new_earthquake: str):
    with open(ATOM_EARTHQUAKE_TEXT_FILE, "w") as file:
        file.write(new_earthquake)

def get_last_seen_earthquake():
    # Reading the string back from the file
    with open(ATOM_EARTHQUAKE_TEXT_FILE, "r") as file:
        read_string = file.read()
    if read_string == None:
        return 0
    else:
        return read_string

def record_new_modified(new_modified: str):
    with open(ATOM_LASTMODIFIED_TEXT_FILE, "w") as file:
        file.write(new_modified)

def get_last_modified():
    # Reading the string back from the file
    with open(ATOM_LASTMODIFIED_TEXT_FILE, "r") as file:
        read_string = file.read()
    return read_string

def remove_non_numeric(input_str):
    return re.sub(r'\D', '', input_str)

def initialize():
    if RESET_EVERY_RUN==1:
        try:
            os.remove(ATOM_LASTMODIFIED_TEXT_FILE)
            os.remove(ATOM_EARTHQUAKE_TEXT_FILE)
            pass
        except FileNotFoundError:
            pass

    try:
        # Attempt to open the file in read mode
        with open(ATOM_LASTMODIFIED_TEXT_FILE, "r"):
            pass  # If successful, do nothing
    except FileNotFoundError:
        # If the file doesn't exist, create it
        with open(ATOM_LASTMODIFIED_TEXT_FILE, "w") as file:
            file.write("")
    try:
        # Attempt to open the file in read mode
        with open(ATOM_EARTHQUAKE_TEXT_FILE, "r"):
            pass  # If successful, do nothing
    except FileNotFoundError:
        # If the file doesn't exist, create it
        with open(ATOM_EARTHQUAKE_TEXT_FILE, "w") as file:
            file.write("")

def check_last_modified():

    xml_url = "https://www.data.jma.go.jp/developer/xml/feed/eqvol.xml"

    # Fetch JSON data from the URL
    last_modified_response = requests.head(xml_url,timeout=10)

    last_modified = get_last_modified()

    if last_modified != last_modified_response.headers['Last-Modified']:
        logger.info(f"There's been new earthquakes. Previous last modified: {last_modified} New Last Modified: {last_modified_response.headers['Last-Modified']} ")
        record_new_modified(last_modified_response.headers['Last-Modified'])
        return True
    else:
        logger.info(f"No new earthquakes recently last modified response is {last_modified_response.headers['Last-Modified']}")
        return False


def fetch_and_send_new_earthquakes():

    connection = sqlite3.connect(DATABASE, timeout=SQLLITE_TIMEOUT)
    cursor = connection.cursor()
    atom_url = "https://www.data.jma.go.jp/developer/xml/feed/eqvol.xml"

    with open(PREFECTURE_JSON,encoding="utf8") as f:
        PREFECTURE_LIST=json.load(f)

    if LOAD_FILE==1:
        with open("test.json",encoding="utf8") as f:
            quake_list=json.load(f)
    else:
        list_feed = feedparser.parse(atom_url)
        quake_list=list_feed.entries

    last_earthquake_ctt = get_last_seen_earthquake()
    if last_earthquake_ctt == None or last_earthquake_ctt == "":
        last_earthquake_ctt=datetime.now(pytz.timezone('Asia/Tokyo')) - timedelta(days=1)

    last_earthquake_ctt=datetime.fromisoformat(str(last_earthquake_ctt))
    filtered_quakes = [obj for obj in quake_list if datetime.fromisoformat(obj["updated"]) > last_earthquake_ctt and (obj["title"] == "震度速報" or obj["title"] == "震源・震度に関する情報")]

    new_earthquake_count = len(filtered_quakes)
    logger.info(f"New earthquake count {new_earthquake_count}")

    filtered_quakes.reverse()

    quake_list=[]

    if new_earthquake_count > 0:
        for quake in filtered_quakes:
            xml_url = quake["id"]
           # xml_url="https://www.data.jma.go.jp/developer/xml/data/20240109041859_0_VXSE53_010000.xml"
            logger.debug(f"Getting specific file at {xml_url}")

            response=requests.get(xml_url)

            one_quake=xmltodict.parse(response.text, force_list={'Pref'})

            #print(json.dumps(one_quake))

            Proceed = True
            try:
                test1 = one_quake["Report"]["Body"]["Intensity"]["Observation"]["Pref"][0]
            except (TypeError, KeyError):
                 logger.info(f"Skipping this file because it doesnt have correct schema: {xml_url}")
                 Proceed=False

            if (Proceed==True):
                for prefecture_int in one_quake["Report"]["Body"]['Intensity']["Observation"]["Pref"]:
                    new_quake={}
                    new_quake["jma_eid"] = one_quake["Report"]["Head"]["EventID"]
                    new_quake["jma_rdt"] = one_quake["Report"]["Head"]["ReportDateTime"]
                    new_quake["jma_at"] = one_quake["Report"]["Head"]["TargetDateTime"]
                    prefecture_name = [obj for obj in PREFECTURE_LIST if obj["iso_code"] == prefecture_int["Code"]]
                    new_quake["prefecture_name"] = prefecture_name[0]["name"]
                    new_quake["prefecture_maxi"] = int(float(remove_non_numeric(prefecture_int["MaxInt"]))) 
                    new_quake["mqtt_timestamp"] = str(datetime.now(pytz.timezone('Asia/Tokyo')).isoformat())
                    new_quake["mqtt_uuid"] = str(uuid.uuid4())
                    new_quake["source"] = atom_url
                    new_quake["issued_to_mqtt_delay"] = (datetime.now(pytz.timezone('Asia/Tokyo')) - datetime.fromisoformat(new_quake["jma_rdt"])).total_seconds()
                    new_quake["jma_observed_to_issued_delay"] = (datetime.fromisoformat(new_quake["jma_rdt"]) - datetime.fromisoformat(new_quake["jma_at"])).total_seconds()
                    if SEND_MQTT==1:
                        send_to_mqtt(new_quake)
                    cursor.execute('INSERT OR IGNORE INTO earthquakes (eid, arrival_timestamp) VALUES (?, ?)', (new_quake["jma_eid"], new_quake["jma_at"]))
                    cursor.execute(f'UPDATE earthquakes set atom_timestamp= ? where eid = ?', (new_quake["mqtt_timestamp"], new_quake["jma_eid"]) )
                    quake_list.append(new_quake)

                logger.info(f'Updating ctt from {last_earthquake_ctt} to {quake["updated"]}')
                record_new_earthquake(quake["updated"])

        send_any_to_mqtt(quake_list)
    connection.commit()
    connection.close()    

def send_any_to_mqtt(quake_list):
    max_object = max(quake_list, key=lambda x: x["prefecture_maxi"])
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    client.username_pw_set(CONST_MQTT_USERNAME,CONST_MQTT_PASSWORD)
    client.connect( CONST_MQTT_HOST, 1883) 
    logger.info(f"Sending max intensity as Any -> {max_object['prefecture_maxi']}")
    client.publish(f"homeassistant/sensor/japan_earthquake_any/state", payload=max_object["prefecture_maxi"], qos=0, retain=False)
    client.disconnect()   


def send_to_mqtt(quake):
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    client.username_pw_set(CONST_MQTT_USERNAME,CONST_MQTT_PASSWORD)
    client.connect( CONST_MQTT_HOST, 1883)
    payload = json.dumps(quake)
    logger.info(f"New earthquake details -> {payload}")
    client.publish(f"earthquake/{quake['prefecture_name'].lower()}", payload=payload, qos=0, retain=False)
    client.publish(f"homeassistant/sensor/japan_earthquake_{quake['prefecture_name'].lower()}/state", payload=quake["prefecture_maxi"], qos=0, retain=False)
    client.disconnect()   

def reset_all_to_zero():
    with open(PREFECTURE_JSON,encoding="utf8") as f:
        PREFECTURE_LIST=json.load(f)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    client.username_pw_set(CONST_MQTT_USERNAME,CONST_MQTT_PASSWORD)
    client.connect( CONST_MQTT_HOST, 1883) 

    for prefecture in PREFECTURE_LIST:
        client.publish(f"homeassistant/sensor/japan_earthquake_{prefecture['name'].lower()}/state", payload=0, qos=0, retain=False)
    client.disconnect()   


def reset_any_to_zero():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    client.username_pw_set(CONST_MQTT_USERNAME,CONST_MQTT_PASSWORD)
    client.connect( CONST_MQTT_HOST, 1883) 
    logger.info(f"Resetting quake to zero -> Any")
    client.publish(f"homeassistant/sensor/japan_earthquake_any/state", payload=0, qos=0, retain=False)
    client.disconnect()   

if __name__ == "__main__":
    print(f"I am atom client running {VERSION}")
    initialize()
    while True:
        has_been_modified = check_last_modified()
        if (has_been_modified):
            fetch_and_send_new_earthquakes()
        sleep_interval = randrange(0,30)
        logger.info(f"Sleeping for {sleep_interval}")
        time.sleep(sleep_interval)

        reset_all_to_zero()
        reset_any_to_zero()