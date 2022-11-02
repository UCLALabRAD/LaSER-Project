
from UCLA_CS_labrad.servers.hardwaresimulation.hardware_simulating_server import SerialDeviceModel
from labrad.errors import Error

from UCLA_CS_labrad.servers.hardwaresimulation.simulated_cables import SimulatedPiezoPMTSignal

__all__=['SimulatedAMO3']


class SimulatedPiezo(SerialDeviceModel):
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
            self.channels.append(SimulatedPiezoPMTSignal())
        self.set_default_settings()
        
    def generate_constant_signal_func(self,voltage):
        return (lambda times: np.full(len(times),voltage))

    def set_default_settings(self):
        pass

    
    
        
    

    def get_channel_status(self,channel):
        channel=int(channel)
        if (1<= channel <= 4):
            return (str(int(self.channels[channel-1].outputting)))
            
                    
                        
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
		
class SimulatedAMO3(SimulatedPiezo):
    name= 'AMO3'
    version = '1.0'
    description='test piezo'
    
    required_baudrate=38400
    
    max_voltage=150.0
    set_voltage_string="vout.w : set output {} to {:.3f}"
    set_toggle_on_string="out.w : output {} enabled"
    set_toggle_off_string="out.w : output {} disabled"
    
    command_dict={
        (b'remote.r',1)           : None,
        (b'remote.w',2)        : None,
        (b'out.r',1)    : SimulatedPiezo.get_channel_status,
        (b'out.w',2)    : SimulatedPiezo.set_channel_status,
        (b'vout.r',1)   : SimulatedPiezo.get_channel_voltage,
        (b'vout.w',2)  : SimulatedPiezo.set_channel_voltage }
