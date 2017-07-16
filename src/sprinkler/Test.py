import logging
import SprinklerGlobals as globals
globals.LOG_LEVEL = logging.DEBUG
globals.DB_PING_INTERVAL = 5
globals.VALVE_STATE_UPDATE_INTERVAL = 3
import SprinklerUtils as utils
import unittest
from PinsControl import PinsController as PC
import ValveControl
from ValveControl import ValveSwitch as VS
from ValveControl import RemoteValveController as RemoteVC
from ValveControl import ValveTimerController as TimerVC
from ValveControl import ValveManager as VM
import SprinklerDB as DB
import RPi.GPIO as pins
import random
import threading
import time
import datetime

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
            self.switch.update(pins.HIGH)
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
            self.switch.update(pins.LOW)
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
            
    # @unittest.skip("no good reason")
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
        num_threads = 20
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
class TestRemoteValveController(unittest.TestCase):

    def setUp(self):
        self.controller = RemoteVC()
        self.component_id = ValveControl.get_component_id(ValveControl.VALVE_COMPONENT_NAME)

    def latest_state_db(self):
        with DB.Connection() as cursor:
            sql = "select id,state,completion_status from valve_remote_switch_job where " +\
                    "id=(select max(id) from valve_remote_switch_job where component_id=%s)"
            count = cursor.execute(sql, (self.component_id,))
            if count is 0:
                return None
            else:
                row = cursor.fetchone()
                return row
    
    def update_controller(self, state, completion=None):
        with DB.Connection() as cursor:
            sql = "insert into valve_remote_switch_job (component_id, state, completion_status) Values(%s, %s, %s)"
            inserted = cursor.execute(sql, (self.component_id, state, completion))
            self.assertIs(inserted, 1)


    # @unittest.skip("no good reason")
    def test1_controller_sync_db_empty(self):
        db_state = self.latest_state_db()
        self.assertIs(db_state, None)
        success = self.controller.sync_with_db()
        self.assertTrue(success)
        self.assertEqual(self.controller.state, pins.LOW)
        controller_state = self.controller.get_controller_state()
        self.assertIs(controller_state.state, pins.LOW)
        self.assertFalse(controller_state.forced)


    # @unittest.skip("no good reason")
    def test2_controller_sync_open(self):
        self.update_controller(pins.HIGH)
        db_state = self.latest_state_db()
        db_state = db_state['state']
        self.assertIs(db_state, pins.HIGH)
        success = self.controller.sync_with_db()
        self.assertTrue(success)
        controller_state = self.controller.get_controller_state()
        self.assertIs(controller_state.state, pins.HIGH)
        self.assertTrue(controller_state.forced)

    # @unittest.skip("no good reason")
    def test3_controller_sync_close(self):
        self.update_controller(pins.LOW)
        db_state = self.latest_state_db()
        db_state = db_state['state']
        self.assertIs(db_state, pins.LOW)
        success = self.controller.sync_with_db()
        self.assertTrue(success)
        controller_state = self.controller.get_controller_state()
        self.assertIs(controller_state.state, pins.LOW)
        self.assertTrue(controller_state.forced)

    # @unittest.skip("no good reason")
    def test4_controller_sync_fail_open(self):
        self.test3_controller_sync_close()
        self.update_controller(-1)
        db_state = self.latest_state_db()
        db_state = db_state['state']
        self.assertIs(db_state, -1)
        success = self.controller.sync_with_db()
        self.assertFalse(success)
        controller_state = self.controller.get_controller_state()
        self.assertIs(controller_state.state, pins.LOW)
        self.assertTrue(controller_state.forced)

    # @unittest.skip("no good reason")
    def test5_controller_sync_fail_close(self):
        self.test2_controller_sync_open()
        self.update_controller(3)
        db_state = self.latest_state_db()
        db_state = db_state['state']
        self.assertIs(db_state, 3)
        success = self.controller.sync_with_db()
        self.assertFalse(success)
        controller_state = self.controller.get_controller_state()
        self.assertIs(controller_state.state, pins.HIGH)
        self.assertTrue(controller_state.forced)

    # @unittest.skip("no good reason")
    def test6_controller_sync_fail_invalid_completion(self):
        self.update_controller(0, -1)
        db_state = self.latest_state_db()
        self.assertEqual(db_state['completion_status'], -1)
        success = self.controller.sync_with_db()
        self.assertFalse(success)

    # @unittest.skip("no good reason")
    def test7_controller_job_update_success(self):
        self.update_controller(0)
        self.controller.sync_with_db()
        self.assertFalse(self.controller.job_completed)
        updated_state = ValveControl.ControllerState(pins.LOW, None)
        self.controller.valve_update_callback(updated_state)
        self.assertTrue(self.controller.job_completed)
        db_state = self.latest_state_db()
        self.assertIs(db_state['completion_status'], 1)
    
    # @unittest.skip("no good reason")
    def test8_controller_job_update_fail(self):
        self.update_controller(0)
        self.controller.sync_with_db()
        self.assertFalse(self.controller.job_completed)
        updated_state = ValveControl.ControllerState(pins.HIGH, None)
        self.controller.valve_update_callback(updated_state)
        self.assertTrue(self.controller.job_completed)
        db_state = self.latest_state_db()
        self.assertIs(db_state['completion_status'], 0)

    # @unittest.skip("no good reason")
    def test9_controller_job_update_unchanged(self):
        self.controller.job_completed = "TEMP"
        updated_state = ValveControl.ControllerState(pins.HIGH, None)
        self.controller.valve_update_callback(updated_state)
        self.assertEqual(self.controller.job_completed, "TEMP")


@unittest.skip("no good reason")
class TestValveTimerController(unittest.TestCase):

    def setUp(self):
        self.controller = TimerVC()
        self.component_id = ValveControl.get_component_id(ValveControl.VALVE_COMPONENT_NAME)

    def latest_state_db(self):
        with DB.Connection() as cursor:
            sql = "select enabled, start_time, end_time from valve_timer where " +\
                    "id=(select max(id) from valve_timer where component_id=%s)"
            count = cursor.execute(sql, (self.component_id,))
            if count is 0:
                return None
            else:
                row = cursor.fetchone()
                return row
    
    def update_controller(self, enabled, start_time=None, end_time=None):
        with DB.Connection() as cursor:
            sql = "insert into valve_timer (component_id, enabled, start_time, end_time) Values(%s, %s, %s, %s)"
            inserted = cursor.execute(sql, (self.component_id, enabled, start_time, end_time))
            self.assertIs(inserted, 1)

    def get_curr_time(self):
        curr_time = datetime.datetime.now().time()
        return datetime.timedelta(hours=curr_time.hour, minutes=curr_time.minute, seconds=curr_time.second)

    # @unittest.skip("no good reason")
    def test1_controller_sync_db_empty(self):
        db_state = self.latest_state_db()
        self.assertIs(db_state, None)
        success = self.controller.sync_with_db()
        self.assertTrue(success)
        self.assertFalse(self.controller.timer_enabled)
        controller_state = self.controller.get_controller_state()
        self.assertIs(controller_state.state, pins.LOW)
        self.assertFalse(controller_state.forced)

    # @unittest.skip("no good reason")
    def test2_controller_sync_open(self):
        curr_time = self.get_curr_time()
        test_start_time = curr_time - datetime.timedelta(minutes=10)
        test_end_time = curr_time + datetime.timedelta(minutes=10)
        self.update_controller(True, test_start_time, test_end_time)
        db_state = self.latest_state_db()
        self.assertIsNot(db_state, None)
        self.assertIs(db_state['enabled'], 1)
        self.assertEqual(db_state['start_time'].total_seconds(), test_start_time.total_seconds())
        self.assertEqual(db_state['end_time'].total_seconds(), test_end_time.total_seconds())
        success = self.controller.sync_with_db()
        self.assertTrue(success)
        self.assertTrue(self.controller.timer_enabled)
        self.assertEqual(self.controller.start_time.total_seconds(), test_start_time.total_seconds())
        self.assertEqual(self.controller.end_time.total_seconds(), test_end_time.total_seconds())
        controller_state = self.controller.get_controller_state()
        self.assertIs(controller_state.state, pins.HIGH)
        self.assertFalse(controller_state.forced)

    # @unittest.skip("no good reason")
    def test3_controller_sync_close_1(self):
        curr_time = self.get_curr_time()
        test_start_time = curr_time - datetime.timedelta(minutes=20)
        test_end_time = curr_time - datetime.timedelta(minutes=10)
        self.update_controller(True, test_start_time, test_end_time)
        db_state = self.latest_state_db()
        self.assertIsNot(db_state, None)
        self.assertIs(db_state['enabled'], 1)
        self.assertEqual(db_state['start_time'].total_seconds(), test_start_time.total_seconds())
        self.assertEqual(db_state['end_time'].total_seconds(), test_end_time.total_seconds())
        success = self.controller.sync_with_db()
        self.assertTrue(success)
        self.assertTrue(self.controller.timer_enabled)
        self.assertEqual(self.controller.start_time.total_seconds(), test_start_time.total_seconds())
        self.assertEqual(self.controller.end_time.total_seconds(), test_end_time.total_seconds())
        controller_state = self.controller.get_controller_state()
        self.assertIs(controller_state.state, pins.LOW)
        self.assertFalse(controller_state.forced)

    # @unittest.skip("no good reason")
    def test4_controller_sync_close_2(self):
        self.update_controller(False)
        db_state = self.latest_state_db()
        self.assertIsNot(db_state, None)
        self.assertIs(db_state['enabled'], 0)
        success = self.controller.sync_with_db()
        self.assertTrue(success)
        self.assertFalse(self.controller.timer_enabled)
        controller_state = self.controller.get_controller_state()
        self.assertIs(controller_state.state, pins.LOW)
        self.assertFalse(controller_state.forced)

    # @unittest.skip("no good reason")
    def test5_controller_sync_fail_missing_start_end_times(self):
        old_timer_enabled = self.controller.timer_enabled
        old_start_time = self.controller.start_time
        old_end_time = self.controller.end_time
        old_state = self.controller.get_controller_state()
        self.update_controller(True)
        db_state = self.latest_state_db()
        self.assertIsNot(db_state, None)
        self.assertIs(db_state['enabled'], 1)
        self.assertIs(db_state['start_time'], None)
        self.assertIs(db_state['end_time'], None)
        success = self.controller.sync_with_db()
        self.assertFalse(success)
        self.assertEqual(self.controller.timer_enabled, old_timer_enabled)
        self.assertEqual(self.controller.start_time, old_start_time)
        self.assertEqual(self.controller.end_time, old_end_time)
        controller_state = self.controller.get_controller_state()
        self.assertEqual(controller_state.state, old_state.state)
        self.assertEqual(controller_state.forced, old_state.forced)
       

    # @unittest.skip("no good reason")
    def test6_controller_sync_fail_invalid_start_end_times(self):
        old_timer_enabled = self.controller.timer_enabled
        old_start_time = self.controller.start_time
        old_end_time = self.controller.end_time
        old_state = self.controller.get_controller_state()
        curr_time = self.get_curr_time()
        test_start_time = curr_time + datetime.timedelta(minutes=10)
        test_end_time = curr_time - datetime.timedelta(minutes=10)
        self.update_controller(True, test_start_time, test_end_time)
        db_state = self.latest_state_db()
        self.assertIsNot(db_state, None)
        self.assertIs(db_state['enabled'], 1)
        self.assertEqual(db_state['start_time'].total_seconds(), test_start_time.total_seconds())
        self.assertEqual(db_state['end_time'].total_seconds(), test_end_time.total_seconds())
        success = self.controller.sync_with_db()
        self.assertFalse(success)
        self.assertEqual(self.controller.timer_enabled, old_timer_enabled)
        self.assertEqual(self.controller.start_time, old_start_time)
        self.assertEqual(self.controller.end_time, old_end_time)
        controller_state = self.controller.get_controller_state()
        self.assertEqual(controller_state.state, old_state.state)
        self.assertEqual(controller_state.forced, old_state.forced)
       

    # @unittest.skip("no good reason")
    def test7_controller_sync_fail_invalid_enabled_flag(self):
        old_timer_enabled = self.controller.timer_enabled
        old_start_time = self.controller.start_time
        old_end_time = self.controller.end_time
        old_state = self.controller.get_controller_state()
        curr_time = self.get_curr_time()
        test_start_time = curr_time - datetime.timedelta(minutes=10)
        test_end_time = curr_time + datetime.timedelta(minutes=10)
        self.update_controller(3, test_start_time, test_end_time)
        db_state = self.latest_state_db()
        self.assertIsNot(db_state, None)
        self.assertIs(db_state['enabled'], 3)
        success = self.controller.sync_with_db()
        self.assertFalse(success)
        self.assertEqual(self.controller.timer_enabled, old_timer_enabled)
        self.assertEqual(self.controller.start_time, old_start_time)
        self.assertEqual(self.controller.end_time, old_end_time)
        controller_state = self.controller.get_controller_state()
        self.assertEqual(controller_state.state, old_state.state)
        self.assertEqual(controller_state.forced, old_state.forced)


class TestValveController(ValveControl.BasicValveController):

    def __init__(self, name):

        ValveControl.BasicValveController.__init__(self, name)
        self.controller_state = ValveControl.ControllerState(pins.LOW, datetime.datetime.now())

    def get_controller_state(self):
        return self.controller_state
    

# @unittest.skip("no good reason")
class TestValveManager(unittest.TestCase):

    def setUp(self):
        self.pc = PC()
        self.switch = VS()
        self.testVC1 = TestValveController('test-1')
        self.testVC2 = TestValveController('test-2')
        self.vm = VM(self.switch, [self.testVC1, self.testVC2])
        
    def tearDown(self):
        self.vm.active = False
        self.vm.update_thread.join()
        self.pc.clean_up()

    def stop_update_thread(self):
        self.vm.active = False
        self.vm.update_thread.join()

    @unittest.skip("no good reason")
    def test1_init(self):
        self.assertIsNot(self.switch, None)
        self.assertIs(len(self.vm.controllers), 2)
        self.assertIsNot(self.vm.controllers[self.testVC1.name], None)
        self.assertIsNot(self.vm.controllers[self.testVC2.name], None)

    @unittest.skip("no good reason")
    def test2_valve_open_success_scenarios(self):
        self.stop_update_thread()
        total_tests = 3
        for test_num in range(total_tests):
            
            try:
                self.switch.update(pins.LOW)
            except utils.SprinklerException as ex:
                pass

            self.assertIs(self.switch.state, pins.LOW)
            curr_time = datetime.datetime.now()
            time_delta_10mins = datetime.timedelta(minutes=10)
           
            # Both open
            if test_num is 0:
                self.testVC1.controller_state = ValveControl.ControllerState(pins.HIGH, curr_time - time_delta_10mins)
                self.testVC2.controller_state = ValveControl.ControllerState(pins.HIGH, curr_time - time_delta_10mins)

            # Both open, one future
            elif test_num is 1:
                self.testVC1.controller_state = ValveControl.ControllerState(pins.HIGH, curr_time + time_delta_10mins)
                self.testVC2.controller_state = ValveControl.ControllerState(pins.HIGH, curr_time - time_delta_10mins)

            # One open, one close
            elif test_num is 2:
                self.testVC1.controller_state = ValveControl.ControllerState(pins.LOW, curr_time - time_delta_10mins)
                self.testVC2.controller_state = ValveControl.ControllerState(pins.HIGH, curr_time - time_delta_10mins)
            
            success = self.vm.update_valve_switch()
            self.assertTrue(success)
            self.assertEqual(self.switch.state, pins.HIGH)
            

    # @unittest.skip("no good reason")
    def test3_valve_close_success_scenarios(self):
        self.stop_update_thread()
        total_tests = 4
        for test_num in range(total_tests):
            
            try:
                self.switch.update(pins.HIGH)
            except utils.SprinklerException as ex:
                pass

            self.assertIs(self.switch.state, pins.HIGH)
            curr_time = datetime.datetime.now()
            time_delta_10mins = datetime.timedelta(minutes=10)
            time_delta_5mins = datetime.timedelta(minutes=5)
           
            # Both close
            if test_num is 0:
                self.testVC1.controller_state = ValveControl.ControllerState(pins.LOW, curr_time - time_delta_10mins)
                self.testVC2.controller_state = ValveControl.ControllerState(pins.LOW, curr_time - time_delta_10mins)

            # Both close, one forced
            elif test_num is 1:
                self.testVC1.controller_state = ValveControl.ControllerState(pins.LOW, curr_time - time_delta_10mins)
                self.testVC2.controller_state = ValveControl.ControllerState(pins.LOW, curr_time - time_delta_10mins, True)

            # One close, one open future
            elif test_num is 2:
                self.testVC1.controller_state = ValveControl.ControllerState(pins.LOW, curr_time - time_delta_10mins)
                self.testVC2.controller_state = ValveControl.ControllerState(pins.HIGH, curr_time + time_delta_10mins)

            # One open then one force close
            elif test_num is 3:
                self.testVC1.controller_state = ValveControl.ControllerState(pins.LOW, curr_time - time_delta_5mins, True)
                self.testVC2.controller_state = ValveControl.ControllerState(pins.HIGH, curr_time - time_delta_10mins)
            
            success = self.vm.update_valve_switch()
            self.assertTrue(success)
            self.assertEqual(self.switch.state, pins.LOW)
            

if __name__ == "__main__":
    unittest.main()
