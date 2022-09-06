
from twisted.internet.defer import returnValue, inlineCallbacks, DeferredLock

from labrad.errors import Error
from labrad.server import LabradServer, Signal, setting


__all__ = ['SerialDevice','CSHardwareSimulatingServer','SimulatedDeviceError']

class HSSError(Exception):
    errorDict ={0: 'Port in Use',1: 'No device at port'}

    def __init__(self, code):
        self.code = code

    def __str__(self):
        if self.code in self.errorDict:
            return self.errorDict[self.code]
            
class SimulatedDeviceError(Exception):
    errorDict ={0: 'Unsupported Value for Serial Connection Parameter'}

    def __init__(self, code):
        self.code = code

    def __str__(self):
        if self.code in self.errorDict:
            return self.errorDict[self.code]
            

class SerialDevice(object):

    required_baudrate=None
    required_bytesize=None
    required_parity=None
    required_stopbits=None
    required_dtr=None
    required_rst=None
    
    actual_baudrate=None
    actual_bytesize=None
    actual_parity=None
    actual_stopbits=None
    actual_dtr=None
    actual_rst=None
        
    def interpretSerialCommand(self,cmd):
        pass
        
        
    def __init__(self):
        self.output_buffer=bytearray(b'')
        self.input_buffer=bytearray(b'')
        
    
# DEVICE CLASS
class CSHardwareSimulatingServer(LabradServer):
    
    device_added=Signal(565656,'Signal: Simulated Device Added','(s,s)')
    device_removed=Signal(676767,'Signal: Simulated Device Removed','s')
    def initServer(self):
        super().initServer()
        self.devices={}
        
  
    @setting(11, 'Read', count='i', returns='s')
    def read(self,c,count):
        if 'Port' not in c or c['Port'] not in self.devices:
            raise HSSError(1)
        active_device=self.devices[c['Port']]
        write_out,rest=active_device.input_buffer[:count],active_device.input_buffer[count:]
        active_device.input_buffer=rest
        return write_out.decode()

    
    @setting(12, 'Write', data='s', returns='')
    def write(self,c,data):
        if 'Port' not in c or c['Port'] not in self.devices:
            raise HSSError(1)
        active_device=self.devices[c['Port']]
        active_device.output_buffer.extend(data.encode())
        *cmds, rest=active_device.output_buffer.decode().split("\r\n")
        for cmd in cmds:
            try:
                command_interpretation=active_device.interpret_serial_command(cmd)
                active_device.input_buffer.extend(command_interpretation.encode())
            except SimulatedDeviceError as e:
                raise e
            except:
                raise Exception('Error with interpret_serial_command implementation: Every command should either result in a SimulatedDeviceError or a returned string.')
            
            
            
            
                
        active_device.output_buffer=bytearray(rest.encode())
    

    
    def createNewDevice(self):
        pass
    
    
    @setting(31, 'Add Simulated Device', port='s', returns='')
    def add_device(self, c, port):
        if port in self.devices:
            raise HSSError(0)
        self.devices[port]=self.create_new_device() #better way to do this?
        self.device_added((self.name,port))
        
        
    @setting(32, 'Remove Simulated Device', port='s', returns='')
    def remove_device(self,c, port):
        if port in self.devices:
            del self.devices[port]
        else:
            raise HSSError(1)
        self.device_removed(port)
    
    @setting(41, 'Get In-Waiting', returns='i')
    def get_in_waiting(self,c):
        if 'Port' not in c or c['Port'] not in self.devices:
            raise HSSError(1)
        active_device=self.devices[c['Port']]
        return len(active_device.input_buffer)
    
    @setting(42, 'Get Out-Waiting', returns='i')
    def get_out_waiting(self,c):
        if 'Port' not in c or c['Port'] not in self.devices:
            raise HSSError(1)
        active_device=self.devices[c['Port']]
        return len(active_device.output_buffer)
    
    
    @setting(51, 'Reset Input Buffer', returns='')
    def reset_input_buffer(self,c):
        if 'Port' not in c or c['Port'] not in self.devices:
            raise HSSError(1)
        active_device=self.devices[c['Port']]
        active_device.input_buffer=bytearray(b'')
    
    @setting(52, 'Reset Output Buffer', returns='')
    def reset_output_buffer(self,c):
        if 'Port' not in c or c['Port'] not in self.devices:
            raise HSSError(1)
        active_device=self.devices[c['Port']]
        active_device.output_buffer=bytearray(b'')

    @setting(61, 'Select Device', port='s', returns='')
    def select_device(self,c,port):
        if 'Port' in c:
            del c['Port']
        if port not in self.devices:
            raise HSSError(1)
        c['Port']=port

    @setting(71, 'Baudrate', val=[': Query current baudrate', 'w: Set baudrate'], returns='w: Selected baudrate')
    def baudrate(self,c,val):
        if 'Port' not in c or c['Port'] not in self.devices:
            raise HSSError(1)
        active_device=self.devices[c['Port']]
        if val:
            if val!=active_device.required_baudrate:
                raise SimulatedDeviceError(0)
            else:
                active_device.actual_baudrate=val
        return active_device.actual_baudrate
        
    @setting(72, 'Bytesize',val=[': Query current stopbits', 'w: Set bytesize'], returns='w: Selected bytesize')
    def bytesize(self,c,val):
        if 'Port' not in c or c['Port'] not in self.devices:
            raise HSSError(1)
        active_device=self.devices[c['Port']]
        if val:
            if val!=active_device.required_bytesize:
                raise SimulatedDeviceError(0)
            else:
                active_device.actual_bytesize=val
        return active_device.actual_bytesize
        
    @setting(73, 'Parity', val=[': Query current parity', 'w: Set parity'], returns='w: Selected parity')
    def parity(self,c,val):
        if 'Port' not in c or c['Port'] not in self.devices:
            raise HSSError(1)
        active_device=self.devices[c['Port']]
        if val:
            if val!=active_device.required_parity:
                raise SimulatedDeviceError(0)
            else:
                active_device.actual_parity=val
        return active_device.actual_parity
        
    @setting(74, 'Stopbits', val=[': Query current stopbits', 'w: Set stopbits'], returns='w: Selected stopbits')
    def stopbits(self,c,val):
        if 'Port' not in c or c['Port'] not in self.devices:
            raise HSSError(1)
        active_device=self.devices[c['Port']]
        if val:
            if val!=active_device.required_stopbits:
                raise SimulatedDeviceError(0)
            else:
                active_device.actual_stopbits=val
        return active_device.actual_stopbits
        
    @setting(75, 'RTS', val='b', returns='b')
    def rts(self,c,val):
        if 'Port' not in c or c['Port'] not in self.devices:
            raise HSSError(1)
        active_device=self.devices[c['Port']]
 
        if val!=active_device.required_rts:
            raise SimulatedDeviceError(0)
        else:
            active_device.actual_rts=val
        return active_device.actual_rts
        
    @setting(76, 'DTR', val='b', returns='b')
    def dtr(self,c,val):
        if 'Port' not in c or c['Port'] not in self.devices:
            raise HSSError(1)
        active_device=self.devices[c['Port']]
 
        if val!=active_device.required_dtr:
            raise SimulatedDeviceError(0)
        else:
            active_device.actual_dtr=val
        return active_device.actual_dtr
        
        
    @setting(81, 'Buffer Size', returns='')
    def buffer_size(self,c):
        return 0
        
    @setting(91, 'Get Devices List',returns='*s')
    def get_devices_list(self,c):
        return list(self.devices.keys())

  

