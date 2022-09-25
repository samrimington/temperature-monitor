#!/usr/bin/env python
import json
import sqlite3
import time

from labels import DOWNSTAIRS, UPSTAIRS
from secrets import MQTT_URL, MQTT_PORT

import paho.mqtt.client as mqtt

DB_PATH = "/media/usbstick/IoT.db"

def createDbIfNotExists():
    conn = sqlite3.connect(DB_PATH)
    curs = conn.cursor()
    schema = ("""create table if not exists %s (
    timestamp float primary key,
    indoor_downstairs float,
    indoor_upstairs float,
    outdoor float
);
""" * 2) % ("temperature", "humidity")
    sqlite3.complete_statement(schema)
    curs.executescript(schema)
    curs.close()
    conn.close()

def connected(client, userdata, rc):
    if rc == 0:
        print("Connected")

def messaged(client, userdata, msg):
    print("Messaged")
    conn = sqlite3.connect(DB_PATH)
    curs = conn.cursor()
    data = json.loads(msg.payload)
    if not data or not "value" in data:
        return
    level = msg.topic.split("/")
    if len(level) != 3 or \
        level[1] not in ["indoor", "outdoor"] or \
        level[2] not in ["temperature", "humidity"]:
        return
    device = level[0]
    if device == UPSTAIRS:
        loc = "upstairs"
    elif device == DOWNSTAIRS:
        loc = "downstairs"
    else:
        return
    if level[1] == "indoor":
        prop = "%s_%s" % (level[1], loc)
    else:
        prop = level[1]
    query = "insert into %s (timestamp, %s) values (?, ?)" % (level[2], prop)
    print("Writing")
    curs.execute(query, (time.time(), data["value"]))
    conn.commit()
    curs.close()
    conn.close()

if __name__ == "__main__":
    createDbIfNotExists()
    client = mqtt.Client()
    client.on_connect = connected
    client.on_message = messaged
    client.connect(MQTT_URL, MQTT_PORT)
    client.subscribe("esp/#")
    client.subscribe("rpi/#")
    print("Hello")
    client.loop_forever()
