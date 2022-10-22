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
        self.id_string='Agilent Technologies,33210A,MY48007979,1.04-1.04-22-2'
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
        print(self.channels[0].incoming_voltage)
        return self.channels[0].incoming_voltage
    
    
    
        

    
    
            
            
            
            
                    
