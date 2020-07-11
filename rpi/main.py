#!/usr/bin/env python
import sys
import os
import json
import kivy
from pint import UnitRegistry
from secrets import MQTT_URL, MQTT_PORT
import paho.mqtt.client as mqtt
from kivy.properties import StringProperty
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.lang import Builder
Builder.load_file("main.kv")
kivy.require("1.11.1")
if os.name == "posix":
    import Adafruit_DHT


class HomeDisplay(BoxLayout):
    outdoorTemperature = StringProperty("Unknown")
    upstairsTemperature = StringProperty("Unknown")
    upstairsHumidity = StringProperty("Unknown")
    downstairsTemperature = StringProperty("Unknown")
    downstairsHumidity = StringProperty("Unknown")


class HomeDisplayApp(App):
    def build(self):
        self.display = HomeDisplay()
        return self.display

    def connected(self, client, userdata, flags, rc):
        if rc == 0:
            client.subscribe("indoor/#")
            client.subscribe("outdoor/#")

    def messaged(self, client, userdata, msg):
        data = json.loads(msg.payload)
        if not data or not "value" in data or not "unit" in data:
            return
        quantity = "{:~P}".format(self.Q_(data["value"], data["unit"]))
        level = msg.topic.split("/")
        if len(level) == 2 and level[0] == "outdoor" and level[1] == "temperature":
            self.display.outdoorTemperature = quantity
        elif len(level) == 3 and level[0] == "indoor":
            if level[1] == "upstairs":
                if level[2] == "temperature":
                    self.display.upstairsTemperature = quantity
                elif level[2] == "humidity":
                    self.display.upstairsHumidity = quantity
            elif level[1] == "downstairs":
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
                    "indoor/downstairs/humidity",
                    json.dumps({"value": round(humidity, 1), "unit": "percent"}))
            if temperature is not None:
                self._client.publish(
                    "indoor/downstairs/temperature",
                    json.dumps(
                        {"value": round(temperature, 1), "unit": "degC"}))

    def on_start(self):
        self._ureg = UnitRegistry()
        self._ureg.define("percent = 1e-2 [] = % = pc")
        self.Q_ = self._ureg.Quantity
        self._client = mqtt.Client(userdata={"self": self})
        self._client.on_connect = self.connected
        self._client.on_message = self.messaged
        self._client.connect(MQTT_URL, MQTT_PORT)
        self._client.loop_start()
        if "Adafruit_DHT" in sys.modules:
            Clock.schedule_interval(self.getOnboardReading, 2)


if __name__ == "__main__":
    HomeDisplayApp().run()
