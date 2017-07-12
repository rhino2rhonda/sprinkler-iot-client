import RPi.GPIO as pins
import SprinklerGlobals as globals

PINS_MODE = globals.PINS_MODE

class PinsController(object):

    def __init__(self):
        pins.setmode(PINS_MODE)
        assert pins.getmode() == PINS_MODE
        print "Pins have been initialized"

    def clean_up(self):
        pins.cleanup()
        print "Clean up complete"
