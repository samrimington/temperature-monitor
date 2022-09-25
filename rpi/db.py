#!/usr/bin/env python
import json
import logging
import math
import os
import sys
import time
from collections.abc import Iterable
from threading import Timer

from labels import DOWNSTAIRS, UPSTAIRS
import orm

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter(
    fmt="%(asctime)s %(name)s.%(levelname)s: %(message)s", datefmt="%Y.%m.%d %H:%M:%S")
handler = logging.StreamHandler(stream=sys.stdout)
handler.setFormatter(formatter)
logger.addHandler(handler)

WRITE_INTERVAL = 300  # seconds


class RollingAverage(float):
    def __new__(cls, value, *_):
        return float.__new__(cls, value)

    def __init__(self, value, total=None, count=1):
        float.__init__(value)
        self._total = value if total is None else total
        self._count = count

    def __repr__(self):
        return f"{self.__class__.__name__}({float(self)})"

    @property
    def count(self):
        return self._count

    def insert(self, value):
        if isinstance(value, Iterable):
            total = self._total + sum(value)
            count = self._count + len(value)
        else:
            total = self._total + value
            count = self._count + 1
        return self.__class__(total / count, total, count)


class Broker:
    def __init__(self):
        self.records = {}

    def writeAll(self):
        counts = ", ".join(f"{k}={v.count}" for k,
                           v in self.records.items())
        logger.info("Ready write counts: %s", counts)
        orm.Environment.insert(**self.records).execute()
        self.records.clear()

    def connected(self, client, userdata, rc):
        if rc == 0:
            logger.debug("Connected")

    def messaged(self, client, userdata, msg):
        logger.debug("Messaged")
        data = json.loads(msg.payload)
        if not data or not "value" in data:
            return
        level = msg.topic.split("/")
        if len(level) != 3 or\
            (level[1] == "humidity" and
             (not (0 < data["value"] < 100) or
                data["unit"] != "percent")) or\
            (level[1] == "temperature" and
             (not (-10 < data["value"] < 40) or
                data["unit"] != "degC")):
            return
        location = {
            DOWNSTAIRS: "downstairs",
            UPSTAIRS: "upstairs"
        }[level[0]]
        field = f"{location}_{level[1]}_{level[2]}"
        if field in self.records:
            self.records[field] = self.records[field].insert(data["value"])
        else:
            self.records[field] = RollingAverage(data["value"])


class RepeatTimer(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)


if __name__ == "__main__":
    orm.db.connect()
    orm.db.create_tables([orm.Environment])

    broker = Broker()

    # Schedule first write to be on the minute
    def writeBegin():
        broker.writeAll()
        # Every 5 minutes
        RepeatTimer(WRITE_INTERVAL, broker.writeAll).start()

    writeBeginEpoch = WRITE_INTERVAL * math.ceil(time.time() / WRITE_INTERVAL)
    Timer(writeBeginEpoch - time.time(), writeBegin).start()
    logger.info(
        "Scheduled writeBegin in %f seconds", writeBeginEpoch - time.time())

    client = mqtt.Client()
    client.on_connect = broker.connected
    client.on_message = broker.messaged
    client.connect(os.environ["MQTT_URL"], int(os.environ["MQTT_PORT"]))
    client.subscribe("esp/#")
    client.subscribe("rpi/#")
    client.loop_forever()
