from SprinklerAPI import CommonSprinklerAPI as api
from ValveControl import ValveController
import SprinklerUtils as utils
import SprinklerGlobals
from threading import Thread
import pickle
import os
import zmq
import time

# Provides access to the valve through the command line
class CommandLineController(ValveController):

    def __init__(self, switch, api):
        ValveController.__init__(self, switch)
        self.api = api 
        self.name = "CommandLineController"
        self.server_up = True
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind("tcp://*:%d" % SprinklerGlobals.CLI_SERVER_PORT)
        self.server_thread = Thread(target=self.start_server)
        self.server_thread.start()
        print "Command Line Controller has been initialized"

    def start_server(self):
        while self.server_up:
            print "Waiting for client request"
            args_pickled = self.socket.recv()
            args = pickle.loads(args_pickled)
            print "Request : %s" % str(args)
            resp = self.generate_response(args)
            print "Response : %s" % resp
            resp_pickled = pickle.dumps(resp)
            self.socket.send(resp_pickled)
            print "Request completed"
            time.sleep(5)

    def stop_server(self):
        args = ['', 'stop_server']
        args_pickled = pickle.dumps(args)
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.connect("tcp://localhost:%d" % SprinklerGlobals.CLI_SERVER_PORT)
        socket.send(args_pickled)
        resp_pickled = socket.recv()
        resp = pickle.loads(resp_pickled)
        return resp

    def generate_response(self, args):
        if type(args) is not list:
            return "Message received cannot be processed as it is not a list"
        if len(args) <= 1:
            return "No arguments to process"
        command = args[1]
        if command == "start" and len(args) == 2:
            self.api.start_sprinkler(self)
            return "Request has been submitted"
        elif command == "stop":
            if len(args) == 2:
                self.api.stop_sprinkler(self)
                return "Request has been submitted"
            elif args[2] == "force" and len(args) == 3:
                self.api.stop_sprinkler(self, True)
                return "Request has been submitted"
        elif command == "is_sprinkler_started" and len(args) == 2:
            return self.api.is_sprinkler_started()
        elif command == "is_controller_started" and len(args) == 2:
            return self.api.is_controller_started(self)
        elif command == "stop_server" and len(args) == 2:
            self.server_up = False
            return True
        else:
            # todo timer config
            return "Invalid arguments %s. Failed to process" % str(args)
