try:
    from PrivateConfig import config
except:
    config = {}
RPi_MODE = config['RPi_MODE'] if config.has_key('RPi_MODE') else False

if RPi_MODE:
    import RPi.GPIO as pins
else:
    import DummyGPIO as pins

import logging

# Product
PRODUCT_ID = config['PRODUCT_ID'] if config.has_key('PRODUCT_ID') else 1 #TODO: This is obviously temporary
HEART_BEAT_INTERVAL = config['HEART_BEAT_INTERVAL'] if config.has_key('HEART_BEAT_INTERVAL') else 60 # seconds

# Pins
PINS_MODE = pins.BOARD

# Valve
VALVE_PIN = config['VALVE_PIN'] if config.has_key('VALVE_PIN') else 40
VALVE_STATE_UPDATE_INTERVAL = config['VALVE_STATE_UPDATE_INTERVAL'] if config.has_key('VALVE_STATE_UPDATE_INTERVAL') else 10 # secs

# Flow Sensor
FLOW_SENSOR_PIN = config['FLOW_SENSOR_PIN'] if config.has_key('FLOW_SENSOR_PIN') else 38
PULSES_PER_LITRE = config['PULSES_PER_LITRE'] if config.has_key('PULSES_PER_LITRE') else 365
FLOW_POLL_INTERVAL = config['FLOW_POLL_INTERVAL'] if config.has_key('FLOW_POLL_INTERVAL') else 10 # seconds
SAVE_MIN_FLOW_VOLUME = config['SAVE_MIN_FLOW_VOLUME'] if config.has_key('SAVE_MIN_FLOW_VOLUME') else 0.1 # litres
SAVE_MAX_FLOW_DURATION = config['SAVE_MAX_FLOW_DURATION'] if config.has_key('SAVE_MAX_FLOW_DURATION') else 3600 # seconds

# DB
DB_HOST = config['DB_HOST'] if config.has_key('DB_HOST') else ''
DB_PORT = config['DB_PORT'] if config.has_key('DB_PORT') else ''
DB_USER = config['DB_USER'] if config.has_key('DB_USER') else ''
DB_PSWD = config['DB_PSWD'] if config.has_key('DB_PSWD') else ''
DB_NAME = config['DB_NAME'] if config.has_key('DB_NAME') else ''
DB_PING_INTERVAL = config['DB_PING_INTERVAL'] if config.has_key('DB_PING_INTERVAL') else 60*10 # secs

# Logging
LOG_LEVEL = logging.DEBUG
