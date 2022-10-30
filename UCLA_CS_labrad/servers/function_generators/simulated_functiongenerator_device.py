
from UCLA_CS_labrad.servers.hardwaresimulation.sim_instr_models import GPIBDeviceModel
from labrad.errors import Error

class SimulatedFunctionGenerator(GPIBDeviceModel):
    name=None
    version=None
    description=None
    id_string=None

        
    def __init__(self):
        super().__init__()
        self.channels=[]
        for i in range(2):
            self.channels.append(SimulatedFunctionGeneratorSignal(self,i))
        self.set_default_settings()
        
    def set_default_parameters(self):
        self.stored_frequency=1000.0
        self.stored_amplitude=.1
        self.generator_on=False
        
        
    def toggle(self,status=None):
        if status:
            if status=='ON' or (status.isnumeric() and int(status)==1):
               self.generator_on=True
            elif status=='OFF' or (status.isnumeric() and int(status)==0):
               self.generator_on=False
        else:
            return str(int(self.generator_on))
        

    def frequency(self,freq=None):
        if freq:
            self.stored_frequency=float(freq)
        else:
            return str(self.stored_frequency)
            
    def amplitude(self,amp=None):
        if amp:
            self.stored_amplitude=float(amp)
        else:
            return str(self.stored_amplitude)
            
                
        
#frequency,amplitude,toggle
class SimulatedAgilent33210A(SimulatedFunctionGenerator):
    name= 'Agilent33210A'
    version = '1.0'
    description='test function generator'
    
    id_string='Agilent Technologies,33210A,MY48007979,1.04-1.04-22-2'
    self.command_dict={

        ("OUTPut",1,True)           : self.toggle,
        ("FREQuency",1, True)        : self.frequency,
        ("VOLTage",1,True)        : self.amplitude }
    }
    
            
            
            
            
                    
