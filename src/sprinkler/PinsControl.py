import SprinklerGlobals as globals

if globals.RPi_MODE: 
    import RPi.GPIO as pins
else:
    import DummyGPIO as pins

import SprinklerUtils as utils
import logging


# Globals
PINS_MODE = globals.PINS_MODE


class PinsController(object):

    def __init__(self):
        self.logger = logging.getLogger()
        pins.setmode(PINS_MODE)
        assert pins.getmode() == PINS_MODE
        self.logger.debug("Pins have been initialized")

    def clean_up(self):
        pins.cleanup()
        self.logger.debug("Clean up complete")
