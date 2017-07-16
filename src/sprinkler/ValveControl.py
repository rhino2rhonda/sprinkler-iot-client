import SprinklerGlobals as globals

if globals.RPi_MODE:
    import RPi.GPIO as pins
else:
    import DummyGPIO as pins

import SprinklerDB as DB
import SprinklerUtils as utils
import threading
import time
import datetime

# Globals
logger = utils.get_logger()
PRODUCT_ID = globals.PRODUCT_ID
VALVE_PIN = globals.VALVE_PIN
VALVE_STATE_UPDATE_INTERVAL= globals.VALVE_STATE_UPDATE_INTERVAL

# Constants
VALVE_COMPONENT_NAME = 'valve'
REMOTE_SWITCH_COMPONENT_NAME = 'remote-switch'
TIMER_COMPONENT_NAME = 'timer'


# Fetches the ID of a component
def get_component_id(component_name):
   
    component_id = None
    
    with DB.Connection() as cursor:
    
        sql = "select c.id " +\
                "from component c " +\
                "join component_type t " +\
                "on c.component_type_id = t.id " +\
                "and t.component_name=%s " +\
                "and c.product_id=%s"
        
        count = 0
        try:
            count = cursor.execute(sql, (component_name, PRODUCT_ID))
        except Exception as ex: 
            logger.error("Error occurred while fetching component ID for component %s:\n%s", component_name, str(ex))
        
        if count is 0:
            logger.error("Component ID not found for component %s", component_name)
        else:
            data = cursor.fetchone()
            component_id = data['id']
            logger.debug("Component ID fetched for component %s: %d", component_name, component_id)
    
    return component_id


# Operates the valve directly by changing the state of the GPIO pin
# Syncs the state of the Valve with the DB
class ValveSwitch(object):

    def __init__(self):

        self.logger = utils.get_logger()
        self.logger.debug("Initializing Valve Switch")

        self.lock = threading.RLock()

        # Unique component ID
        self.component_id = get_component_id(VALVE_COMPONENT_NAME)
        if self.component_id is None:
            self.logger.error("Component ID not found in DB")
            raise Exception("Component ID not found in DB")

        # Setup valve pin
        pins.setup(VALVE_PIN, pins.OUT)
       
        # Initially, the valve is switched off
        self.state = pins.LOW
        pins.output(VALVE_PIN, pins.LOW)
        
        self.logger.debug("Valve Switch is up and running")

        # Update valve state from DB
        self.sync_with_db()
    
    
    # Updates the valve state from the latest state in the DB
    # Returns 1 for success and 0 for failure
    # In case of failure, valve state remains unchanged
    def sync_with_db(self):

        def log_sync_error(msg):
            self.logger.error("SYNC FAILED: %s",  msg)

        self.logger.debug("Syncing valve state with DB")

        with DB.Connection() as cursor:
            
            sql = "select state from valve_state where id = (select max(id) from valve_state where component_id=%s);"
        
            count = 0
            try:
                count = cursor.execute(sql, (self.component_id,)) 
            except Exception as ex:
                log_sync_error("Error occurred while fetching Valve state from DB:\n%s" % ex)
                return False

            if count is 0:
                # Valve state not found in DB (Would typically happen only when DB is empty)
                log_sync_error("Valve state is not available in DB")
                return False
            else:
                data = cursor.fetchone()
                new_state = data['state']
                self.logger.debug("Valve state from DB: %s", new_state)
                if new_state in [pins.LOW, pins.HIGH]:
                    # Update valve state
                    self.state = new_state
                    pins.output(VALVE_PIN, new_state)
                else:
                    # Some invlid state found in DB
                    log_sync_error("Invalid valve state obtained from DB: %s" % new_state)
                    return False
        
        self.logger.debug("Valve state has been synced with DB")
        return True


    # Updates the valve state at the pin and DB
    # State can be set as 1 for open and 0 for close
    # Throws SprinklerException if update fails
    def update(self, new_state):

        def update_error(msg):
            self.logger.error("UPDATE FAILED: %s",  msg)
            raise utils.SprinklerException(msg)

        self.logger.debug("Updating valve state")

        if new_state not in [pins.LOW, pins.HIGH]:
            update_error("Invalid valve state %s" % new_state)

        old_state = self.state
        if new_state is old_state:
            update_error("Valve state is already %d" % new_state)

        self.logger.debug("Valve state will be changed from %d to %d" % (old_state, new_state))

        # Update and pin and DB status in a transactional and thread safe manner
        with self.lock:
            with DB.Connection() as cursor:
                
                # Update the DB
                self.logger.debug("Updating valve state in DB")
                
                sql = "insert into valve_state (component_id, state) Values (%s, %s)"
                
                try:
                    inserted = cursor.execute(sql, (self.component_id, new_state))
                    self.logger.debug("Rows inserted: %d", inserted)
                except:
                    update_error("Error occurred while saving state to DB:\n %s" % ex)
                self.logger.debug("Updated valve state in DB")

                # Update the valve status at the pin
                self.logger.debug("Toggling pin state")
                try:
                    self.state = new_state
                    pins.output(VALVE_PIN, new_state)
                except Exception as ex:
                    update_error("Error occurred while switching the pin state:\n %s" % ex)
                self.logger.debug("Pin state has been toggled from %d to %d" % (old_state, new_state))

        self.logger.debug("Updated valve state from %d to %d" % (old_state, new_state))


# Stores controller state and related attributes
class ControllerState(object):

    def __init__(self, state, due_by, forced=False):
        self.state = state
        self.due_by = due_by
        self.forced = forced


# A basic valve controller that determines the valve state and maintains its own
# As there can be multpile controllers, a single controller does not directly controle the valve
# The only way to change the controller state should be by syncing it with the DB
# It basically needs to be extended to do useful stuff
class BasicValveController(object):

    def __init__(self, controller_name="BasicValveController"):

        self.logger = utils.get_logger()
        self.logger.debug("Initializing Valve Controller")
        
        # Assign a name to identify the controller
        self.name = controller_name

        # Unique component ID
        self.component_id = get_component_id(VALVE_COMPONENT_NAME)
        if self.component_id is None:
            self.logger.error("Component ID not found in DB")
            raise Exception("Component ID not found in DB")


    # Updates the cotroller state from the latest state in the DB
    # Returns True for success
    def sync_with_db(self):
        return True


    # Determines the current controller state
    def get_controller_state(self):
        return None


    # Perform any controller specific action that should occur after a valve update completes (successful or not)
    def valve_update_callback(this, updated_state):
        pass


# Manages a valve switch by changing its status with the consensus of all the valve controllers
class ValveManager(object):

    def __init__(self, switch, controllers = []):
        
        self.logger = utils.get_logger()

        self.switch = switch
        self.controllers = {}
        for controller in controllers:
            self.register_controller(controller)
        self.logger.debug("Valve Manager is up and running")

        # Start a daemon thread for valve status updates
        self.active = True
        self.update_thread = threading.Thread(target=self.keep_updating_valve_switch)
        self.update_thread.setDaemon(True)
        self.update_thread.start()
        

    # Registers a valve controller
    def register_controller(self, controller):
        
        if controller is None or not hasattr(controller, 'name') or controller.name is None:
            self.logger.error("Controller configuration is invalid. Cannot proceed.")
            raise "Invalid controller. Cannot register"
        self.controllers[controller.name] = controller
        self.logger.debug("Controller %s has been registered", controller.name)


    # To be executed as a thread to ensure that the valve state keeps getting updated
    def keep_updating_valve_switch(self):

        self.logger.debug("Valve switch update thread is up and running")
        while self.active:
            updated = self.update_valve_switch()           
            self.logger.debug("Valve switch update completed with status %s. Next update in %d seconds" % (updated, VALVE_STATE_UPDATE_INTERVAL))
            time.sleep(VALVE_STATE_UPDATE_INTERVAL)

        self.logger.debug("Valve switch update thread will now terminate")


    # Updates the valve switch with the consensus of the valve controllers
    def update_valve_switch(self):
            
        def log_update_error(msg):
            self.logger.error("UPDATE VALVE SWITCH ERROR: %s", msg)

        self.logger.debug("Syncing valve state controller states from DB")
        
        # Sync ad fetch latest state for all controllers
        controller_states = []
        sync_failed = False
        curr_time = datetime.datetime.now()
        for controller in self.controllers.values():
                
            # Sync controller with db
            success = controller.sync_with_db()
            if not success:
                # If sync fails, no further action should be taken as the system might end up in an inconsistent state
                log_update_error("Controller sync for controller %s was not successful")
                sync_failed = True
                break
            state = controller.get_controller_state()
            if state.due_by > curr_time:
                logger.debug("Skipping state for controller %s as state due time (%s) is after current time (%s)", controller.name, state.due_by, curr_time)
                continue
            controller_states.append(state)

        # Evaluate final state
        controller_states.sort(key=lambda cs: cs.due_by, reverse=True)
        computed_state = None
        for state in controller_states:
            if computed_state is None:
                computed_state = state
                continue
            if state.state is pins.HIGH or (state.state is pins.LOW and state.forced is True):
                computed_state = state
                break
        next_state = None if sync_failed or computed_state is None else computed_state.state 
        logger.debug("Computed next state for valve switch is %s", next_state)

        # Update the valve switch
        updated = False
        if next_state not in [pins.LOW, pins.HIGH]:
            log_update_error("Switch state is invalid: %s. Skipping update" % next_state)
        elif next_state is self.switch.state:
            log_update_error("Switch state is already %d. Skipping update" % next_state)
        else:
            try:
                self.switch.update(next_state)
                updated = True
                logger.debug("Updated valve state to %d", next_state)
            except SprinklerExcept as ex:
                log_update_error("Error occurred while updating valve switch to %d:\n%s" % (next_state, ex))
            except Exception as ex:
                log_update_error("An unhandled error has occurred while updating valve switch to %d:\n%s" % (next_state, ex))

        # Execute post update callbacks
        self.logger.debug("Executing post update controller callbacks")
        for controller in self.controllers.values():
            controller.valve_update_callback(computed_state if updated else None)
        
        return updated


class RemoteValveController(BasicValveController):

    def __init__(self):

        BasicValveController.__init__(self, REMOTE_SWITCH_COMPONENT_NAME)

        # Initial state
        self.state = pins.LOW
        self.state_id = None
        self.state_created = datetime.datetime.now()
        self.job_completed = False


    def sync_with_db(self):

        def log_sync_error(msg):
            self.logger.error("VALVE CONTROLLER SYNC FAILED: %s", msg)

        
        self.logger.debug("Syncing controller %s with db", self.name)
        with DB.Connection() as cursor:

            sql = "select id, state, completion_status, created from valve_remote_switch_job where " +\
                    "id=(select max(id) from valve_remote_switch_job where component_id=%s)"

            count = 0
            try:
                count = cursor.execute(sql, (self.component_id,))
            except Exception as ex:
                log_sync_error("Error occurred while fetching latest state for controller %s:\n%s", (self.name, ex))
                return False
            
            if count is 0:
                self.logger.warning("Controller state not found in DB for controller %s. Defaulting to off state" % self.name)
                self.state = pins.LOW
            else:
                row = cursor.fetchone()
                
                new_state = row['state']
                if new_state not in [pins.LOW, pins.HIGH]:
                    log_sync_error("Invalid state for controller %s was found in DB: %s" % (self.name, new_state))
                    return False
                
                state_id = row['id']
                if state_id is None:
                    log_sync_error("Invalid state id for controller %s was found in DB: %s" % (self.name, state_id))
                    return False

                state_created = row['created']
                if state_created is None or type(state_created) is not datetime.datetime:
                    log_sync_error("Invalid state created datetime for controller %s was found in DB: %s" % (self.name, state_created))
                    return False

                completion_status = row['completion_status']
                if completion_status is not None and completion_status not in [0,1]:
                    log_sync_error("Invalid completion status for controller %s was found in DB: %s" % (self.name, completion_status))
                    return False

                self.state = new_state
                self.state_id = state_id
                self.state_created - state_created
                self.job_completed = completion_status is not None
            
            return True


    def get_controller_state(self):
        self.logger.debug("Fetching controller state for controller %s" % self.name)
        forced = self.state_id is not None
        return ControllerState(self.state, self.state_created, forced)


    def valve_update_callback(self, updated_state):
        
        if updated_state is None:
            return

        self.logger.debug("Executing post valve update callback for controller %s", self.name)
       
        if self.job_completed:
            self.logger.debug("Job status has already been updated for controller %s", self.name)
            return
    
        expected_state = self.get_controller_state()
        job_completed = 1 if updated_state.state is expected_state.state else 0

        # Updating job status
        with DB.Connection() as cursor:
            
            sql = "update valve_remote_switch_job set completion_status=%s where id=%s"
           
            try:
                updated_rows = cursor.execute(sql, (job_completed, self.state_id))
                self.logger.info("Rows updated: %d", updated_rows)
                self.job_completed = True
                self.logger.debug("Job status updated for state id %d for controller %s", self.state_id, self.name)
            except Exception as ex:
                self.logger.error("Failed to update job status for state id %d for controller %s:\n%s", self.state_id, self.name, str(ex))


class ValveTimerController(BasicValveController):

    def __init__(self):

        BasicValveController.__init__(self, TIMER_COMPONENT_NAME)

        # Initialially timer is disabled
        self.timer_enabled = False
        self.start_time = None
        self.end_time = None
        self.timer_id = None
        self.timer_created = datetime.datetime.now()


    def sync_with_db(self):
        
        self.logger.debug("Syncing controller %s with DB", self.name)
        with DB.Connection() as cursor:

            sql = "select enabled, start_time, end_time from valve_timer where " +\
                    "id=(select max(id) from valve_timer where component_id=%s)"

            count = 0
            try:
                count = cursor.execute(sql, (self.component_id,))
            except Exception as ex:
                self.logger.error("Error occurred while fetching latest state for controller %s:\n%s", (self.name, ex))
                return False
            
            if count is 0:
                self.logger.warning("Controller state not found in DB for controller %s. Defaulting to off state" % self.name)
                self.timer_enabled = False
            else:
                row = cursor.fetchone()
                
                timer_enabled = row['enabled']
                if timer_enabled not in [0,1]:
                    self.logger.error("Invalid value for timer enabled found in DB for controller %s" % (self.name,))
                    return False
                if timer_enabled is 0:
                    self.timer_enabled = False
                    return True
                
                start_time = row['start_time']
                if start_time is None\
                    or type(start_time) is not datetime.timedelta\
                    or not 0 <= start_time.total_seconds() <= 24*60*60:
                        self.logger.error("Invalid value for timer start time found in DB for controller %s" % (self.name,))
                        return False
                
                end_time = row['end_time']
                if end_time is None\
                    or type(end_time) is not datetime.timedelta\
                    or not 0 <= end_time.total_seconds() <= 24*60*60:
                        self.logger.error("Invalid value for timer end time found in DB for controller %s" % (self.name,))
                        return False

                if start_time.total_seconds() > end_time.total_seconds():
                    self.logger.error("Invalid values: Start time is greater than end time for controller %s" % self.name)
                    return False

                self.timer_enabled = True
                self.start_time = start_time
                self.end_time = end_time
            
            return True


    def get_controller_state(self):
        self.logger.debug("Fetching controller state for controller %s" % self.name)
        curr_state = None
        
        if not self.timer_enabled:
            logger.debug("Valve timer is disabled")
            curr_state = pins.LOW
        else:
            curr_time = datetime.datetime.now()
            today_begin = datetime.datetime.combine(curr_time.date(), datetime.time.min)
            timer_start = today_begin + self.start_time
            timer_end = today_begin + self.end_time
            curr_state = pins.HIGH if timer_start < curr_time < timer_end else pins.LOW
            logger.debug("Valve timer is enabled. Current time lies in timer duration?: %d", curr_state)
        
        return ControllerState(curr_state, self.name)
