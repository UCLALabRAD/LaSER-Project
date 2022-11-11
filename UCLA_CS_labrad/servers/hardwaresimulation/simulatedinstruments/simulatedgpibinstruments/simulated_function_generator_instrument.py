
from ..simulated_instruments import SimulatedGPIBInstrument, SimulatedInstrumentError
from UCLA_CS_labrad.servers.hardwaresimulation import   SimulatedFunctionGeneratorOutputSignal

__all__=["SimulatedFunctionGeneratorInstrument","SimulatedFunctionGeneratorError"]

class SimulatedFunctionGeneratorError(SimulatedInstrumentError):
    user_defined_errors={}

class SimulatedFunctionGeneratorInstrument(SimulatedGPIBInstrument):
    name=None
    version=None
    description=None
    id_string=None

        
    def __init__(self):
        self.channels=[]
        for i in range(1):
            self.channels.append(SimulatedFunctionGeneratorOutputSignal())
        self.set_default_settings()
        
    def set_default_settings(self):
        for chan in self.channels:
             chan.outputting=False
             chan.frequency=1.0
             chan.amplitude=1.0
             chan.function="SIN"
             chan.offset=0.0
             
        
        
    def toggle(self,status=None):
        if status:
            if status=='ON' or (status.isnumeric() and int(status)==1):
               self.channels[0].outputting=True
            elif status=='OFF' or (status.isnumeric() and int(status)==0):
               self.channels[0].outputting=False
        else:
            return str(int(self.channels[0].outputting))
        

    def frequency(self,freq=None):
        if freq:
            self.channels[0].frequency=float(freq)
        else:
            return str(self.channels[0].frequency)
            
    def amplitude(self,amp=None):
        if amp:
            self.channels[0].amplitude=float(amp)
        else:
            return str(self.channels[0].amplitude)
            
    def offset(self,offs=None):
        if offs:
            self.channels[0].offset=float(offs)
        else:
            return str(self.channels[0].offset)
        
            
    def function(self,func=None):
        if func:
            self.channels[0].function=func
        else:
            return self.channels[0].function

    
            
            
            
            
                    
