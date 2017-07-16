import SprinklerGlobals as globals

if globals.RPi_MODE: 
    import RPi.GPIO as pins
else:
    import DummyGPIO as pins
import SprinklerUtils as utils

PINS_MODE = globals.PINS_MODE
logger = utils.get_logger()

class PinsController(object):

    def __init__(self):
        pins.setmode(PINS_MODE)
        assert pins.getmode() == PINS_MODE
        logger.debug("Pins have been initialized")

    def clean_up(self):
        pins.cleanup()
        logger.debug("Clean up complete")
