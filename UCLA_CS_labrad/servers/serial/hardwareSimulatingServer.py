from twisted.internet.defer import returnValue, inlineCallbacks, DeferredLock

from labrad.errors import Error
from labrad.server import LabradServer, setting

__all__ = []




class SerialDevice(object):
    def interpretSerialCommand(self,cmd)
    {
        pass
    }
    self.output_buffer=bytearray(b'')
    self.input_buffer=bytearray(b'')
    
# DEVICE CLASS
class CSHardwareSimulatingServer(LabradServer):

    def __init__(self):
        self.devices={}
        
    
    @setting(11, 'Write', data='s', returns='')
    def write(self,c,data)
    {
        active_device=c['Device ID']
        self.devices[active_device].input_buffer.extend(data)
        *cmds, rest=self.devices[active_device].input_buffer.decode().split("\r\n")
        for cmd in cmds:
            command_interpretation=self.devices[active_device].interpret_serial_command(cmd)
            self.output_buffer.extend(command_interpretation.encode())
        self.devices[active_device].input_buffer=rest.encode()
        
    }
    
    
    @setting(12, 'Read', count='i', returns='s')
    def read(self,c,count)
    {
        active_device=c['Device ID']
        write_out,rest=self.devices[active_device].output_buffer.decode()[:count],self.devices[active_device].output_buffer.decode()[count:]
        self.devices[active_device].output_buffer=rest.encode()
        return write_out.encode()
    }

    
    def createNewDevice(self)
    {
        pass
    }
    
    
    @setting(31, 'Add Simulated Device', device_id='s', returns='')
    def add_device(self, c, device_id)
    {
        self.devices[device_id]=self.create_new_device() #better way to do this?
    }

    @setting(32, 'Remove Simulated Device', device_id='i', returns='')
    def remove_device(self,c, device_id)
    {
        del self.devices[device_id]
    }
    
    @setting(41, 'Get In-Waiting', returns='i')
    def get_in_waiting(self,c)
    {
        active_device=c['Device ID']
        return len(self.devices[active_device].output_buffer)
    }
    
    @setting(42, 'Get Out-Waiting', returns='i')
    def get_out_waiting(self,c)
    {
        active_device=c['Device ID']
        return len(self.devices[active_device].input_buffer)
    }
    
    @setting(51, 'Reset Input Buffer', returns='')
    def reset_input_buffer(self,c)
    {
        active_device=c['Device ID']
        self.devices[active_device].output_buffer=bytearray(b'')
    }
    
    @setting(52, 'Reset Output Buffer', returns='')
    def reset_output_buffer(self,c)
    {
        active_device=c['Device ID']
        self.devices[active_device].input_buffer=bytearray(b'')
    }



