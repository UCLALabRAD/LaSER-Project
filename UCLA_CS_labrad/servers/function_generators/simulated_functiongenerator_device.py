
from UCLA_CS_labrad.servers.hardwaresimulation.sim_instr_models import GPIBDeviceModel
from labrad.errors import Error

#frequency,amplitude,toggle
class SimulatedAgilent33210ADevice(GPIBDeviceModel):
    name= 'Agilent33210A'
    version = '1.0'
    description='test function generator'
    def __init__(self):
        super().__init__()
        self.stored_frequency=1000.0
        self.stored_amplitude=.1
        self.generator_on=False
        self.supports_command_chaining=True
        self.id_string='Agilent Technologies,33210A,MY48007979,1.04-1.04-22-2'
        self.command_dict={

        ("OUTPut",1,True)           : self.toggle,
        ("FREQuency",1, True)        : self.frequency,
        ("VOLTage",1,True)        : self.amplitude }
        

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
            
                
            
            
            
            
                    
