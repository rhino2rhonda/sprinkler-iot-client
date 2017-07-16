import logging
import SprinklerGlobals as globals

# Globals
LOG_LEVEL = globals.LOG_LEVEL
PRODUCT_ID = globals.PRODUCT_ID

# Fetches a configured logger
def get_logger():
    logging.basicConfig(format='%(levelname)s:%(message)s', level=LOG_LEVEL)
    return logging


# Custom exception
class SprinklerException(Exception):

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


# Deocrator for singleton classes
def singleton(class_):
    instance = class_()
    return instance()
