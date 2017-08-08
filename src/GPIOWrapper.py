# This wrapper is is used so that client can run on any machine
# If the device is not a raspberry pi, a dummy GPIO module is used that does nothing
from SprinklerConfig import config

if config['FORCE_DUMMY_GPIO']:
    import DummyGPIO as pins
else:
    try:
        import RPi.GPIO as pins
    except RuntimeError:
        import DummyGPIO as pins
