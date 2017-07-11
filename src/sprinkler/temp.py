from PinsControl import PinsController as PC
from ValveControl import ValveMultiSwitch as VMS
from SprinklerAPI import CommonSprinklerAPI as CAPI
from SprinklerCLI import CommandLineController as CLI

pc = PC()
switch = VMS()
api = CAPI(switch)
controller = CLI(switch, api)
switch.register_controller(controller)
