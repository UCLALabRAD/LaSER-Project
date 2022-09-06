"""
### BEGIN NODE INFO
[info]
name = CS Piezo Simulating Server
version = 1.1
description = Gives access to serial devices via pyserial.
instancename = %LABRADNODE% CS Piezo Simulating Server

[startup]
cmdline = %PYTHON% %FILE%
timeout = 20

[shutdown]
message = 987654321
timeout = 20
### END NODE INFO
"""


from twisted.internet.defer import returnValue, inlineCallbacks, DeferredLock


from labrad.server import LabradServer, setting

from UCLA_CS_labrad.servers.serial.hardwareSimulatingServer import *

__all__ = ['SimulatedPiezoDevice','CSPiezoSimulatingServer']


class SimulatedPiezoDevice(SerialDevice):

    max_voltage=150.0

    def __init__(self):
        super().__init__()
        self.required_baudrate=1
        self.required_bytesize=2
        self.required_parity=3
        self.required_stopbits=4
        self.required_rts=True
        self.required_dtr=False
        
        
                
                
        self.voltages=[0,0,0,0]
        self.remote_status=True
        self.channel_on=[False,False,False,False]
        
    def log_and_return(resp):
        print("Device returned: "+resp +".")
        return resp
        
    def interpret_serial_command(self,cmd ):
        cmd,*args= cmd.split(' ')
        print("Device received command "+cmd)
        if cmd =="remote.r":
            return None
    

        elif cmd == "remote.w":
            return None
        
        elif cmd =="out.r":
            channel = int(args[0])
            if (1<= channel <= 4):
                return self.log_and_return(str(int(self.channel_on[channel-1])))

                    
                        
        elif cmd =="out.w":
            channel, power = int(args[0]), int(args[1])
            if (1<= channel <= 4):
                if power==0:
                    self.channel_on[channel-1]=False
                    return self.log_and_return("out.w : output {} disabled\n".format(channel))
                elif power==1:
                    self.channel_on[channel-1]=True
                    return self.log_and_return("out.w : output {} enabled\n".format(channel))
            
                    
                        
                        

        elif cmd =="vout.r":
            current_voltage=None
            channel=int(args[0])
            if (1<= channel <= 4):
                    current_voltage=self.voltages[channel-1]
            return self.log_and_return("{:.2f}\n".format(current_voltage))
                
                
        elif cmd =="vout.w":
            channel, voltage= int(args[0]), float(args[1])
            if voltage>self.max_voltage:
                voltage=self.max_voltage
            elif voltage<0:
                voltage=0
                        
            if (1<= channel <= 4):
                self.voltages[channel-1]=voltage

            return self.log_and_return("vout.w : set output {} to {:.3f}\n".format(channel,voltage))



# DEVICE CLASS
class CSPiezoSimulatingServer(CSHardwareSimulatingServer):
    name = '%LABRADNODE% CS Piezo Simulating Server'
    def initServer(self):
        super().initServer()
        
    def create_new_device(self):
        return SimulatedPiezoDevice()

    
#do we really want user to have to do this part?

__server__ = CSPiezoSimulatingServer()

if __name__ == '__main__':
    from labrad import util
    util.runServer(__server__)
