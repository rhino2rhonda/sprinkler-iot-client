import RPi.GPIO as pins

# INPIN=38
# OUTPIN=40

pins.setmode(pins.BOARD)
pins.setup(40, pins.OUT)
pins.output(40, pins.HIGH)

raw_input("Press ENTER to exit")
pins.cleanup()
