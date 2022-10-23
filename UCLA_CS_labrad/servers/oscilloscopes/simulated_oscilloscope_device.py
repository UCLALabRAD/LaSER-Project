from UCLA_CS_labrad.servers.hardwaresimulation.sim_instr_models import GPIBDeviceModel

from UCLA_CS_labrad.servers.hardwaresimulation.simulated_cables import SimulatedInSignal
from labrad.errors import Error

#frequency,amplitude,toggle
class SimulatedKeysightDSOXADevice(GPIBDeviceModel):
    name= 'KeysightDSOX2024A'
    version = '1.0'
    description='Oscilloscope'
  
    def __init__(self):
        super().__init__()
        self.supports_command_chaining=True
        self.id_string='AGILENT TECHNOLOGIES,DSO-X 2024A,MY58104761,02.43.2018020635'
        self.command_dict={
        ("VOLTage",1,True) : self.get_voltage_test }
        #self.measurement_displays=([],[],[],[])
        self.channels=[]
        for i in range(4):
            self.channels.append(SimulatedInSignal())

  #  def start_measuring(display_section,channel,measurement):
   #     self.measurement_displays[display_section].extend([channel,measurement,0.0])
        
   # def calculate_mean(self,channel):
     #   for i in range(
    def get_voltage_test(self):
        return str(self.channels[0].incoming_voltage)
    
    
    
        

    
    
            
            
            
            
                    
