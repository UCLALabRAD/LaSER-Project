
from ..simulated_instruments import SimulatedSerialInstrument, SimulatedInstrumentError

from UCLA_CS_labrad.servers.hardwaresimulation import SimulatedPiezoPMTOutputSignal

__all__=['SimulatedPiezoInstrument','SimulatedPiezoError']
class SimulatedPiezoError(SimulatedInstrumentError):
    user_defined_errors={}

class SimulatedPiezoInstrument(SimulatedSerialInstrument):
    name= None
    version = None
    description= None
    
    required_baudrate=None
    required_bytesize=None
    required_parity=None
    required_stopbits=None
    required_rts=None
    required_dtr=None
    
    voltage_range=None
    
    set_voltage_string=None
    set_toggle_on_string=None
    set_toggle_off_string=None

    
    def __init__(self):
        super().__init__()
        self.channels=[]
        for i in range(4):
            self.channels.append(SimulatedPiezoPMTOutputSignal())
        self.set_default_settings()
        
    def generate_constant_signal_func(self,voltage):
        return (lambda times: np.full(len(times),voltage))

    def set_default_settings(self):
        pass

    
    
        
    

    def get_channel_status(self,channel):
        channel=self.enforce_type_and_range(channel,(int,(1,4)),"channel")
        return (str(int(self.channels[channel-1].outputting)))

                    
                        
    def set_channel_status(self,channel,status):
        channel=self.enforce_type_and_range(channel,(int,(1,4)),"channel")
        status=self.enforce_type_and_range(status,(int,(0,1)),"status")
        self.channels[channel-1].outputting=bool(status)
        if status==0:
            return self.set_toggle_off_string.format(channel)
        elif status==1:
            return self.set_toggle_on_string.format(channel)
                        
                        

    def get_channel_voltage(self,channel):
        channel=self.enforce_type_and_range(channel,(int,(1,4)),"channel")
        current_voltage=self.channels[channel-1].voltage
        return "{:.2f}".format(current_voltage)
                
                
    def set_channel_voltage(self,channel,voltage):
        channel=self.enforce_type_and_range(channel,(int,(1,4)),"channel")
        
        voltage=self.enforce_type_and_range(voltage,(float,self.calculate_voltage_range()),"voltage")
        self.channels[channel-1].voltage=voltage

        return self.set_voltage_string.format(channel,voltage)
        
    def calculate_voltage_range(self):
        return self.voltage_range
