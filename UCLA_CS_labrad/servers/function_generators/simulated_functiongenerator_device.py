"""
### BEGIN SIMULATED GPIB DEVICE INFO
[info]
name = SimulatedFunctionGeneratorDevice
version = 1.0
description = Blah
### END SIMULATED GPIB DEVICE INFO
"""

from UCLA_CS_labrad.servers.serial.hardware_simulating_server import GPIBSerialDevice
from labrad.errors import Error

#frequency,amplitude,toggle
class SimulatedFunctionGeneratorDeviceDevice(GPIBSerialDevice):


    
    def __init__(self):
        super().__init__()
        self.frequency=1
        self.amplitude=100
        self.generator_on=False
        self.command_dict={

        ("OUTPut",1,True)           : self.toggle,
        ("FREQuency",1, True)        : self.frequency 
        ("VOLTage",1,True)        : self.amplitude
		
		}
		
#query case??
    def toggle(self,channel):
        channel=int(channel)
        if (1<= channel <= 4):
            return str(int(self.channel_on[channel-1]))
            
                    
