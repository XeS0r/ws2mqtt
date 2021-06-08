#!/bin/python3

from http import server
import logging
from urllib import parse
from http.server import HTTPServer
from http.server import BaseHTTPRequestHandler
from decimal import Decimal
import paho.mqtt.client as mqtt
import datetime as dt
import pytz

serverAddress = ''
serverPort = 8081

ows_topic = "outdoor/weatherstation"

# Fahrenheit to °Celcius
f2c = { "indoortempf":"indoortemp", "tempf":"temp", "dewptf":"dewpt", "windchillf":"windchill" }
# Miles per hour to kilometers per hour
m2k = { "windspeedmph":"windspeedkmh", "windgustmph":"windgustkmh" }
# inHG to hPA
i2h = { "absbaromin":"absbaromhpa", "baromin":"barohpa" }
# inch to mm
i2mm = { "rainin":"rainmm", "dailyrainin":"dailyrainmm", "weeklyrainin":"weeklyrainmm", "monthlyrainin":"monthlyrainmm", "yearlyrainin":"yearlyrainmm" }
# utc to local timezone
u2tz = { "dateutc":"Europe/Berlin" }

class WeatherStationServer(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def publish_mqtt(self, kv):
        for key in kv.keys():
            value = kv.get(key)[0]

            if key in f2c.keys():
                key = f2c.get(key)
                value = str(round((Decimal(value) - Decimal("32.0")) / Decimal("9.0") * Decimal("5.0"), 2))
            elif key in m2k.keys():
                key = m2k.get(key)
                value = str(round(Decimal(value) * Decimal("1.60934"), 2))
            elif key in i2h.keys():
                key = i2h.get(key)
                value = str(round(Decimal(value) * Decimal("33.8638815789"), 2))
            elif key in i2mm.keys():
                key = i2mm.get(key)
                value = str(round(Decimal(value) * Decimal("25.4"), 2))
            elif key in u2tz.keys():
                value = dt.datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
                value = pytz.timezone(u2tz.get(key)).localize(value).isoformat()

            topic = "{}/{}".format(ows_topic, key)
            logging.debug("Publish: {} {}".format(topic, value))
            mqttClient.publish(topic, value)

    def _set_response(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(bytes("Server is running", "UTF-8"))
        parms = parse.parse_qs(parse.urlparse(self.path).query)
        if parms:
            self.publish_mqtt(parms)
            logging.debug("Published values")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logging.info("Connect MQTT client")

    mqttClient = mqtt.Client()
    mqttClient.username_pw_set("mqtt-user", "password")
    lwtopic = "{}/LWT".format(ows_topic)
    mqttClient.will_set(lwtopic, "Offline", qos=1, retain=True)
    mqttClient.connect("wendy", 1883, 60)
    mqttClient.loop_start()
    mqttClient.publish(lwtopic, "Online", retain=True)

    webserver = HTTPServer((serverAddress, serverPort), WeatherStationServer)
    logging.info("Start webserver on Port {}".format(serverPort))
    try:
        webserver.serve_forever()
    except KeyboardInterrupt:
        pass
    logging.info("Stop webserver")
    webserver.server_close()
    logging.info("Disconnect MQTT client")
    mqttClient.loop_stop()
