#include <DHT.h>
#include <DS18B20.h>
#include <ESP8266WiFi.h>
#include <OneWire.h>
#include <PubSubClient.h>
#include "secrets.h"

#define DHT22_PORT 5
#define DS18B20_PORT 4

#define INDOOR_TEMPERATURE_TOPIC "indoor/upstairs/temperature"
#define INDOOR_HUMIDITY_TOPIC "indoor/upstairs/humidity"
#define OUTDOOR_TEMPERATURE_TOPIC "outdoor/temperature"

#define VALUE_UNIT_JSON "{\"value\":%.1f,\"unit\":\"%s\"}"
#define TEMPERATURE_UNIT "degC"
#define HUMIDITY_UNIT "percent"

#define BUF_SIZE 128

DHT indoor(DHT22_PORT, DHT22);
OneWire oneWire(DS18B20_PORT);
DS18B20 outdoor(&oneWire);
WiFiClient client;
PubSubClient mqtt(client);

char buf[BUF_SIZE];

void setup()
{
    Serial.begin(115200);
    indoor.begin();
    outdoor.begin();

    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    Serial.print("Connecting to Wifi");
    while (WiFi.status() != WL_CONNECTED)
    {
        delay(500);
        Serial.print(".");
    }
    Serial.println();
    Serial.print("Connected to Wifi, IP address: ");
    Serial.println(WiFi.localIP());

    mqtt.setServer(MQTT_SERVER, MQTT_PORT);
    mqtt.connect("esp8266");
}

void reconnect()
{
    while (!mqtt.connected())
    {
        Serial.print("Connecting to MQTT broker");
        if (mqtt.connect("esp8266"))
        {
            Serial.println();
            Serial.println("Connected to MQTT broker");
        }
        else
        {
            Serial.println();
            Serial.print("Failed to connect to MQTT broker (rc = ");
            Serial.print(mqtt.state());
            Serial.println(")");
            Serial.println("Trying again in 5 seconds");
            delay(5000);
        }
        }
}

void loop()
{
    if (!client.connected())
        reconnect();
    mqtt.loop();
    delay(2000);
    snprintf(buf, BUF_SIZE, VALUE_UNIT_JSON,
             indoor.readTemperature(), TEMPERATURE_UNIT);
    mqtt.publish(INDOOR_TEMPERATURE_TOPIC, buf, true);
    snprintf(buf, BUF_SIZE, VALUE_UNIT_JSON,
             indoor.readHumidity(), HUMIDITY_UNIT);
    mqtt.publish(INDOOR_HUMIDITY_TOPIC, buf, true);
    if (outdoor.isConversionComplete())
    {
        snprintf(buf, BUF_SIZE, VALUE_UNIT_JSON,
                 outdoor.getTempC(), TEMPERATURE_UNIT);
        mqtt.publish(OUTDOOR_TEMPERATURE_TOPIC, buf, true);
    }
    outdoor.requestTemperatures();
    delay(10000);
}
