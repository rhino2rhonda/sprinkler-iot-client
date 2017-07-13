import RPi.GPIO as pins
import sys

INPUT_PIN=38
CALIB_FACTOR=365 # pulses/Litre

MODE="calib" #calib/test
if len(sys.argv) > 1:
    MODE = sys.argv[1]

flow_pulse_counter=0
def record_pulse(pin_no):
    global flow_pulse_counter
    flow_pulse_counter+=1

pins.setmode(pins.BOARD)
pins.setup(INPUT_PIN, pins.IN, pull_up_down=pins.PUD_DOWN)
pins.add_event_detect(INPUT_PIN, pins.RISING, callback=record_pulse)

calib_config = []
if MODE == "calib":
    calib_config += ["1 Litre"] * 5
    calib_config += ["10 Litres"] * 3
elif MODE == "test":
    calib_config += ["1 Litre"] * 4
else:
    print "Invalid mode %s" % MODE
    sys.exit(1)

print "********Flow Sensor Caliberation************\n\n"

for i,calib in enumerate(calib_config):

    if MODE == "calib":
        print "\n\nCaliberation %d of %d\n" % (i+1, len(calib_config))
        raw_input("Press ENTER to start measuring %s" % calib)
        flow_pulse_counter=0
        raw_input("Press ENTER to stop measuring")
        num_pulses = flow_pulse_counter
        with open('flow-calib-results', 'a') as fp:
            fp.write("%s,%d\n" % (calib, num_pulses))
        print "Measured %s. Num pulses: %d" % (calib, num_pulses)
    
    elif MODE == "test":
        print "\n\nTest %d of %d\n" % (i+1, len(calib_config))
        raw_input("Press ENTER to start measuring %s" % calib)
        flow_pulse_counter=0
        raw_input("Press ENTER to stop measuring")
        num_pulses = flow_pulse_counter
        litres = float(num_pulses)/CALIB_FACTOR
        with open('flow-calib-tests', 'a') as fp:
            fp.write("%s,%f\n" % (calib, litres))
        print "Measured %.2f L. Num pulses: %d" % (litres, num_pulses)

pins.cleanup()

print "************DONE*************"
