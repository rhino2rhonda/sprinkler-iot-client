import SprinklerGlobals as globals

if globals.RPi_MODE:
    import RPi.GPIO as pins
else:
    import DummyGPIO as pins

import SprinklerUtils as utils
import SprinklerDB as DB
import time
import threading


# Globals
FLOW_SENSOR_PIN = globals.FLOW_SENSOR_PIN
PULSES_PER_LITRE = globals.PULSES_PER_LITRE
FLOW_POLL_INTERVAL = globals.FLOW_POLL_INTERVAL
SAVE_MIN_FLOW_VOLUME = globals.SAVE_MIN_FLOW_VOLUME
SAVE_MAX_FLOW_DURATION = globals.SAVE_MAX_FLOW_DURATION


# Constants
FLOW_SENSOR_COMPONENT_NAME = 'flow-sensor'


# Sets up and polls the Flow Sensor
class FlowSensor(object):

    def __init__(self):
        
        self.logger = utils.get_logger()
        self.lock = threading.RLock()

        # Unique component ID
        self.component_id = DB.get_component_id(FLOW_SENSOR_COMPONENT_NAME)
        if self.component_id is None:
            self.logger.error("Component ID not found in DB")
            raise Exception("Component ID not found in DB")

        self.pulses = 0
        self.last_read_time = time.time()
        pins.setup(FLOW_SENSOR_PIN, pins.IN, pull_up_down=pins.PUD_DOWN)
        pins.add_event_detect(FLOW_SENSOR_PIN, pins.RISING, callback=lambda _: self.record_pulse())
        self.logger.debug("Flow Sensor is up and running")

        # Start a daemon thread for tracking water flow
        self.active = True
        self.save_thread = threading.Thread(target=self.keep_saving_flow)
        self.save_thread.setDaemon(True)
        self.save_thread.start()

    
    # Records a pulse from the flow sensor
    def record_pulse(self):
        with self.lock: # Should I/O thread be blocked? Buffer?
            self.pulses += 1


    # Saves the recorded pulses to the DB
    def save_flow(self):
        with self.lock:
            
            # Compute flow
            new_time = time.time()
            flow_duration = new_time - self.last_read_time
            flow_volume = float(self.pulses) / PULSES_PER_LITRE

            # Check time and volume thresholds
            if flow_duration < SAVE_MAX_FLOW_DURATION and flow_volume < SAVE_MIN_FLOW_VOLUME:
                self.logger.warning("Flow volume (%.2f) and duration (%.2f) do not satisfy the thresholds for saving (%.2f, %.2f). " +\
                        "Skipping save", flow_volume, flow_duration, SAVE_MIN_FLOW_VOLUME, SAVE_MAX_FLOW_DURATION)
                return False

            # Save to DB
            self.logger.debug("Saving flow data to DB (Volume : %.2f litre(s) and Duration : %.2f seconds)", flow_volume, flow_duration)
            with DB.Connection() as cursor:
                sql = "insert into flow_rate (component_id, flow_volume, flow_duration) values (%s, %s, %s)"
                try:
                    inserted = cursor.execute(sql, (self.component_id, flow_volume, flow_duration))
                    self.logger.debug("Rows inserted: %d", inserted)
                except Exception as ex:
                    self.logger.error("Failed to save flow data to DB:%s", str(ex))
                    return False

            # Reset the state
            self.pulses = 0
            self.last_read_time = new_time
            return True


    # To be executed as a thread to ensure that flow data is periodically saved in the DB
    def keep_saving_flow(self):
        self.logger.debug("Save flow thread is up and running")
        while self.active:
            time.sleep(FLOW_POLL_INTERVAL)
            success = self.save_flow()
            self.logger.debug("Save flow process completed with status %s. Next save in %d seconds" % (success, FLOW_POLL_INTERVAL))
        self.logger.debug("Save flow thread will now terminate")
