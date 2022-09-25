#!/usr/bin/env python
from datetime import datetime
import json
import os
import sys

from labels import DOWNSTAIRS, UPSTAIRS

from kivy.properties import StringProperty
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.lang import Builder
from pint import UnitRegistry
import kivy
import paho.mqtt.client as mqtt

Builder.load_file("main.kv")
kivy.require("1.11.1")
# TODO: Detect Rpi
if os.name == "posix":
    import Adafruit_DHT


class HomeDisplay(BoxLayout):
    outdoorTemperature = StringProperty("Unknown")
    upstairsTemperature = StringProperty("Unknown")
    upstairsHumidity = StringProperty("Unknown")
    downstairsTemperature = StringProperty("Unknown")
    downstairsHumidity = StringProperty("Unknown")
    lastRecv = StringProperty("Never")


class HomeDisplayApp(App):
    def build(self):
        self.display = HomeDisplay()
        return self.display

    def connected(self, client, userdata, flags, rc):
        if rc == 0:
            print("Connected")
            client.subscribe("esp/#")
            client.subscribe("rpi/#")

    def messaged(self, client, userdata, msg):
        print("Messaged")
        self.display.lastRecv = datetime.now().isoformat()
        data = json.loads(msg.payload)
        if not data or not "value" in data or not "unit" in data:
            return
        quantity = "{:~P}".format(self.Q_(data["value"], data["unit"]))
        level = msg.topic.split("/")
        if len(level) != 3:
            return
        if level[1] == "outdoor" and level[2] == "temperature":
            self.display.outdoorTemperature = quantity
        elif level[1] == "indoor":
            if level[0] == UPSTAIRS:
                if level[2] == "temperature":
                    self.display.upstairsTemperature = quantity
                elif level[2] == "humidity":
                    self.display.upstairsHumidity = quantity
            elif level[0] == DOWNSTAIRS:
                if level[2] == "temperature":
                    self.display.downstairsTemperature = quantity
                elif level[2] == "humidity":
                    self.display.downstairsHumidity = quantity

    def getOnboardReading(self, key, *largs):
        if self._client.is_connected:
            humidity, temperature = Adafruit_DHT.read_retry(
                Adafruit_DHT.DHT22, 2)
            if humidity is not None:
                self._client.publish(
                    "rpi/indoor/humidity",
                    json.dumps({"value": round(humidity, 1), "unit": "percent"}))
            if temperature is not None:
                self._client.publish(
                    "rpi/indoor/temperature",
                    json.dumps(
                        {"value": round(temperature, 1), "unit": "degC"}))

    def on_start(self):
        self._ureg = UnitRegistry()
        self._ureg.define("percent = 1e-2 [] = % = pc")
        self.Q_ = self._ureg.Quantity

        self._client = mqtt.Client(userdata={"self": self})
        self._client.on_connect = self.connected
        self._client.on_message = self.messaged
        self._client.connect(
            os.environ["MQTT_URL"], int(os.environ["MQTT_PORT"]))
        self._client.loop_start()
        if "Adafruit_DHT" in sys.modules:
            Clock.schedule_interval(self.getOnboardReading, 2)

        print("Ready")


if __name__ == "__main__":
    HomeDisplayApp().run()
