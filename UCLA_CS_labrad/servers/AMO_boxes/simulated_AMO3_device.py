
from UCLA_CS_labrad.servers.hardwaresimulation.hardware_simulating_server import SerialDeviceModel
from labrad.errors import Error

from UCLA_CS_labrad.servers.hardwaresimulation.simulated_cables import SimulatedPiezoPMTSignal

__all__=['SimulatedPiezoDevice']

class SimulatedPiezoDevice(SerialDeviceModel):

    name= 'AMO3'
    version = '1.0'
    description='test piezo'
    
    def __init__(self):
        super().__init__()
        
        self.required_baudrate=38400
        self.required_bytesize=None
        self.required_parity=None
        self.required_stopbits=None
        self.required_rts=None
        self.required_dtr=None
        self.voltages=[0.0]*4
        self.channels=[]
        for i in range(2):
            self.channels.append(SimulatedPiezoPMTSignal(self,i+1))
        self.remote_status=True
        self.command_dict={
        ("remote.r",1)           : None,
        ("remote.w",2)        : None,
        ("out.r",1)    : self.get_channel_status,
        ("out.w",2)    : self.set_channel_status,
        ("vout.r",1)   : self.get_channel_voltage,
        ("vout.w",2)  : self.set_channel_voltage }

        
    max_voltage=150.0

    def get_channel_status(self,channel):
        channel=int(channel)
        if (1<= channel <= 4):
            return str(int(self.channels[channel-1].outputting))
            
                    
                        
    def set_channel_status(self,channel,status):
        channel=int(channel)
        status=int(status)
        if (1<= channel <= 4):
            channel=int(channel)
            if status==0:
                self.channels[channel-1].outputting=False
                return "out.w : output {} disabled\n".format(channel)
            elif status==1:
                self.channels[channel-1].outputting=True
                return "out.w : output {} enabled\n".format(channel)
            
                    
                        
                        

    def get_channel_voltage(self,channel):
        channel=int(channel)
        current_voltage=None
        if (1<= channel <= 4):
                current_voltage=self.voltages[channel-1]
        return "{:.2f}\n".format(current_voltage)
                
                
    def set_channel_voltage(self,channel,voltage):
        channel=int(channel)
        voltage=float(voltage)
        if voltage>self.max_voltage:
            voltage=self.max_voltage
        elif voltage<0:
            voltage=0
        if (1<= channel <= 4):
            self.voltages[channel-1]=voltage

        return "vout.w : set output {} to {:.3f}\n".format(channel,voltage)
		
