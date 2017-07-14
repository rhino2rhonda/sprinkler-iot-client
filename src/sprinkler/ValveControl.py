import RPi.GPIO as pins
import SprinklerDB as DB
import SprinklerGlobals as globals
import SprinklerUtils as utils
import threading


# Globals
logger = utils.get_logger()
PRODUCT_ID = globals.PRODUCT_ID
VALVE_PIN = globals.VALVE_PIN


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
    

# Fetches the ID of a component
def get_controller_type_id(controller_name):

    controller_id = None
    
    with DB.Connection() as cursor:
        
        sql = "select id from valve_controller_type t where t.controller_name=%s"
        
        count = 0
        try:
            count = cursor.execute(sql, (controller_name,))
        except Exception as ex:
            logger.error("Error occurred while fetching controller type ID for controller %s:\n%s", controller_name, str(ex))
 
        if count is 0:
            logger.error("Controller type ID not found for controller %s", controller_name)
        else:
            data = cursor.fetchone()
            controller_id = data['id']
            logger.debug("Controller type ID fetched for controller %s: %d", controller_name, controller_id)
    
    return controller_id


# Operates the valve directly by changing the state of the GPIO pin
# Syncs the state of the Valve with the DB
class ValveSwitch(object):

    def __init__(self):

        # TODO: Own logger
        logger.debug("Initializing Valve Switch")

        self.lock = threading.RLock()

        # Unique component ID
        self.component_id = get_component_id(VALVE_COMPONENT_NAME)
        if self.component_id is None:
            logger.error("Component ID not found in DB")
            raise Exception("Component ID not found in DB")

        # Setup valve pin
        pins.setup(VALVE_PIN, pins.OUT)
       
        # Initially, the valve is switched off
        self.state = pins.LOW
        pins.output(VALVE_PIN, pins.LOW)
        
        logger.debug("Valve Switch is up and running")

        # Update valve state from DB
        self.sync()


    # Opens the valve
    def open(self):
        logger.debug("Opening the Valve")
        new_state = pins.HIGH
        self.update(new_state)


    # Closes the valve
    def close(self):
        logger.debug("Closing the Valve")
        new_state = pins.LOW
        self.update(new_state)


    # Updates the valve state from the latest state in the DB
    # Returns 1 for success and 0 for failure
    # In case of failure, valve state remains unchanged
    def sync(self):

        def log_sync_error(msg):
            logger.error("SYNC FAILED: %s",  msg)

        logger.debug("Syncing valve state with DB")

        with DB.Connection() as cursor:
            
            sql = "select state from valve_state where id = (select max(id) from valve_state where component_id=%s);"
        
            count = 0
            try:
                count = cursor.execute(sql, (self.component_id,)) 
            except Exception as ex:
                log_sync_error("Error occurred while fetching Valve state from DB:\n%s" % ex)
                return 0

            if count is 0:
                # Valve state not found in DB (Would typically happen only when DB is empty)
                log_sync_error("Valve state is not available in DB")
                return 0
            else:
                data = cursor.fetchone()
                new_state = data['state']
                logger.debug("Valve state from DB: %s", new_state)
                if new_state in [pins.LOW, pins.HIGH]:
                    # Update valve state
                    self.state = new_state
                    pins.output(VALVE_PIN, new_state)
                else:
                    # Some invlid state found in DB
                    log_sync_error("Invalid valve state obtained from DB: %s" % new_state)
                    return 0
        
        logger.debug("Valve state has been synced with DB")
        return 1


    # Updates the valve state at the pin and DB
    # Returns 1 for success and 0 for failure
    def update(self, new_state):

        def update_error(msg):
            logger.error("UPDATE FAILED: %s",  msg)
            raise utils.SprinklerException(msg)

        logger.debug("Updating valve state")

        if new_state not in [pins.LOW, pins.HIGH]:
            update_error("Invalid valve state %s" % new_state)

        old_state = self.state
        if new_state is old_state:
            update_error("Valve state is already %d" % new_state)

        logger.debug("Valve state will be changed from %d to %d" % (old_state, new_state))

        # Update and pin and DB status in a transactional and thread safe manner
        with self.lock:
            with DB.Connection() as cursor:
                
                # Update the DB
                logger.debug("Updating valve state in DB")
                
                sql = "insert into valve_state (component_id, state) Values (%s, %s)"
                
                try:
                    inserted = cursor.execute(sql, (self.component_id, new_state))
                    logger.debug("Rows inserted: %d", inserted)
                except:
                    update_error("Error occurred while saving state to DB:\n %s" % ex)
                logger.debug("Updated valve state in DB")

                # Update the valve status at the pin
                logger.debug("Toggling pin state")
                try:
                    self.state = new_state
                    pins.output(VALVE_PIN, new_state)
                except Exception as ex:
                    update_error("Error occurred while switching the pin state:\n %s" % ex)
                logger.debug("Pin state has been toggled from %d to %d" % (old_state, new_state))

        logger.debug("Updated valve state from %d to %d" % (old_state, new_state))



# Manages a valve switch by changing its status with the consensus of all the valve controllers
class ValveManager(object):

    def __init__(self, switch, controllers = []):
        
        self.switch
        
        self.controllers = {}
        for controller in controllers:
            self.register_controller(controller)
        logger.debug("Valve Manager has been initialized")
        
        # Update the controller and switch states from DB
        self.sync_controller_states()


    # Registers a valve controller
    def register_controller(self, controller):
        if controller is None or not hasattr(controller, 'name') or controller.name is None:
            raise "Invalid controller. Cannot register"
        self.controllers[controller.name] = controller
        logger.debug("Controller %s has been registered", controller.name)

    # Updates the controller state from the latest state in the DB
    # Returns 1 for success and 0 for failure
    def sunc_controller_states():
        def log_sync_error(msg):
            logger.error("SYNC FAILED: %s",  msg)

        logger.debug("Syncing state of conteoller %s with DB" % self.name)

        success = 1
        con = DB.get_connection()
        try:
            cursor = con.cursor()
            sql = "select state from valve_controller_state where id = " +\
                    "(select max(id) from valve_controller_state where " +\
                    "component_id=%s and controller_type_id=%s);"
            count = cursor.execute(sql, (self.component_id, self.controller_type_id))
            if count is 0:
                log_sync_error("State for controller %s is not available in DB" % self.name)
                success = 0
            else:
                data = cursor.fetchone()
                new_state = data['state']
                logger.debug("Valve state from DB: %s", new_state)
                success = self.update(new_state)
        except Exception as ex:
            log_sync_error("Error occurred while fetching Valve state from DB:\n%s" % ex)
            success = 0
        finally:
            DB.close_connection(con)
    
        if success is 1:
            logger.debug("Valve state has been synced with DB")

        return success


    def force_close(self):
        for controller in self.controllers.values():
            controller.state = pins.LOW
        print "All controllers states have been reset"


    # Updates the valve switch status with the consensus of the controllers
    def update_switch(self):
        open_controllers = filter(lambda x : x.state == pins.HIGH, self.controllers.values())
        updated_state = pins.HIGH if len(open_controllers) > 0 else pins.LOW
        if self.switch.state is updated_state:
            logger.warning("Switch state is already %d. State was not changed." % updated_state)
        elif updated_state == pins.LOW:
            logger.debug("Attempting to switch off the valve")
            self.switch.close()
        else:
            logger.debug("Attempting to switch on the valve")
            self.switch.open()


# A basic valve controller that controls the valve state (and its own state) through a valve manager
# It basically needs to be extended to do useful stuff
class BasicValveController(object):

    def __init__(self, valve_manager, controller_name="BasicValveController"):

        logger.debug("Initializing Valve Controller")
        
        self.valve_manager = valve_manager

        # Assign a name to identify the controller
        self.name = controller_name

        self.lock = threading.RLock()

        # Unique component and controller ID
        self.component_id = valve_manager.switch.component_id
        seld.controller_type_id = get_controller_type_id(controller_name)
        if self.controller_type_id is None: 
            logger.error("Controller type ID not found in DB for controller %s" % controller_name)
            raise Exception("Controller tpye ID not found in DB for controller %s" % controller_name)
       
        # Initially, controller is off
        self.state = pins.LOW

        logger.debug("Valve Controller (%s) has been initialized" % controller_name)
        

    # Marks controller as open and opens the valve
    def open(self):
        logger.debug("Opening the Controller %s" % self.name)
        new_state = pins.HIGH
        return self.update(new_state)


    # Marks controller as closed and tries to close the valve
    def close(self):
        logger.debug("Closing the Controller %s" % self.name)
        new_state = pins.LOW
        return self.update(new_state)


    # Updates the controller state in the DB
    # Also updates the valve switch state through the valve manager
    # Returns 1 for success and 0 for failure
    def update(self, new_state):

        def log_update_error(msg):
            logger.error("UPDATE FAILED: %s",  msg)

        logger.debug("Updating state for controller %s" % self.name)

        if new_state not in [pins.LOW, pins.HIGH]:
            log_update_error("Invalid controller state %s" % new_state)
            return 0

        old_state = self.state
        if new_state is old_state:
            log_update_error("Controller state is already %d" % new_state)
            return 0

        logger.debug("Valve state will be changed from %d to %d" % (old_state, new_state))

        # Update controller and switch state in DB in a transactional and thread safe manner
        success = 1
        with self.lock:

            # Update the switch state
            self.state = new_state
            self.valve_manager.update_switch_state()


            logger.debug("Toggling pin state")
            try:
                self.state = new_state
                pins.output(VALVE_PIN, new_state)
            except Exception as ex:
                log_update_error("Error occurred while switching the pin state:\n %s" % ex)
                return 0
            logger.debug("Pin state has been toggled from %d to %d" % (old_state, new_state))

            # Update the DB
            logger.debug("Updating valve state in DB")
            con = DB.get_connection()
            try:
                con.begin()
                cursor = con.cursor()
                sql = "insert into Valve (state) Values (%s)"
                inserted = cursor.execute(sql, (new_state,))
                con.commit()
                logger.debug("Rows inserted: %d", inserted)
            except Exception as ex:
                log_update_error("Error occurred while saving state to DB:\n %s" % ex)
                logger.warn("Reverting valve state to %d", old_state)
                self.state = old_state
                pins.output(VALVE_PIN, old_state)
                success = 0
            finally:
                DB.close_connection(con)
            logger.debug("Updated valve state in DB")

        logger.debug("Updated valve state from %d to %d" % (old_state, new_state))

        return success
