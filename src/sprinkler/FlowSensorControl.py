import SprinklerGlobals as globals

if globals.RPi_MODE:
    import RPi.GPIO as pins
else:
    import DummyGPIO as pins

import time

# Constants
INPUT_PIN = 40
PULSE_FACTOR = 227 # Pulses per Litre
POLL_FREQ = 10 # Seconds


# Sets up and polls the Flow Sensor
class FlowSensor(object):

    def __init__(self):
        self.pulses = 0
        self.last_read_time = time.time()
        pins.setup(INPUT_PIN, pins.IN, pull_up_down=pins.PUD_DOWN)
        pins.add_event_detect(INPUT_PIN, pins.RISING, callback=lambda: self.record_pulse)
        print "Flow Sensor is up and running"

    def record_pulse(self):
        self.pulses += 1

    def rest_pulses(self):
        self.pulses = 0

    def read_value(self):
        new_time = time.time()
        time_hours = float(new_time - curr_time) / 3600
        flow_litres = float(self.pulses) / PULSE_FACTOR
        self.rest_pulses()
        self.last_read_time = new_time
        return flow_litres / time_hours
