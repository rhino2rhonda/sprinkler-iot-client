import logging
import requests
import threading
import time

from requests.auth import HTTPBasicAuth

import SprinklerUtils
from GPIOWrapper import pins
from SprinklerConfig import config

logger = logging.getLogger(__name__)


# Operates the valve directly by changing the state of the GPIO pin
# Starts in a separate thread for valve updates
class Valve(object):
    def __init__(self):
        pins.setup(config['VALVE_PIN'], pins.OUT)
        self.state = pins.LOW
        pins.output(config['VALVE_PIN'], pins.LOW)
        logger.debug("Valve has been configured at pin %d and state %d", config['VALVE_PIN'], self.state)
        self.process_loop = None
        self.active = False

    # Updates the state of the valve
    def update(self, state):
        logger.debug('Attempting to update valve state to %s', state)
        if state not in [pins.LOW, pins.HIGH]:
            logger.error('Failed to update valve state: Invalid state: %s', state)
            return False
        elif self.state == state:
            logger.debug('Valve state is already %s', state)
            return True
        else:
            logger.debug("Valve state needs to be updated")
            try:
                pins.output(config['VALVE_PIN'], state)
                self.state = state
                logger.info("Valve state updated successfully")
            except Exception:
                logger.exception('Failed to update valve state: Error occurred while updating')
                return False
        logger.debug('Valve state updated successfully')
        return True

    # Updates the state of the valve by communicating with the server
    def valve_update_process(self):
        orig_state = self.state
        logger.debug('Starting valve update process. Orig state: %d', orig_state)

        valve_info = Valve.get_valve_info()
        if valve_info is None:
            logger.error('Update loop failed as valve info was not fetched')
            return False

        try:
            next_state = valve_info['state']
        except KeyError:
            logger.exception('Update loop failed as valve info received is invalid')
            return False

        update_success = self.update(next_state)
        if not update_success:
            logger.error('Update loop failed as valve could not be updated')
            return False

        send_success = Valve.send_success(valve_info)
        if not send_success:
            logger.error(
                'Valve has been updated but server could not be communicated. Hence reverting to original state %d',
                orig_state)
            revert_success = self.update(orig_state)
            if not revert_success:
                logger.critical('Failed to revert valve state. Server and Client might be in inconsistent states')
                return False
            logger.info('Reverted valve state to original state %d', orig_state)
            return False

        logger.debug('Valve update process was successful')
        return True

    # Starts the valve state update client
    def start(self):
        def keep_updating():
            logger.debug('Starting process loop for Valve')
            while self.active:
                success = self.valve_update_process()
                logger.debug('Update loop completed with status %s. Sleeping for %d second(s)', success,
                             config['VALVE_STATE_POLL_INTERVAL'])
                time.sleep(config['VALVE_STATE_POLL_INTERVAL'])
            logger.debug('Ending process loop for Valve')

        logger.info("Starting Valve")
        self.active = True
        self.process_loop = threading.Thread(target=keep_updating, name='ValveThread')
        self.process_loop.start()
        logger.info("Valve has been started")

    # Stops the valve state update client
    def stop(self):
        logger.info("Stopping Valve")
        self.active = False
        self.process_loop.join()
        self.state = pins.LOW
        pins.output(config['VALVE_PIN'], pins.LOW)
        logger.info("Valve has been stopped")

    # Fetches the latest valve info from the server
    @staticmethod
    def get_valve_info():
        logger.debug('Fetching valve state from serve')
        api = SprinklerUtils.get_server_api_base() + '/valve'
        try:
            resp = requests.get(api, auth=HTTPBasicAuth('API_KEY', config['PRODUCT_KEY']))
        except requests.ConnectionError:
            logger.exception("Error occurred while fetching valve state from server")
            return None
        if resp.status_code == 200:
            valve_info = resp.json()
            logger.debug('Fetched valve info from server: %s', valve_info)
            return valve_info
        else:
            logger.error("Request to obtain valve state failed with status %s", resp.status_code)
            logger.debug("Failed response: Reason: %s, Text: %s", resp.reason, resp.text)
            return None

    # Notifies the server regarding the latest valve update
    @staticmethod
    def send_success(valve_info):
        api = SprinklerUtils.get_server_api_base() + '/valve'
        logger.debug('Sending valve state update success to server: %s', valve_info)
        try:
            resp = requests.post(api, json=valve_info, auth=HTTPBasicAuth('API_KEY', config['PRODUCT_KEY']))
        except requests.ConnectionError:
            logger.exception("Error occurred while sending valve state update success to server")
            return None
        if resp.status_code == 200:
            logger.debug('Sent valve state update success to server successfully')
            return True
        else:
            logger.error("Request to send valve state update success failed with status %s", resp.status_code)
            logger.debug("Failed response: Reason: %s, Text: %s", resp.reason, resp.text)
            return False
