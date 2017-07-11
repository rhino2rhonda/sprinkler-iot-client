import RPi.GPIO as pins

PINS_MODE = pins.BOARD

class PinsController(object):

    def __init__(self):
        pins.setmode(PINS_MODE)
        assert pins.getmode() == PINS_MODE
        print "Pins have been initialized"

    def clean_up(self):
        pins.cleanup()
        print "Clean up complete"
