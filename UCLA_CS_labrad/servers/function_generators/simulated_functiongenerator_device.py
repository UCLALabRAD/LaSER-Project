
from UCLA_CS_labrad.servers.hardwaresimulation.sim_instr_models import GPIBDeviceModel
from UCLA_CS_labrad.servers.hardwaresimulation.simulated_cables import SimulatedFunctionGeneratorSignal
from labrad.errors import Error

class SimulatedFunctionGenerator(GPIBDeviceModel):
    name=None
    version=None
    description=None
    id_string=None

        
    def __init__(self):
        self.channels=[]
        for i in range(1):
            self.channels.append(SimulatedFunctionGeneratorSignal())
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
            if status=='ON'.encode() or (status.decode().isnumeric() and int(status)==1):
               self.channels[0].outputting=True
            elif status=='OFF'.encode() or (status.decode().isnumeric() and int(status)==0):
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
            self.channels[0].function=func.decode()
        else:
            return self.channels[0].function
        
#frequency,amplitude,toggle
class SimulatedAgilent33210A(SimulatedFunctionGenerator):
    name= 'Agilent33210A'
    version = '1.0'
    description='test function generator'
    
    id_string='Agilent Technologies,33210A,MY48007979,1.04-1.04-22-2'
    command_dict={

        (b'OUTPut',1)           : SimulatedFunctionGenerator.toggle,
        (b'FREQuency',1)        : SimulatedFunctionGenerator.frequency,
        (b'VOLTage',1)        : SimulatedFunctionGenerator.amplitude,
        (b'FUNCtion',1)        : SimulatedFunctionGenerator.function,
        (b'VOLTage:OFFSet',1)        : SimulatedFunctionGenerator.offset,
        (b'OUTPut?',0)           : SimulatedFunctionGenerator.toggle,
        (b'FREQuency?',0)        : SimulatedFunctionGenerator.frequency,
        (b'VOLTage?',0)        : SimulatedFunctionGenerator.amplitude,
        (b'FUNCtion?',0)        : SimulatedFunctionGenerator.function,
        (b'VOLTage:OFFSet?',0)        : SimulatedFunctionGenerator.offset
    }
    
            
            
            
            
                    
