import unittest
from PinsControl import PinsController as PC
from ValveControl import ValveSwitch as VS
from SprinklerDB import *
from ValveControl import ValveMultiSwitch as VMS
from ValveControl import ValveController as VC
from SprinklerAPI import CommonSprinklerAPI as API
import SprinklerCLI
from SprinklerCLI import CommandLineController as CLI
import SprinklerGlobals
import RPi.GPIO as pins
import zmq
import pickle
import random

class TestValveSwitch(unittest.TestCase):

    def setUp(self):
        self.pc = PC()
        self.switch = VS()
        
    def tearDown(self):
        self.pc.clean_up()

    def get_db_state(self):
        state = None
        con = get_connection()
        cursor = con.cursor()
        sql = "select state from Valve where id = (select max(id) from Valve);"
        cursor.execute(sql)
        data = cursor.fetchone()
        state = data['state']
        close_connection(con)
        return state
    
    def test_switch_state_initial(self):
        db_state = self.get_db_state()
        if db_state is None:
            self.assertEqual(self.switch.state, pins.LOW)
        else:
            self.assertEqual(self.switch.state, db_state)

    def test_switch_open(self):
        self.switch.open()
        db_state = self.get_db_state()
        self.assertEqual(self.switch.state, pins.HIGH)
        self.assertEqual(db_state, pins.HIGH)

    def test_switch_close(self):
        self.switch.close()
        db_state = self.get_db_state()
        self.assertEqual(self.switch.state, pins.LOW)
        self.assertEqual(db_state, pins.LOW)

    def test_many_switch_toggles(self):
        for _ in range(10):
            self.test_switch_open() if random.randint(0,1) else self.test_switch_close()

@unittest.skip("no good reason")
class TestValveController(unittest.TestCase):

    def setUp(self):
        self.pc = PC()
        self.switch = VS()
        self.controller = VC(self.switch)
        
    def tearDown(self):
        self.pc.clean_up()

    def test_controller_state_initial(self):
        self.assertEqual(self.controller.state, pins.LOW)
        self.assertEqual(self.switch.state, self.controller.state)

    def test_controller_open(self):
        self.controller.open_valve()
        self.assertEqual(self.controller.state, pins.HIGH)
        self.assertEqual(self.switch.state, self.controller.state)

    def test_controller_close(self):
        self.controller.close_valve()
        self.assertEqual(self.controller.state, pins.LOW)
        self.assertEqual(self.switch.state, self.controller.state)

    def test_switch_toggle(self):
        old_state = self.controller.state
        self.assertEqual(self.switch.state, self.controller.state)
        self.controller.toggle_valve()
        self.assertNotEqual(self.controller.state, old_state)
        self.assertEqual(self.switch.state, self.controller.state)
        self.controller.toggle_valve()
        self.assertEqual(self.controller.state, old_state)
        self.assertEqual(self.switch.state, self.controller.state)


@unittest.skip("no good reason")
class TestValveMultiSwitch(unittest.TestCase):

    def setUp(self):
        self.pc = PC()
        self.switch = VMS()
        self.controller1 = VC(self.switch)
        self.controller1.name = "TestController1"
        self.switch.register_controller(self.controller1)
        self.controller2 = VC(self.switch)
        self.controller2.name = "TestController2"
        self.switch.register_controller(self.controller2)

        
    def tearDown(self):
        self.pc.clean_up()

    def test_controller_registration(self):
        self.assertEqual(len(self.switch.controllers), 2)
        self.assertEqual("TestController1", self.controller1.name)
        self.assertIn("TestController1", self.switch.controllers.keys())
        self.assertIs(self.switch.controllers["TestController1"], self.controller1)
        self.assertEqual("TestController2", self.controller2.name)
        self.assertIn("TestController2", self.switch.controllers.keys())
        self.assertIs(self.switch.controllers["TestController2"], self.controller2)

    def test_controller_state_initial(self):
        self.assertEqual(self.controller1.state, pins.LOW)
        self.assertEqual(self.controller2.state, pins.LOW)
        self.assertEqual(self.switch.state, self.controller1.state)


    def test_controller_open_single(self):
        self.controller1.open_valve()
        self.assertEqual(self.controller1.state, pins.HIGH)
        self.assertEqual(self.controller2.state, pins.LOW)
        self.assertEqual(self.switch.state, self.controller1.state)
    
    def test_controller_open_multi(self):
        self.test_controller_open_single()
        self.controller2.open_valve()
        self.assertEqual(self.controller2.state, pins.HIGH)
        self.assertEqual(self.controller1.state, pins.HIGH)
        self.assertEqual(self.switch.state, self.controller2.state)

    def test_controller_close_single(self):
        self.test_controller_open_multi()
        self.controller1.close_valve()
        self.assertEqual(self.controller1.state, pins.LOW)
        self.assertEqual(self.controller2.state, pins.HIGH)
        self.assertEqual(self.switch.state, self.controller2.state)

    def test_controller_close_multi(self):
        self.test_controller_close_single()
        self.controller2.close_valve()
        self.assertEqual(self.controller2.state, pins.LOW)
        self.assertEqual(self.controller1.state, pins.LOW)
        self.assertEqual(self.switch.state, self.controller2.state)
    
    def test_controller_close_force(self):
        self.test_controller_open_multi()
        self.controller1.close_valve(True)
        self.assertEqual(self.controller1.state, pins.LOW)
        self.assertEqual(self.controller2.state, pins.LOW)
        self.assertEqual(self.switch.state, self.controller2.state)

    def test_controller_toggle(self):
        self.test_controller_open_multi()
        self.controller1.toggle_valve()
        self.assertEqual(self.controller1.state, pins.LOW)
        self.assertEqual(self.controller2.state, pins.HIGH)
        self.assertEqual(self.switch.state, self.controller2.state)


@unittest.skip("no good reason")
class TestSprinklerAPI(unittest.TestCase):

    def setUp(self):
        self.pc = PC()
        self.switch = VMS()
        self.controller = VC(self.switch)
        self.controller.name = "TestController"
        self.switch.register_controller(self.controller)
        self.controller_new = VC(self.switch)
        self.controller_new.name = "TestControllerNew"
        self.switch.register_controller(self.controller_new)
        self.api = API(self.switch)
        
    def tearDown(self):
        self.pc.clean_up()

    def test_get_controller(self):
        controller = self.api.get_controller("TestController")
        self.assertIs(controller, self.controller)

    def test_start_sprinkler(self):
        self.api.start_sprinkler(self.controller)
        self.assertEqual(self.controller.state, pins.HIGH)
        self.assertEqual(self.switch.state, pins.HIGH)

    def test_stop_sprinkler(self):
        self.test_start_sprinkler()
        self.api.stop_sprinkler(self.controller)
        self.assertEqual(self.controller.state, pins.LOW)
        self.assertEqual(self.switch.state, pins.LOW)

    def test_stop_sprinker_force(self):
        self.api.start_sprinkler(self.controller)
        self.api.start_sprinkler(self.controller_new)
        self.assertEqual(self.controller.state, pins.HIGH)
        self.assertEqual(self.controller_new.state, pins.HIGH)
        self.assertEqual(self.switch.state, pins.HIGH)
        self.api.stop_sprinkler(self.controller, True)
        self.assertEqual(self.controller.state, pins.LOW)
        self.assertEqual(self.controller_new.state, pins.LOW)
        self.assertEqual(self.switch.state, pins.LOW)

    def test_is_sprinkler_started(self):
        self.api.start_sprinkler(self.controller)
        self.assertTrue(self.api.is_sprinkler_started())
        self.api.start_sprinkler(self.controller_new)
        self.assertTrue(self.api.is_sprinkler_started())
        self.api.stop_sprinkler(self.controller)
        self.assertTrue(self.api.is_sprinkler_started())
        self.api.stop_sprinkler(self.controller_new)
        self.assertFalse(self.api.is_sprinkler_started())

    def test_is_controller_started(self):
        self.api.start_sprinkler(self.controller)
        self.assertTrue(self.api.is_controller_started(self.controller))
        self.assertFalse(self.api.is_controller_started(self.controller_new))
        self.api.start_sprinkler(self.controller_new)
        self.assertTrue(self.api.is_controller_started(self.controller))
        self.assertTrue(self.api.is_controller_started(self.controller_new))
        self.api.stop_sprinkler(self.controller)
        self.assertFalse(self.api.is_controller_started(self.controller))
        self.assertTrue(self.api.is_controller_started(self.controller_new))
        self.api.stop_sprinkler(self.controller_new)
        self.assertFalse(self.api.is_controller_started(self.controller))
        self.assertFalse(self.api.is_controller_started(self.controller_new))
    

@unittest.skip("no good reason")
class TestCommandLineController(unittest.TestCase):

    def setUp(self):
        self.pc = PC()
        self.switch = VMS()
        self.api = API(self.switch)
        self.controller = CLI(self.switch, self.api)
        self.req_sub_ack = "Request has been submitted"
        
    def tearDown(self):
        self.controller.stop_server()
        self.pc.clean_up()

    def test_cli_server(self):
        data = [[["", "start"], self.req_sub_ack],
                [["", "is_controller_started"], True],
                [["", "is_sprinkler_started"], True]]
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.connect("tcp://localhost:%d" % SprinklerGlobals.CLI_SERVER_PORT)
        for d in data:
            dp = pickle.dumps(d[0])
            socket.send(dp)
            rp = socket.recv()
            r = pickle.loads(rp)
            self.assertEqual(r, d[1])


if __name__ == "__main__":
    unittest.main()
