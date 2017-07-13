import RPi.GPIO as pins
import SprinklerDB as DB
import SprinklerGlobals as globals
import SprinklerUtils as utils
import threading


# Globals
logger = utils.get_logger()
VALVE_PIN = globals.VALVE_PINi


# Operates the valve directly by changing the state of the GPIO pin
# Syncs the state of the Valve with the DB
class ValveSwitch(object):

    def __init__(self):

        logger.debug("Initializing Valve Switch")

        self.lock = threading.RLock()

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
    def sync(self):

        def log_sync_error(msg):
            logger.error("SYNC FAILED: %s",  msg)

        logger.debug("Syncing valve state with DB")

        success = 1
        con = get_connection()
        try:
            cursor = con.cursor()
            sql = "select state from Valve where id = (select max(id) from Valve);"
            cursor.execute(sql)
            data = cursor.fetchone()
            new_state = data['state']
            logger.debug("Valve state from DB: %s", state)
            if new_state is not None:
                succes = self.update(new_state)
            else:
                log_sync_error("Valve state is not available in DB")
                success = 0
        except Exception as ex:
            log_sync_error("Error occurred while fetching Valve state from DB:\n%s", ex)
            success = 0
        finally:
            close_connection(con)
    
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
        with self.lock:

            # Update the valve status
            try:
                self.state = new_state
                pins.output(VALVE_PIN, new_state)
            except Exception as ex:
                log_update_error("Error occurred while switching the pin state:\n %s" % ex)
                return 0

            # Update the DB
            con = DB.get_connection()
            try:
                con.begin()
                cursor = con.cursor()
                sql = "insert into Valve (state) Values (%d)"
                inserted = cursor.execute(sql, (new_state,))
                con.commit()
                logger.debug("Rows inserted: %d", inserted)
            except Exception as ex:
                log_update_error("Error occurred while saving state to DB:\n %s" % ex)
                logger.warn("Reverintg valve state to %d", old_state)
                self.state = old_state
                pins.output(VALVE_PIN, old_state)
                return 0
            finally:
                DB.close_connection(con)

        logger.debug("Updated valve state from %d to %d" % (old_state, new_state))


# Operates the valve directly and is controller aware
# The valve is updated with the concensus of all the controllers
class ValveMultiSwitch(ValveSwitch):

    def __init__(self):
        ValveSwitch.__init__(self)
        self.controllers = {}
        print "Valve Multi Switch has been initialized. No controllers have been registered yet"

    def register_controller(self, controller):
        if controller is None or not hasattr(controller, 'name') or controller.name is None:
            raise "Invalid controller. Cannot register"
        self.controllers[controller.name] = controller
        print "Controller %s has been registered" % controller.name

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

    def toggle(self):
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


# A basic valve controller
class ValveController(object):

    def __init__(self, switch):
        self.name = "ValveController"
        self.switch = switch
        self.state = pins.LOW
        print "Valve Controller has been initialized"

    def open_valve(self):
        self.state = pins.HIGH
        self.switch.open()
        print "Valve Controller has opened the valve"

    def close_valve(self, force=False):
        self.state = pins.LOW
        self.switch.close(force)
        print "Valve Controller has closed the valve"

    def toggle_valve(self):
        self.state = pins.HIGH if self.state is pins.LOW else pins.LOW
        self.switch.toggle()
        print "Valve Controller has toggled the valve"
