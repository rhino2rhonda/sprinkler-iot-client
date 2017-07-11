from SprinklerCLI import CommandLineController as controller
import SprinklerGlobals
import sys
import pickle
import zmq

def process_args():
    args = sys.argv
    args_pickled = pickle.dumps(args)
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect("tcp://localhost:%d" % SprinklerGlobals.CLI_SERVER_PORT)
    socket.send(args_pickled)
    resp_pickled = socket.recv()
    resp = pickle.loads(resp_pickled)
    print "Resp :", resp

if __name__ == "__main__":
    process_args()
