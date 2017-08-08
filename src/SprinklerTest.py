import logging
import threading
import time
import unittest

from SprinklerConfig import config

# Common config changes
config['FORCE_DUMMY_GPIO'] = True
config['PRODUCT_KEY'] = '$(2#2Da$131s&*f4!x'

from GPIOWrapper import pins
from ValveControl import Valve
from FlowSensorControl import FlowSensor
import SprinklerLogging

SprinklerLogging.configure_logging()
logger = logging.getLogger(__name__)


# Utilities used across the module
class TestUtils(object):
    @staticmethod
    def configure_server_down():
        config['SERVER_DNS'] = None
        config['SERVER_IP'] = 'localhost'
        config['SERVER_PORT'] = 9999

    @staticmethod
    def configure_invalid_product_key():
        invalid_product_key = 'invalid_key'
        config['PRODUCT_KEY'] = invalid_product_key


# Tests config initialization
class ConfigTest(unittest.TestCase):
    def test_1_mandatory_config(self):
        self.assertIsNotNone(config['PRODUCT_KEY'])
        self.assertIsNotNone(config['VALVE_PIN'])
        self.assertTrue(0 <= config['VALVE_PIN'] <= 40)
        self.assertIsNotNone(config['FLOW_SENSOR_PIN'])
        self.assertTrue(0 <= config['FLOW_SENSOR_PIN'] <= 40)

    def test_2_server_config(self):
        if config['SERVER_DNS'] is None:
            self.assertIsNotNone(config['SERVER_PROTOCOL'])
            self.assertIsNotNone(config['SERVER_IP'])


# Tests valve state after initialization
class ValveInitTest(unittest.TestCase):
    def setUp(self):
        self.valve = Valve()

    def test_1_all_attrib(self):
        self.assertEqual(self.valve.state, pins.LOW)
        self.assertIsNone(self.valve.process_loop)
        self.assertFalse(self.valve.active)


# Tests valve state update scenarios
class ValveStateUpdateTest(unittest.TestCase):
    def setUp(self):
        self.valve = Valve()

    def test_1_open_close_scenarios(self):
        self.assertEqual(self.valve.state, pins.LOW)
        ops = [pins.LOW, pins.HIGH, pins.HIGH, pins.LOW]
        for state in ops:
            success = self.valve.update(state)
            self.assertTrue(success)
            self.assertEqual(self.valve.state, state)

    def test_2_update_state_None(self):
        self.assertEqual(self.valve.state, pins.LOW)
        success = self.valve.update(None)
        self.assertFalse(success)
        self.assertEqual(self.valve.state, pins.LOW)

    def test_2_update_state_invalid(self):
        self.assertEqual(self.valve.state, pins.LOW)
        success = self.valve.update(-1)
        self.assertFalse(success)
        self.assertEqual(self.valve.state, pins.LOW)


# Tests valve info fetch scenarios
class ValveStateFetchTest(unittest.TestCase):
    def setUp(self):
        self.valve = Valve()
        self.config_backup = config.copy()

    def tearDown(self):
        config.update(self.config_backup)

    def test_1_valid_request(self):
        valve_info = Valve.get_valve_info()
        self.assertTrue('id' in valve_info)
        self.assertTrue('state' in valve_info)

    def test_2_invalid_request(self):
        TestUtils.configure_invalid_product_key()
        valve_info = Valve.get_valve_info()
        self.assertIsNone(valve_info)

    def test_3_server_down(self):
        TestUtils.configure_server_down()
        valve_info = Valve.get_valve_info()
        self.assertIsNone(valve_info)


# Tests valve update success send scenarios
class ValveSendSuccessTest(unittest.TestCase):
    def setUp(self):
        self.valve = Valve()
        self.config_backup = config.copy()

    def tearDown(self):
        config.update(self.config_backup)

    def test_1_valid_request(self):
        valve_info = {'state': 0}
        success = Valve.send_success(valve_info)
        self.assertTrue(success)

    def test_2_invalid_valve_info(self):
        valve_info = {}
        success = Valve.send_success(valve_info)
        self.assertFalse(success)

    def test_2_invalid_request(self):
        TestUtils.configure_invalid_product_key()
        valve_info = {'state': 0}
        success = Valve.send_success(valve_info)
        self.assertFalse(success)

    def test_3_server_down(self):
        TestUtils.configure_server_down()
        valve_info = {'state': 0}
        success = Valve.send_success(valve_info)
        self.assertFalse(success)


# Tests the entire valve update process
class ValveUpdateProcessTest(unittest.TestCase):
    def setUp(self):
        self.valve = Valve()
        self.config_backup = config.copy()

    def tearDown(self):
        config.update(self.config_backup)

    def test_1_process_success(self):
        success = self.valve.valve_update_process()
        self.assertTrue(success)

    def test_2_process_fail_invalid_key(self):
        TestUtils.configure_invalid_product_key()
        success = self.valve.valve_update_process()
        self.assertFalse(success)
        self.assertEqual(self.valve.state, pins.LOW)

    def test_3_process_fail_server_down(self):
        TestUtils.configure_server_down()
        success = self.valve.valve_update_process()
        self.assertFalse(success)
        self.assertEqual(self.valve.state, pins.LOW)


# Tests flow sensor state after initialization
class FlowSensorInitTest(unittest.TestCase):
    def setUp(self):
        self.flow = FlowSensor()

    def test_1_all_attrib(self):
        self.assertEqual(self.flow.pulses, 0)
        self.assertIsNotNone(self.flow.last_read_time)
        self.assertIsNone(self.flow.process_loop)
        self.assertFalse(self.flow.active)


# Tests the record pulse method that is called by the GPIO module to record pulses
class FlowSensorRecordPulseTest(unittest.TestCase):
    def setUp(self):
        self.flow = FlowSensor()

    def test_1_record_one(self):
        self.assertEqual(self.flow.pulses, 0)
        self.flow.record_pulse()
        self.assertEqual(self.flow.pulses, 1)

    def test_2_record_many_sequential(self):
        self.assertEqual(self.flow.pulses, 0)
        num_records = 100
        for _ in range(num_records):
            self.flow.record_pulse()
        self.assertEqual(self.flow.pulses, num_records)

    def test_2_record_many_parallel(self):
        self.assertEqual(self.flow.pulses, 0)
        num_records = 100
        threads = [threading.Thread(target=self.flow.record_pulse) for _ in range(num_records)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(self.flow.pulses, num_records)


# Tests the reset data method that resets the flow data after successful save
class FlowSensorResetDataTest(unittest.TestCase):
    def setUp(self):
        self.flow = FlowSensor()

    def test_1_reset_pulse_to_zero(self):
        self.flow.pulses = 100
        self.flow.last_read_time = None
        recorded_data = {
            'recorded_pulses': 100,
            'new_time': time.time()
        }
        self.flow.reset_flow_data(recorded_data)
        self.assertEqual(self.flow.pulses, 0)
        self.assertIsNotNone(self.flow.last_read_time)

    def test_2_reset_pulse_to_non_zero(self):
        self.flow.pulses = 200
        self.flow.last_read_time = None
        recorded_data = {
            'recorded_pulses': 100,
            'new_time': time.time()
        }
        self.flow.reset_flow_data(recorded_data)
        self.assertEqual(self.flow.pulses, 100)
        self.assertIsNotNone(self.flow.last_read_time)


# Tests the method that reads current flow data
class FlowSensorReadFlowDataTest(unittest.TestCase):
    def setUp(self):
        self.flow = FlowSensor()

    def test_1_read(self):
        pulses = self.flow.pulses = 100
        recorded_data = self.flow.read_flow_data()
        expected_volume = float(pulses) / config['PULSES_PER_LITRE']
        expected_duration = recorded_data['new_time'] - self.flow.last_read_time
        self.assertEqual(recorded_data, {
            'new_time': recorded_data['new_time'],
            'recorded_pulses': pulses,
            'volume': expected_volume,
            'duration': expected_duration
        })


# Tests the method that checks thresholds for saving recorded flow data
class FlowSensorSaveThresholdsTest(unittest.TestCase):
    def setUp(self):
        self.flow = FlowSensor()

    def test_1_volume_duration_valid(self):
        recorded_data = {
            'volume': config['MIN_FLOW_VOLUME_FOR_SAVE'] + 100,
            'duration': config['MAX_FLOW_DURATION_FOR_SAVE'] + 100
        }
        satisfied = self.flow.are_thresholds_satisfied(recorded_data)
        self.assertTrue(satisfied)

    def test_2_invalid_volume(self):
        recorded_data = {
            'volume': config['MIN_FLOW_VOLUME_FOR_SAVE'] - 100,
            'duration': config['MAX_FLOW_DURATION_FOR_SAVE'] + 100
        }
        satisfied = self.flow.are_thresholds_satisfied(recorded_data)
        self.assertTrue(satisfied)

    def test_3_invalid_duration(self):
        recorded_data = {
            'volume': config['MIN_FLOW_VOLUME_FOR_SAVE'] + 100,
            'duration': config['MAX_FLOW_DURATION_FOR_SAVE'] - 100
        }
        satisfied = self.flow.are_thresholds_satisfied(recorded_data)
        self.assertTrue(satisfied)

    def test_4_volume_duration_invalid(self):
        recorded_data = {
            'volume': config['MIN_FLOW_VOLUME_FOR_SAVE'] - 100,
            'duration': config['MAX_FLOW_DURATION_FOR_SAVE'] - 100
        }
        satisfied = self.flow.are_thresholds_satisfied(recorded_data)
        self.assertFalse(satisfied)


# Tests the save flow data scenarios
class FlowSensorSaveDataTest(unittest.TestCase):
    def setUp(self):
        self.flow = FlowSensor()
        self.config_backup = config.copy()

    def tearDown(self):
        config.update(self.config_backup)

    def test_1_valid_request(self):
        volume = 10
        duration = 20
        success = FlowSensor.send_flow_data(volume, duration)
        self.assertTrue(success)

    def test_2_invalid_flow_info_negative(self):
        volume = -1
        duration = 10
        success = FlowSensor.send_flow_data(volume, duration)
        self.assertFalse(success)

    def test_2_invalid_flow_info_None(self):
        volume = -1
        duration = None
        success = FlowSensor.send_flow_data(volume, duration)
        self.assertFalse(success)

    def test_2_invalid_request(self):
        TestUtils.configure_invalid_product_key()
        volume = 10
        duration = 20
        success = FlowSensor.send_flow_data(volume, duration)
        self.assertFalse(success)

    def test_3_server_down(self):
        TestUtils.configure_server_down()
        volume = 10
        duration = 20
        success = FlowSensor.send_flow_data(volume, duration)
        self.assertFalse(success)


# Tests the entire valve update process
class FlowSensorSaveFlowProcessTest(unittest.TestCase):
    def setUp(self):
        self.flow = FlowSensor()
        self.config_backup = config.copy()

    def tearDown(self):
        config.update(self.config_backup)

    def test_1_process_success(self):
        self.flow.pulses = 10000
        last_read_time = self.flow.last_read_time
        success = self.flow.save_flow_process()
        self.assertTrue(success)
        self.assertEqual(self.flow.pulses, 0)
        self.assertIsNot(self.flow.last_read_time, last_read_time)

    def test_2_process_fail_invalid_key(self):
        TestUtils.configure_invalid_product_key()
        pulses = self.flow.pulses = 10000
        last_read_time = self.flow.last_read_time
        success = self.flow.save_flow_process()
        self.assertFalse(success)
        self.assertEqual(self.flow.pulses, pulses)
        self.assertIs(self.flow.last_read_time, last_read_time)

    def test_3_process_fail_server_down(self):
        TestUtils.configure_server_down()
        pulses = self.flow.pulses = 10000
        last_read_time = self.flow.last_read_time
        success = self.flow.save_flow_process()
        self.assertFalse(success)
        self.assertEqual(self.flow.pulses, pulses)
        self.assertIs(self.flow.last_read_time, last_read_time)

    def test_4_process_fail_threshold_not_satisfied(self):
        last_read_time = self.flow.last_read_time
        success = self.flow.save_flow_process()
        self.assertFalse(success)
        self.assertEqual(self.flow.pulses, 0)
        self.assertIs(self.flow.last_read_time, last_read_time)


if __name__ == "__main__":
    unittest.main()
