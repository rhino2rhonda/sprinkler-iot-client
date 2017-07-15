import logging
import SprinklerGlobals as globals
globals.LOG_LEVEL = logging.INFO
globals.DB_PING_INTERVAL = 0.01
import unittest
from PinsControl import PinsController as PC
from ValveControl import ValveSwitch as VS
import SprinklerDB as DB
import RPi.GPIO as pins
import random
import threading
import time

@unittest.skip("no good reason")
class TestValveSwitch(unittest.TestCase):

    def setUp(self):
        self.pc = PC()
        self.switch = VS()
        
    def tearDown(self):
        self.pc.clean_up()

    def get_db_state(self):
        state = None
        with DB.Connection as cursor:
            sql = "select state from valve_state where id = (select max(id) from valve_state where component_id=%s);"
            count = cursor.execute(sql, (self.switch.component_id,))
            if count is not 0:
                data = cursor.fetchone()
                state = data['state']
        return state
   
    # @unittest.skip("no good reason")
    def test1_switch_initial_state(self):
        db_state = self.get_db_state()
        if db_state is None:
            self.assertEqual(self.switch.state, pins.LOW)
        else:
            self.assertEqual(self.switch.state, db_state)

    # @unittest.skip("no good reason")
    def test2_switch_open(self):
        success = 1
        try:
            self.switch.open()
        except:
            success = 0
        db_state = self.get_db_state()
        self.assertEqual(self.switch.state, pins.HIGH)
        self.assertEqual(db_state, pins.HIGH)
        return success

    # @unittest.skip("no good reason")
    def test3_switch_close(self):
        success = 1
        try:
            self.switch.close()
        except:
            success = 0
        db_state = self.get_db_state()
        self.assertEqual(self.switch.state, pins.LOW)
        self.assertTrue(db_state in [None, pins.LOW])
        return success

    # @unittest.skip("no good reason")
    def test4_switch_many_toggles(self): 
        old_state = self.get_db_state()
        if old_state is None: old_state = 0
        iters = 10
        for i in range(iters):
            req_new_state = random.randint(0,1)
            exp_success = 0 if old_state is req_new_state else 1
            # print "\n\n NEW TEST %d of %d:\tPrev State: %s\tNext State: %d\tExpected Success: %d" % (i+1, iters, old_state, req_new_state, exp_success)
            success = self.test2_switch_open() if req_new_state is 1 else self.test3_switch_close()
            # print "Update success: %s" % success
            self.assertEqual(exp_success, success)
            old_state = req_new_state
        self.test3_switch_close()


@unittest.skip("no good reason")
class TestDBConnection(unittest.TestCase):

    def setUp(self):
        self.connection = DB.Connection()
    
    @classmethod
    def tearDownClass(Cls):
        connection = DB.Connection()
        connection.close_connection()
        connection.keep_alive_thread.join()

    # @unittest.skip("no good reason")
    def test1_singularity(self):
        anotherConnection = DB.Connection()
        self.assertIs(self.connection, anotherConnection)

    # @unittest.skip("no good reason")
    def test2_simple_query(self):
        with self.connection() as cursor:
            sql = "Select 1"
            cursor.execute(sql)
            row = cursor.fetchone()
            self.assertIsNot(row, None)
            
    #@unittest.skip("no good reason")
    def test3_cursor_close(self):
        cursor = None
        sql = "Select 1"
        with self.connection() as cursor:
            cursor.execute(sql)
            cursor.execute(sql)
        failed = 0
        try:
            cursor.execute(sql)
        except:
            failed = 1
        self.assertIs(failed, 1)

    # @unittest.skip("no good reason")
    def test4_auto_commit(self):
        with self.connection() as cursor:
            sql = "insert into product_type (product_name) Values(%s)"
            inserted = cursor.execute(sql, ("Test",))
            self.assertIs(inserted, 1)
        with self.connection() as cursor:
            sql = "select * from product_type where product_name=%s"
            count = cursor.execute(sql, ("Test",))
            self.assertIs(count, 1)
            row = cursor.fetchone()
            self.assertEqual(row['product_name'],"Test")
        with self.connection() as cursor:
            sql = "delete from product_type where product_name=%s"
            deleted = cursor.execute(sql, ("Test",))
            self.assertIs(deleted, 1)
        with self.connection() as cursor:
            sql = "select * from product_type where product_name=%s"
            count = cursor.execute(sql, ("Test",))
            self.assertIs(count, 0)

    # @unittest.skip("no good reason")
    def test5_rollback_db_exception(self):
        pass_ = True
        try:
            with self.connection() as cursor:
                sql = "insert into product_type (product_name) Values(%s)"
                inserted = cursor.execute(sql, ("Test",))
                self.assertIs(inserted, 1)
                incorrect_sql = "select * from table_not_defined"
                cursor.execute()
                pass_ = False
        except:
            pass 
        self.assertTrue(pass_)
        with self.connection() as cursor:
            sql = "select * from product_type where product_name=%s"
            count = cursor.execute(sql, ("Test",))
            self.assertIs(count, 0)

    # @unittest.skip("no good reason")
    def test6_rollback_other_exception(self):
        pass_ = True
        try:
            with self.connection() as cursor:
                sql = "insert into product_type (product_name) Values(%s)"
                inserted = cursor.execute(sql, ("Test",))
                self.assertIs(inserted, 1)
                5/0
                pass_ = False
        except:
            pass 
        self.assertTrue(pass_)
        with self.connection() as cursor:
            sql = "select * from product_type where product_name=%s"
            count = cursor.execute(sql, ("Test",))
            self.assertIs(count, 0)

    
    # @unittest.skip("no good reason")
    def test7_synchronised_access(self):
        pass_ = True
        shared = {"counter" : 0}
        num_threads = 100
        sleep_time = 0.2
        def increment(i, shared):
            with self.connection() as cursor:
                if shared["counter"] is not 0:
                    pass_ = False
                shared["counter"] += 1
                time.sleep(sleep_time)
                shared["counter"] -= 1
        threads = []
        for x in range(num_threads):
            thrd = threading.Thread(target=increment, args=(x+1, shared))
            thrd.start()
            threads.append(thrd)
        for i,thrd in enumerate(threads):
            thrd.join()

        self.assertIs(shared["counter"], 0)
        self.assertTrue(pass_)
            

    @unittest.skip("no good reason")
    def test8_interactive_connection_revival(self):
        def test_connection():
            with self.connection as cursor:
                sql = "select 1"
                cursor.execute(sql)
        
        self.connection.active = False
        self.connection.keep_alive_thread.join()

        test_connection()
        
        raw_input("Disable socket connection and press ENTER")
        pass_ = True
        try:
            test_connection()
            pass_ = False
        except:
            pass
        self.assertTrue(pass_)

        revived = self.connection.revive_connection()
        self.assertFalse(revived)

        raw_input("Renable socket connection and press ENTER")
        revived = self.connection.revive_connection()
        self.assertTrue(revived)
        test_connection()

        
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
