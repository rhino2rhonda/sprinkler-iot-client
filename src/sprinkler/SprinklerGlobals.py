import RPi.GPIO as pins

try:
    from PrivateConfig import config
except:
    config = {}

# Pins
PINS_MODES = pins.BOARD
VALVE_PIN = config['VALVE_PIN'] if config.has_key('VALVE_PIN') else 40

# DB
DB_USER = config['DB_USER'] if config.has_key('DB_USER') else ''
DB_PSWD = config['DB_PSWD'] if config.has_key('DB_PSWD') else ''
DB_NAME = config['DB_NAME'] if config.has_key('DB_NAME') else ''

