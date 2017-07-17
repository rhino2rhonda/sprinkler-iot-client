import SprinklerGlobals as globals

if globals.RPi_MODE:
    import RPi.GPIO as pins
else:
    import DummyGPIO as pins

import SprinklerDB as DB
import SprinklerUtils as utils
import ValveControl as VC
import FlowSensorControl as FC
import PinsControl as PC

import logging.config
import threading
import json
import time


# Globals
HEART_BEAT_INTERVAL = globals.HEART_BEAT_INTERVAL
PRODUCT_ID = globals.PRODUCT_ID


# Configures application wide logging from JSON file
def configure_logging():
    with open('logging.json', 'r') as log_file:
        log_dict = json.load(log_file)
        logging.config.dictConfig(log_dict)
        logger = logging.getLogger()
        logger.debug("Logging has been configured")


# Initializes all the components
# TODO: Cleanup code, name threads and add to
class Sprinkler(object):

    def __init__(self):

        # Configure logging
        configure_logging()
        self.logger = logging.getLogger(__name__)

        # Initialize components
        self.pins_controller = PC.PinsController()
        self.switch = VC.ValveSwitch()
        self.remote_vc = VC.RemoteValveController()
        self.timer_vc = VC.ValveTimerController()
        self.controllers = [self.remote_vc, self.timer_vc]
        self.manager = VC.ValveManager(self.switch, self.controllers)
        self.flow_sensor = FC.FlowSensor()

        self.logger.info("Application is up and running")

        # Initialize heart beat daemon thread
        self.active = True
        self.heart_beat_thread = threading.Thread(target=self.heart_beat, name="heart_beat_thread")
        self.heart_beat_thread.setDaemon(True)
        self.heart_beat_thread.start()
        self.heart_beat_thread.join()


    # To be executed as a thread for saving the product's heart beat periodically
    def heart_beat(self):
        
        self.logger.info("Heart beat thread is up and running")
        while self.active:
            with DB.Connection() as cursor:
                sql = "insert into product_heart_beat (product_id) values(%s)"
                try:
                    inserted = cursor.execute(sql, (PRODUCT_ID,))
                    self.logger.debug("Rows inserted: %s", inserted)
                    self.logger.info("Heart beat sent successfully")
                except Exception as ex:
                    self.logger.exception("Failed to send heart beat")
            self.logger.debug("Next heart beat in %s seconds", HEART_BEAT_INTERVAL)
            time.sleep(HEART_BEAT_INTERVAL)
        self.logger.info("Heart beat thread will now terminate")


if __name__ == '__main__':
    sprinkler = Sprinkler()
