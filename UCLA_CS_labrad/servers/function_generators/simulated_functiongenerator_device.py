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
class SimulatedAgilent33210ADevice(GPIBSerialDevice):

    
    def __init__(self):
        super().__init__()
        self.frequency=1.0
        self.amplitude=100.0
        self.generator_on=False
        self.command_dict={

        ("OUTPut",1,True)           : self.toggle,
        ("FREQuency",1, True)        : self.frequency,
        ("VOLTage",1,True)        : self.amplitude
		
		}
		

    def toggle(self,status=None):
        if status:
			if status=='ON':
		       self.generator_on=True
		    elif status=='OFF':
			   self.generator_on=False
		else:
		    if self.generator_on:
		       return "ON"
		    else:
		       return "OFF"
		

    def frequency(self,freq=None):
        if freq:
		    self.frequency=float(freq)
		else:
		    return str(self.frequency)
			
    def amplitude(self,amp=None):
        if amp:
		    self.amplitude=float(amp)
		else:
		    return str(self.amplitude)
		    
				
			
		    
		    
            
                    
