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
    con = DB.get_connection()
    try:
        cursor = con.cursor()
        sql = "select c.id " +\
                "from component c " +\
                "join component_type t " +\
                "on c.component_type_id = t.id " +\
                "and t.component_name=%s " +\
                "and c.product_id=%s"
        count = cursor.execute(sql, (component_name, PRODUCT_ID))
        if count is 0:
            logger.error("Component ID not found for component %s", component_name)
        else:
            data = cursor.fetchone()
            component_id = data['id']
            logger.debug("Component ID fetched for component %s: %d", component_name, component_id)
    except Exception as ex:
        logger.debug("Error occurred while fetching component ID for component %s:\n%s", component_name, str(ex))
    finally:
        DB.close_connection(con)
    return component_id
    

# Fetches the ID of a component
def get_controller_type_id(controller_name):
    controller_id = None
    con = DB.get_connection()
    try:
        cursor = con.cursor()
        sql = "select id from valve_controller_type t where t.controller_name=%s"
        count = cursor.execute(sql, (controller_name,))
        if count is 0:
            logger.error("Controller type ID not found for controller %s", controller_name)
        else:
            data = cursor.fetchone()
            controller_id = data['id']
            logger.debug("Controller type ID fetched for controller %s: %d", controller_name, controller_id)
    except Exception as ex:
        logger.debug("Error occurred while fetching controller type ID for controller %s:\n%s", controller_name, str(ex))
    finally:
        DB.close_connection(con)
    return controller_id


# Operates the valve directly by changing the state of the GPIO pin
# Syncs the state of the Valve with the DB
class ValveSwitch(object):

    def __init__(self):

        logger.debug("Initializing Valve Switch")

        self.lock = threading.RLock()

        # Unique component ID
        self.component_id = get_component_id(VALVE_COMPONENT_NAME)
        if self.component_id is None:
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
        return self.update(new_state)


    # Closes the valve
    def close(self):
        logger.debug("Closing the Valve")
        new_state = pins.LOW
        return self.update(new_state)

    # Updates the valve state from the latest state in the DB
    # Returns 1 for success and 0 for failure
    def sync(self):

        def log_sync_error(msg):
            logger.error("SYNC FAILED: %s",  msg)

        logger.debug("Syncing valve state with DB")

        success = 1
        con = DB.get_connection()
        try:
            cursor = con.cursor()
            sql = "select state from valve_state where id = (select max(id) from valve_state where component_id=%s);"
            count = cursor.execute(sql, (self.component_id,))
            if count is 0:
                log_sync_error("Valve state is not available in DB")
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


    # Updates the valve state at the pin and DB
    # Returns 1 for success and 0 for failure
    def update(self, new_state):

        def log_update_error(msg):
            logger.error("UPDATE FAILED: %s",  msg)

        logger.debug("Updating valve state")

        if new_state not in [pins.LOW, pins.HIGH]:
            log_update_error("Invalid valve state %s" % new_state)
            return 0

        old_state = self.state
        if new_state is old_state:
            log_update_error("Valve state is already %d" % new_state)
            return 0

        logger.debug("Valve state will be changed from %d to %d" % (old_state, new_state))

        # Update and pin and DB status in a transactional and thread safe manner
        success = 1
        with self.lock:

            # Update the valve status
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
                sql = "insert into valve_state (component_id, state) Values (%s, %s)"
                inserted = cursor.execute(sql, (self.component_id, new_state))
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

# Init
# Reg cotrollers
# Open Close
class ValveManager(object):

    def __init__(self, switch):
        self.switch
        self.controllers = {}
        logger.debug("Valve Manager has been initialized. No controllers have been registered yet")

    def register_controller(self, controller):
        if controller is None or not hasattr(controller, 'name') or controller.name is None:
            raise "Invalid controller. Cannot register"
        self.controllers[controller.name] = controller
        logger.debug("Controller %s has been registered", controller.name)

    def reset_controller_states(self):
        for controller in self.controllers.values():
            controller.state = pins.LOW
        print "All controllers states have been reset"

    def open(self):
        self.update()

    def close(self, force=False):
        if force:
            self.reset_controller_states()
            print "Attempting to close the valve forcefully"
        self.update()

    def update(self):
        open_controllers = filter(lambda x : x.state == pins.HIGH, self.controllers.values())
        updated_state = pins.HIGH if len(open_controllers) > 0 else pins.LOW
        if self.state is not updated_state and updated_state == pins.LOW:
            super(ValveMultiSwitch, self).close()
        elif self.state is not updated_state and updated_state == pins.HIGH:
            super(ValveMultiSwitch, self).open()
        else:
            print "Valve state has not been changed"


# A basic valve controller that DOES NOT control the valve
# It simply controls its own state and does other things
# It basically needs to be extended to do usefulstuff
class BasicValveController(object):

    def __init__(self, name="BasicValveController"):

        # Assign a name to identify the controller
        self.name = name

        # Initially, controller is off
        self.state = pins.LOW

        logger.debug("Valve Controller (%s) has been initialized" % self.name)


    # Marks controller as opened
    def open(self):
        logger.debug("Opening the Controller %s" % self.name)
        new_state = pins.HIGH
        return self.update(new_state)


    # MArks controller as closed
    def close(self, force=0):
        logger.debug("Closing the Controller %s" % self.name)
        new_state = pins.LOW
        return self.update(new_state, force)

    # Updates the controller state from the latest state in the DB
    # Returns 1 for success and 0 for failure
    def sync(self):

        def log_sync_error(msg):
            logger.error("SYNC FAILED: %s",  msg)

        logger.debug("Syncing valve state with DB")

        success = 1
        con = DB.get_connection()
        try:
            cursor = con.cursor()
            sql = "select state from Valve where id = (select max(id) from Valve);"
            count = cursor.execute(sql)
            if count is 0:
                log_sync_error("Valve state is not available in DB")
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


    # Updates the valve state at the pin and DB
    # Returns 1 for success and 0 for failure
    def update(self, new_state):

        def log_update_error(msg):
            logger.error("UPDATE FAILED: %s",  msg)

        logger.debug("Updating valve state")

        if new_state not in [pins.LOW, pins.HIGH]:
            log_update_error("Invalid valve state %s" % new_state)
            return 0

        old_state = self.state
        if new_state is old_state:
            log_update_error("Valve state is already %d" % new_state)
            return 0

        logger.debug("Valve state will be changed from %d to %d" % (old_state, new_state))

        # Update and pin and DB status in a transactional and thread safe manner
        success = 1
        with self.lock:

            # Update the valve status
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
