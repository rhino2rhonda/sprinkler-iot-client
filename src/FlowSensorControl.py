import logging
import requests
import threading
import time

from requests.auth import HTTPBasicAuth

import SprinklerUtils
from GPIOWrapper import pins
from SprinklerConfig import config

logger = logging.getLogger(__name__)


# Sets up and polls the Flow Sensor
# Starts in a separate thread for sending flow data to the server
class FlowSensor(object):
    def __init__(self):
        pins.setup(config['FLOW_SENSOR_PIN'], pins.IN, pull_up_down=pins.PUD_DOWN)
        pins.add_event_detect(config['FLOW_SENSOR_PIN'], pins.RISING, callback=lambda _: self.record_pulse())
        logger.debug("Flow sensor has been configured at pin %d", config['FLOW_SENSOR_PIN'])
        self.lock = threading.RLock()
        self.pulses = 0
        self.last_read_time = time.time()
        self.process_loop = None
        self.active = False

    # Records a pulse from the flow sensor
    def record_pulse(self):
        with self.lock:
            self.pulses += 1
        if self.pulses % 100 == 0:
            logger.debug('Recorded pulse. Curr pulses: %d', self.pulses)

    # Records the flow data and sends it to the server
    def save_flow_process(self):
        logger.debug('Starting save flow process')
        recorded_data = self.read_flow_data()
        thresholds_satisfied = FlowSensor.are_thresholds_satisfied(recorded_data)
        if not thresholds_satisfied:
            logger.debug(
                "Flow volume (%.2f) and duration (%.2f) do not satisfy the thresholds for saving (%.2f, %.2f). " + \
                "Skipping save", recorded_data['volume'], recorded_data['duration'], config['MIN_FLOW_VOLUME_FOR_SAVE'],
                config['MAX_FLOW_DURATION_FOR_SAVE'])
            return False
        send_success = FlowSensor.send_flow_data(recorded_data['volume'], recorded_data['duration'])
        if not send_success:
            logger.error('Save flow process failed as flow data could not be saved at the server')
            return False
        self.reset_flow_data(recorded_data)
        return True

    # Starts the flow data update client
    def start(self):
        def keep_updating():
            logger.debug('Starting process loop for Flow Sensor')
            while self.active:
                success = self.save_flow_process()
                logger.debug('Update loop completed with status %s. Sleeping for %d second(s)', success,
                             config['FLOW_DATA_SAVE_INTERVAL'])
                time.sleep(config['FLOW_DATA_SAVE_INTERVAL'])
            logger.debug('Ending process loop for Flow Sensor')

        logger.info("Starting Flow Sensor")
        self.active = True
        self.process_loop = threading.Thread(target=keep_updating, name='FlowSensorThread')
        self.process_loop.start()
        logger.info("Flow Sensor has been started")

    # Starts the flow data update client
    def stop(self):
        logger.info("Stopping Flow Sensor")
        self.active = False
        self.process_loop.join()
        logger.info("Flow Sensor has been stopped")

    # Checks whether the recorded flow data satisfies the thresholds for being sent to the server
    @staticmethod
    def are_thresholds_satisfied(recorded_data):
        return recorded_data['volume'] >= config['MIN_FLOW_VOLUME_FOR_SAVE'] or \
               recorded_data['duration'] >= config['MAX_FLOW_DURATION_FOR_SAVE']

    # Records the current flow data
    def read_flow_data(self):
        logger.debug('Recording flow data')
        new_time = time.time()
        pulses = self.pulses
        duration = new_time - self.last_read_time
        volume = float(pulses) / config['PULSES_PER_LITRE']
        recorded_data = {
            'new_time': new_time,
            'recorded_pulses': pulses,
            'volume': volume,
            'duration': duration
        }
        logger.debug('Flow data recorded: %s', recorded_data)
        return recorded_data

    # Resets the flow data when it has been successfully recorded by the server
    def reset_flow_data(self, recorded_data):
        logger.debug('Resetting flow data. Before reset pulses:%d, last_read_time:%s', self.pulses, self.last_read_time)
        with self.lock:
            self.pulses -= recorded_data['recorded_pulses']
            self.last_read_time = recorded_data['new_time']
        logger.debug('Flow data has been reset. After reset pulses:%d, last_read_time:%s', self.pulses,
                     self.last_read_time)

    # Sends the recorded flow data to the server
    @staticmethod
    def send_flow_data(volume, duration):
        api = SprinklerUtils.get_server_api_base() + '/flow'
        flow_info = {
            'volume': volume,
            'duration': duration
        }
        logger.debug('Sending flow data to server: %s', flow_info)
        try:
            resp = requests.post(api, json=flow_info, auth=HTTPBasicAuth('API_KEY', config['PRODUCT_KEY']))
        except requests.ConnectionError:
            logger.exception("Error occurred while sending flow data to server")
            return None
        if resp.status_code == 200:
            logger.debug('Sent flow data to server successfully')
            return True
        else:
            logger.error("Request to send flow data failed with status %s", resp.status_code)
            logger.debug("Failed response: Reason: %s, Text: %s", resp.reason, resp.text)
            return False
