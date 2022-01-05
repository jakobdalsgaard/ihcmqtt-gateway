Ihc Mqtt Gateway
================

A simple IHC-MQTT Gateway; given connection details to an IHC Controller it downloads the project
file and subscribes on events from dataline inputs and outputs. Furthermore it subscribes to topics
in MQTT corresponding to each dataline output in the IHC project file.

The gateway can easily be run as a Python module:

```
python3 -m ihcmqtt.gateway
```

It accepts the command line parameters:

`-h`
: a short help message

`-v`
: increase verbosity, possible levels are: 1, 2 and 3

`-c`
: specify a configuration file to use

The configuration file may look like this:

```
controller_url=http://192.168.178.1.10
controller_username=ihcuser
controller_password=ihcpassword
broker_host=localhost
broker_port=1883
```

These are the required settings. Specifying a `mapfile` configuration item will make the gateway print out
IHC resource identifiers and corresponding MQTT topic names to said file.

By default topic names are derived from name and position tags in the IHC project file and prefixed with "house".
The prefix can be changed by specifying `topic_prefix` in the configuration file.

An example of those extra, non-mandatory, configuration items could be:

```
mapfile=/var/ihcmqtt/ihcmqtt.map
topic_prefix=cottage
```

The gateway connects to the MQTT broker with a client name of "ihcmqtt-gateway-PID" - with PID being the
process id of the gateway.

When run as a Python module, the gateway will exit cleanly on SIGINT.
