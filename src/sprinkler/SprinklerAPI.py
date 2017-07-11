import RPi.GPIO as pins

class CommonSprinklerAPI(object):

    def __init__(self, switch):
        self.switch = switch

    def get_controller(self, name):
        return self.switch.controllers[name] if name in self.switch.controllers.keys() else None

    def start_sprinkler(self, controller):
        controller.open_valve()

    def stop_sprinkler(self, controller, force = False):
        controller.close_valve(force)

    def is_sprinkler_started(self):
        return self.switch.state == pins.HIGH

    def is_controller_started(self, controller):
        return controller.state == pins.HIGH

    def configure_timer():
        pass
