# Dummy module to emulate raspberry pi driver

HIGH=1
LOW=0
IN=10
OUT=11
BOARD=100

def setmode(x):
    pass

def getmode():
    return BOARD

def setup(x,y,z=None):
    pass

def input(x):
    pass

def output(x, y):
    pass

def cleanup():
    pass
