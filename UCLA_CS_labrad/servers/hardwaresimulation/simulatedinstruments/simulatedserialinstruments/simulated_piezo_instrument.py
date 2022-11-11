
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
    
    max_voltage=None
    
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
        channel=int(channel)
        if (1<= channel <= 4):
            return (str(int(self.channels[channel-1].outputting)))
        else:
            #raise SimulatedPiezoError(5,[channel,"channel"])
            raise SimulatedPiezoError(8,[channel,"channel"])
                    
                        
    def set_channel_status(self,channel,status):
        channel=int(channel)
        status=int(status)
        
        if (1<= channel <= 4):
            if status==0:
                self.channels[channel-1].outputting=False
                return self.set_toggle_off_string.format(channel)
            elif status==1:
                self.channels[channel-1].outputting=True
                return self.set_toggle_on_string.format(channel)
            
                    
                        
                        

    def get_channel_voltage(self,channel):
        channel=int(channel)
        current_voltage=None
        if (1<= channel <= 4):
            current_voltage=self.channels[channel-1].voltage
        return "{:.2f}".format(current_voltage)
                
                
    def set_channel_voltage(self,channel,voltage):
        channel=int(channel)
        voltage=float(voltage)
        if voltage>self.max_voltage:
            voltage=self.max_voltage
        elif voltage<0:
            voltage=0
        if (1<= channel <= 4):
            self.channels[channel-1].voltage=voltage

        return self.set_voltage_string.format(channel,voltage)
