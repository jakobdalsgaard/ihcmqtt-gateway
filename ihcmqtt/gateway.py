import os
import getopt
import sys
import signal

import logging
import paho.mqtt.client as mqtt
import string

from ihcsdk.ihccontroller import IHCController
from xml.etree import ElementTree as ET

WHITELIST_CHARS = set(string.ascii_lowercase + string.ascii_uppercase + string.digits + "-_")


#
# Make sure a name that is to be part of an MQTT topic
# hiearchy only contains characters valid for such.
# 
def whitelist_name(name):
    return ''.join(c for c in name if c in WHITELIST_CHARS)

#
# Main gateway class
#
# All configuration is pulled from the IHC controller, and all state is stored in the 
# callback handlers. For this to work, the MQTT controller must be connected first, then
# the IHC controller, thus proper execution is like this:
#
#    import ihcmqtt
#    gw = ihcmqtt.IhcMqttGateway()
#    gw.connect_broker("localhost")
#    gw.connect_controler("192.168.1.100", "username", "password")
#
# This will map all dataline_input to MQTT topics where input state changes are published,
# and all dataline_output to MQTT topics where state changes are published - and also map
# command MQTT topics to state changes in the controller.
class IhcMqttGateway:

    def __init__(self):
        self.controller = None
        self.broker = None
        self.logger = logging.getLogger("ihcmqtt.gateway")
        self.mapfile = None
        self.topic_prefix = "house"

    def connect_controller(self, url, username, password):
        self.logger.info("Connecting to IHC system at {} with user {}".format(url, username))
        ctl = IHCController(url, username, password)
        if not ctl.authenticate():
            self.logger.error("Cannot authenticate to IHC system at {} with user {}".format(url, username))
            sys.exit(4)
        self.set_controller(ctl)

    def set_controller(self, ctl):
        self.controller = ctl
        mapfile = None
        if self.mapfile:
            mapfile = open(self.mapfile, "w")

        # parse project file from controller
        # to get all dataline_input and dataline_output
        project = ctl.get_project()
        doc = ET.fromstring(project)
        for group in doc.findall(".//group"):
            pparent_name = whitelist_name(group.attrib["name"])
            for product in group.findall(".//product_dataline"):
                parent_name = whitelist_name("{}-{}".format(product.attrib["name"], product.attrib["position"]))
                for dout in product.findall(".//dataline_output"):
                    name = whitelist_name(dout.attrib["name"])
                    # set up IHC->MQTT
                    base_topic_name = "{}/{}/{}/{}/state".format(self.topic_prefix, pparent_name, parent_name, name)
                    resid = dout.attrib["id"]
                    intid = int(resid[1:], base=16)
                    self.logger.debug("dataline output resource id {} ({}) publishes to {}".format(resid, intid, base_topic_name))
                    if mapfile:
                        mapfile.write("{}, {}, {}\n".format(resid, intid, base_topic_name))
                    self.controller.add_notify_event(intid, self.on_ihc_change_handler(base_topic_name), True)
                    # set up MQTT->IHC
                    if self.broker:
                        base_topic_name = "{}/{}/{}/{}/command".format(self.topic_prefix, pparent_name, parent_name, name)
                        self.broker.subscribe(base_topic_name)
                        self.logger.debug("dataline output resource id {} ({}) subscribes to {}".format(resid, intid, base_topic_name))
                        if mapfile:
                            mapfile.write("{}, {}, {}\n".format(resid, intid, base_topic_name))
                        self.broker.message_callback_add(base_topic_name, self.on_topic_message_handler(intid))
                for din in product.findall(".//dataline_input"):
                    name = whitelist_name(din.attrib["name"])
                    # set up IHC->MQTT
                    base_topic_name = "{}/{}/{}/{}/state".format(self.topic_prefix, pparent_name, parent_name, name)
                    resid = din.attrib["id"]
                    intid = int(resid[1:], base=16)
                    self.logger.debug("dataline input resource id {} ({}) publishes to {}".format(resid, intid, base_topic_name))
                    if mapfile:
                        mapfile.write("{}, {}, {}\n".format(resid, intid, base_topic_name))
                    self.controller.add_notify_event(intid, self.on_ihc_change_handler(base_topic_name), True)
        if mapfile:
            mapfile.close()

    def on_topic_message_handler(self, resid):
        def inner(client, userdata, message):
            print("message: {} for {}".format(message.payload, resid))
            if message.payload.decode() == "ON":
                state = True
            else:
                state = False
            self.controller.set_runtime_value_bool(resid, state)
        return inner

    def on_ihc_change_handler(self, topic):
        def inner(resid, value):
            if value:
                payload = "ON"
            else:
                payload = "OFF"
            if self.broker:
                self.broker.publish(topic, payload=payload)
        return inner

    def set_broker(self, brk):
        self.broker = brk

    def connect_broker(self, host, port=1883):
        client_id = "ihcmqtt-gateway-{}".format(os.getpid())
        self.logger.info("Connecting to mqtt broker {}:{} with client-id {}".format(host, port, client_id))
        broker = mqtt.Client(client_id=client_id)
        broker.connect(host, port)
        broker.loop_start()
        self.set_broker(broker)

    def close(self):
        self.controller.disconnect()
        self.controller.client.connection.session.close()
        self.broker.loop_stop()


#
# Read a 'properties' style config file.
def read_config(filename, config):
    def parse_line(line):
        eq = line.find("=")
        if eq > 1:
            (key, val) = (line[0:eq], line[eq+1:])
            config[key] = val
    with open(filename) as file:
        for line in file:
            if not line.startswith("#"):
                parse_line(line.rstrip())

#
# Check if supplied dict contains the mandatory configuration items.
def valid_config(config):
    keys = ["broker_host", "broker_port", "controller_url", "controller_username", "controller_password" ]
    for key in keys:
        if not key in config:
            return False
    return True

USAGE = """\
python3 -m ihcmqtt.gateway [-h] [-v #] [-c file]

  -h displays this message
  -v increases verbosity (on stdout), value 1..3
  -c specifies a config file to read
"""

def main(argv):
    config = dict()
    log_level = logging.ERROR

    try:
        opts, args = getopt.getopt(argv, "hv:c:",[])
    except:
        print("Error parsing command line arguments: {}".format(' '.join(argv)))
        sys.exit(2)
    for opt, arg  in opts:
        if opt in ["-h"]:
            print(USAGE)
            sys.exit(0)
        elif opt in ["-c"]:
            read_config(arg, config)
        elif opt in ["-v"]:
            if arg == "1":
                log_level = logging.WARN
            elif arg == "2":
                log_level = logging.INFO
            elif arg == "3":
                log_level = logging.DEBUG

    logging.basicConfig(level=log_level)

    if not valid_config(config):
        print("Insufficient configuration given, exit")
        sys.exit(3)

    gw = IhcMqttGateway()
    if "mapfile" in config:
        gw.mapfile = config["mapfile"]
    if "topic_prefix" in config:
        gw.topic_prefix = config["topic_prefix"]
    gw.connect_broker(config["broker_host"], int(config["broker_port"]))
    gw.connect_controller(config["controller_url"], config["controller_username"], config["controller_password"])
    signal.signal(signal.SIGINT, lambda sig, frame: gw.close())

if __name__ == "__main__":
    main(sys.argv[1:])
