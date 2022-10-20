
from UCLA_CS_labrad.servers.hardwaresimulation.sim_instr_models import GPIBDeviceModel
from labrad.errors import Error

#frequency,amplitude,toggle
class SimulatedSomethingDevice(GPIBDeviceModel):
    name= 'Something'
    version = '1.0'
    description='Oscilloscope'
  
    def __init__(self):
        super().__init__()
        self.supports_command_chaining=True
        self.id_string='Agilent Technologies,33210A,MY48007979,1.04-1.04-22-2'
        self.command_dict={ }
        self.measurement_displays=([],[],[],[])
        self.channels=[]
        for i in range(4):
            self.channels.append(SimulatedInConn())

    def start_measuring(display_section,channel,measurement):
        self.measurement_displays[display_section].extend([channel,measurement,0.0])
        
    def calculate_mean(self,channel):
        for i in range(
    
        

    
    
            
            
            
            
                    
