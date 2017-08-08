import logging
import signal
import time

import SprinklerLogging
from FlowSensorControl import FlowSensor
from PinsControl import PinsController
from ValveControl import Valve

# App entry point
active = True

# Configure logging
SprinklerLogging.configure_logging()

logger = logging.getLogger(__name__)

# Start components
pins_controller = PinsController()
valve = Valve()
valve.start()
flow_sensor = FlowSensor()
flow_sensor.start()


# Cleanup
def cleanup(sig_num, stack_frame):
    logger.info('Interrupted by sig_num %d. Cleaning up before exit', sig_num)
    valve.stop()
    flow_sensor.stop()
    pins_controller.clean_up()
    global active
    active = False

signals = [signal.SIGINT, signal.SIGTERM]
for s in signals:
    signal.signal(s, cleanup)

logger.debug('Keeping the main thread alive')
while active:
    time.sleep(10)