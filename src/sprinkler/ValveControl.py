import RPi.GPIO as pins
from SprinklerDB import *
import SprinklerGlobals as globals

# Constants
VALVE_PIN = globals.VALVE_PIN

# Operates the valve directly by changing the state of the GPIO pin
# Saves the latest state of the Valve in the DB
class ValveSwitch(object):

    def __init__(self):
        self.state = pins.LOW
        pins.setup(VALVE_PIN, pins.OUT)
        print "Valve Switch is up and running"
        self.sync()

    def open(self):
        con = get_connection()
        try:
            con.begin()
            cursor = con.cursor()
            sql = "insert into Valve (state) Values (1);"
            inserted = cursor.execute(sql)
            print "%d row(s) inserted" % inserted
            con.commit()
            pins.output(VALVE_PIN, pins.HIGH)
            self.state = pins.HIGH
            print "Valve has been opened"
        except Exception as ex:
            "Failed to open Valve:\n%s" % ex
        finally:
            con.close()

    def close(self, force=False):
        con = get_connection()
        try:
            con.begin()
            cursor = con.cursor()
            sql = "insert into Valve (state) Values (0);"
            inserted = cursor.execute(sql)
            print "%d row(s) inserted" % inserted
            con.commit()
            pins.output(VALVE_PIN, pins.LOW)
            self.state = pins.LOW
            print "Valve has been closed"
        except Exception as ex:
            "Failed to close Valve:\n%s" % ex
        finally:
            con.close()

    def sync(self):
        con = get_connection()
        try:
            cursor = con.cursor()
            sql = "select state from Valve where id = (select max(id) from Valve);"
            cursor.execute(sql)
            state = cursor.fetchone()
            print "Valve state from DB: %d" % state
            self.close() if state is None or state == 0 else self.open()
        except Exception as ex:
            print "Failed to sync Valve State with DB:\n%s" % ex
        finally:
            close_connection(con)

    def toggle(self):
        if self.state is pins.LOW:
            self.open()
        else:
            self.close()


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
