import RPi.GPIO as pins
import logging

try:
    from PrivateConfig import config
except:
    config = {}

# Product
PRODUCT_ID = config['PRODUCT_ID'] if config.has_key('PRODUCT_ID') else 1 #TODO: This is obviously temporary

# Pins
PINS_MODE = pins.BOARD
VALVE_PIN = config['VALVE_PIN'] if config.has_key('VALVE_PIN') else 40
VALVE_STATE_UPDATE_INTERVAL = config['VALVE_STATE_UPDATE_INTERVAL'] if config.has_key('VALVE_STATE_UPDATE_INTERVAL') else 5 # secs
VALVE_PIN = config['VALVE_PIN'] if config.has_key('VALVE_PIN') else 40

# DB
DB_HOST = config['DB_HOST'] if config.has_key('DB_HOST') else ''
DB_PORT = config['DB_PORT'] if config.has_key('DB_PORT') else ''
DB_USER = config['DB_USER'] if config.has_key('DB_USER') else ''
DB_PSWD = config['DB_PSWD'] if config.has_key('DB_PSWD') else ''
DB_NAME = config['DB_NAME'] if config.has_key('DB_NAME') else ''
DB_PING_INTERVAL = config['DB_PING_INTERVAL'] if config.has_key('DB_PING_INTERVAL') else 10 # secs

# Logging
LOG_LEVEL = logging.DEBUG
