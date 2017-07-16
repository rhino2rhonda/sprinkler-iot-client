# Dummy module to emulate raspberry pi driver

HIGH=1
LOW=0

IN=11
OUT=10

BOARD=20

PUD_UP=31
PUD_DOWN=30

RISING=41
FALLING = 40

def setmode(x):
    pass

def getmode():
    return BOARD

def setup(x,y,pull_up_down=None):
    pass

def input(x):
    pass

def output(x, y):
    pass

def cleanup():
    pass

def add_event_detect(x,y,callback=None):
    pass
