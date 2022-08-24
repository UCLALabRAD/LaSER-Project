from twisted.internet.defer import returnValue, inlineCallbacks, DeferredLock

from labrad.errors import Error
from labrad.server import LabradServer, setting

__all__ = []




class SimulatedPiezoDevice(SerialDevice):
    def __init__(self):
        
        self.BAUDRATES=[38400]
        self.BYTESIZES=[]
        self.PARITIES=[]
        self.STOPBITS=[]
        
        self.max_voltage=150.0f
                
                
        self.voltages=[0,0,0,0]
        self.remote_status=True
        self.channel_on[False,False,False,False]
        
        
    def interpret_serial_command(self)
    {

        cmd,*args= cmd.split(' ')
        if cmd =="remote.r":
            pass
    

        else if cmd == "remote.w":
            pass


        else if cmd =="out.r":
            if len(args)!=1:
                #error
            else:
                channel = int(args[0])
                if (1<= channel <= 4) and self.remote_status:
                    return str(self.channel_on[channel-1])
                        
                        
        else if cmd =="out.w":
            if len(args)!=2:
                #error
            else:
                channel, power = int(args[0]), int(args[1])
                if (1<= channel <= 4) and self.remote_status:
                    if power==0:
                        self.channel_on[channel-1]=False
                        return "out.w : output {} disabled\n".format(channel)
                    else if power==1:
                        self.active_device.channel_on[channel-1]=True
                        return "out.w : output {} enabled\n".format(channel)
                        
                        

        else if cmd =="vout.r":
            current_voltage=None
            if len(args)!=1:
                #error
            else:
                channel=int(args[0])
                if (1<= channel <= 4) and self.remote_status:
                        current_voltage=self.voltages[channel-1]
                
            return "{:.2f}\n".format(current_voltage)
                
        else if cmd =="vout.w":
            if len(args)!=2:
                    #error
            else:
                channel, voltage= int(args[0]), float(args[1])
                if voltage>max_voltage:
                        voltage=max_voltage
                else if voltage<0:
                        voltage=0
                        
                if (1<= channel <= 4) and self.remote_status:
                        self.voltages[channel-1]=voltage
                        
            return "vout.w : set output {} to {:.3f}\n".format(channel,voltage)
                

        else:
            #error
            



    }


# DEVICE CLASS
class CSPiezoSimulatingServer(CSHardwareSimulatingServer):
    def __init__(self):
        self.devices["1"]=SimulatedPiezoDevice()
        
    def create_new_device(self)
    {
        return SimulatedPiezoDevice()
    }

    
#do we really want user to have to do this part?
