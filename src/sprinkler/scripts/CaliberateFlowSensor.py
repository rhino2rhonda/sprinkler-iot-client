import RPi.GPIO as pins
import time

INPUT_PIN=40
CALC_FREQ=10 #secs

flow_pulse_counter=0#1 pulse = 7.5 L
def yolo(pin_no):
    global flow_pulse_counter
    flow_pulse_counter+=1
    # print "Flow Pulse Detected: %d" % flow_pulse_counter


pins.setmode(pins.BOARD)
pins.setup(INPUT_PIN, pins.IN, pull_up_down=pins.PUD_DOWN)
pins.add_event_detect(INPUT_PIN, pins.RISING, callback=yolo)

curr_time = time.time()
counter = 0
while True:
    new_time = time.time()
    if(new_time - curr_time > CALC_FREQ):
        curr_time = new_time
        counter += 1
        #lph = float(flow_pulse_counter*360)/7.5
        #print "Flow is %.2f L/Hr. Counter was %d" % (lph, flow_pulse_counter)
        #flow_pulse_counter=0
        print "Time %d : Flow Counter %d" % (counter*10,flow_pulse_counter)
