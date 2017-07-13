import logging
import SprinklerGlobals as globals

# Globals
LOG_LEVEL = globals.LOG_LEVEL

# Fetches a configured logger
def get_logger():
    logging.basicConfig(format='%(levelname)s:%(message)s', level=LOG_LEVEL)
    return logging
