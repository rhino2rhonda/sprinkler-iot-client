import logging
from GPIOWrapper import pins

PINS_MODE = pins.BOARD


# Performs GPIO related initializations and cleanup
class PinsController(object):
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        pins.setmode(PINS_MODE)
        assert pins.getmode() == PINS_MODE
        self.logger.info("Pins have been initialized. Mode: %d", PINS_MODE)

    # Resets the GPIO pins
    def clean_up(self):
        pins.cleanup()
        self.logger.info("Clean up complete")
