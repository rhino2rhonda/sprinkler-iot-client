# All
config = {}

# Product
product_config = {
    'PRODUCT_KEY': None
}
config.update(product_config)

# Server
server_config = {
    'SERVER_DNS': None,
    'SERVER_PROTOCOL': 'http://',
    'SERVER_IP': None,
    'SERVER_PORT': None
}
config.update(server_config)

# Pins
gpio_config = {
    'FORCE_DUMMY_GPIO': False
}
config.update(gpio_config)

# Valve
valve_config = {
    'VALVE_PIN': None,  # todo: test init
    'VALVE_STATE_POLL_INTERVAL': 10  # Seconds
}
config.update(valve_config)

# Flow Sensor
flow_config = {
    'FLOW_SENSOR_PIN': None,  # todo: test init
    'PULSES_PER_LITRE': 365,
    'FLOW_DATA_SAVE_INTERVAL': 10,  # Seconds
    'MIN_FLOW_VOLUME_FOR_SAVE': 0.1,  # Litres
    'MAX_FLOW_DURATION_FOR_SAVE': 3600  # Seconds
}
config.update(flow_config)

# Private Overrides
try:
    from PrivateConfig import config as private_config
except ImportError:
    private_config = {}
config.update(private_config)
