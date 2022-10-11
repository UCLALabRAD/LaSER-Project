"""
### BEGIN NODE INFO
[info]
name = CS Hardware Simulating Server
version = 1.1
description = Gives access to serial devices via pyserial.
instancename = CS Hardware Simulating Server

[startup]
cmdline = %PYTHON% %FILE%
timeout = 20

[shutdown]
message = 987654321
timeout = 20
### END NODE INFO
"""
from twisted.internet.defer import returnValue, inlineCallbacks, DeferredLock
import collections
from labrad.errors import Error
from labrad.server import LabradServer, Signal, setting

from importlib import reload, import_module
import UCLA_CS_labrad.config.hardwaresimulatingserver_config as hss_config

from UCLA_CS_labrad.servers.hardwaresimulation.sim_instr_models import GPIBDeviceModel, SerialDeviceModel

import os, sys


from labrad import auth, protocol, util, types as T, constants as C

STATUS_TYPE = '*(s{name} s{desc} s{ver})'

class HSSError(Exception):
    errorDict ={ 0:'Device already exists at specified node and port',1:'No device exists at specified node and port',2: 'Device type not supported.',3: 'No directories for Simulated Device files found in registry',4:'One or more simulated device info blocks were not successfully parsed in directory.', 5:'Unable to find class for desired device in module'}

    def __init__(self, code):
        self.code = code

    def __str__(self):
        if self.code in self.errorDict:
            return self.errorDict[self.code]
            
class SimulatedDeviceError(Exception):
    errorDict ={0:'Serial command not supported by device.', 1: 'Unsupported Value for Serial Connection Parameter'}

    def __init__(self, code):
        self.code = code

    def __str__(self):
        if self.code in self.errorDict:
            return self.errorDict[self.code]
            
SimInstrModel = collections.namedtuple('SimInstrModel', ['name','version','description','cls'])

        
# DEVICE CLASS
class CSHardwareSimulatingServer(LabradServer):
    name='CS Hardware Simulating Server'
    device_added=Signal(565656,'Signal: Device Added','(s,s)')
    device_removed=Signal(676767,'Signal: Device Removed','(s,s)')

    def initServer(self):
        super().initServer()
        self.devices={}
        self.sim_instr_models={}
        self.load_simulated_instrument_models()
        if not self.sim_instr_models:
            raise HSSError(4)

    def initContext(self,c):
        c['Device']=None
            
    
    def load_simulated_instrument_models(self):
        '''
        Loads simulated instrument classes from the configuration file.
        '''
        config = hss_config.config
        for import_path, class_name in config.sim_instr_models:
            try:
                # imports the file
                import_module(import_path)
                # gets the file
                module = sys.modules[import_path]
                
                # gets the experiment class from the module
                cls = getattr(module, class_name)
            except ImportError as e:
                print('Error importing simulated device model:', e)
            except AttributeError as e:
                print(e)
                print('There is no class {0} in module {1}'.format(class_name, module))
            except SyntaxError as e:
                print(e)
                print('Incorrect syntax in file {0}'.format(import_path, class_name))
            except Exception as e:
                print('There was an error in {0} : {1}'.format(class_name, e))
            else:
                try:
                    name = cls.name
                    version = cls.version
                    description = cls.description

                except AttributeError:
                    name_not_provided = 'Name is not provided for class {0} in module {1}'
                    print(name_not_provided.format(class_name, module))
                else:
                    self.sim_instr_models[name] = SimInstrModel(name,version,description,cls)
                    
    @setting(11, 'Serial Read', count='i', returns='s')
    def serial_read(self,c,count):
        if not c['Device']:
            raise HSSError(1)
        active_device=c['Device']
        write_out,rest=active_device.input_buffer[:count],active_device.input_buffer[count:]
        active_device.input_buffer=rest
        return write_out.decode()

    
    @setting(12, 'Serial Write', data='s', returns='')
    def serial_write(self,c,data):
        if not c['Device']:
            raise HSSError(1)
        active_device=c['Device']
        active_device.output_buffer.extend(data.encode())
        *cmds, rest=active_device.output_buffer.decode().split('\r\n')
        for cmd in cmds:
            command_interpretation=active_device.interpret_serial_command(cmd)
            active_device.input_buffer.extend(command_interpretation.encode())
                
        active_device.output_buffer=bytearray(rest.encode())
    
   
    @setting(13, 'GPIB Read', count='i', returns='s')
    def gpib_read(self,c,count=None):
        if not c['Device']:
            raise HSSError(1)
        active_device=c['Device']
        if not count:
           count=len(active_device.input_buffer)
        write_out,rest=active_device.input_buffer[:count],active_device.input_buffer[count:]
        active_device.input_buffer=rest
        return write_out.decode()

    @setting(14, 'GPIB Write', data='s', returns='')
    def gpib_write(self,c,data):
        if not c['Device']:
            raise HSSError(1)
        self.reset_input_buffer(c)
        if data=='*CLS':
            pass
        active_device=c['Device']
        invalid_command_entered=False
        if active_device.supports_command_chaining:
            cmds=data.split(';')
            for cmd in cmds:
               command_interpretation=active_device.interpret_serial_command(cmd)
               if command_interpretation or command_interpretation=="":
                   active_device.input_buffer.extend((command_interpretation+';').encode())
               else:
                   invalid_command_entered=True
                   break
        if active_device.input_buffer:
            active_device.input_buffer=active_device.input_buffer[:-1]
            if not invalid_command_entered:
                active_device.input_buffer.extend(active_device.termination_character)
            
        
    
    @setting(31, 'Add Device', node='s',port='s', instr_model='s',is_gpib='b',returns='')
    def add_device(self, c, node, port,instr_model,is_gpib):
        if (node,port) in self.devices:
            raise HSSError(0)
    
        if instr_model not in self.sim_instr_models or (issubclass(self.sim_instr_models[instr_model].cls,GPIBDeviceModel))!=is_gpib:
            raise HSSError(2)
        self.devices[(node,port)]=self.sim_instr_models[instr_model].cls()
        self.device_added((node,port))
        
        
        
        
    @setting(32, 'Remove Device', node='s', port='s', returns='')
    def remove_device(self,c, node, port):
        if (node,port) not in self.devices: 
            raise HSSError(1)
        
        for context_obj in self.contexts.values():
            if context_obj.data['Device'] is self.devices[(node,port)]:
                context_obj.data['Device']=None
                break
        del self.devices[(node,port)]
        
        self.device_removed((node,port))
    
    @setting(41, 'Get In-Waiting', returns='i')
    def get_in_waiting(self,c):
        if not c['Device']:
            raise HSSError(1)
        active_device=c['Device']
        return len(active_device.input_buffer)
    
    @setting(42, 'Get Out-Waiting', returns='i')
    def get_out_waiting(self,c):
        if not c['Device']:
            raise HSSError(1)
        active_device=c['Device']
        return len(active_device.output_buffer)
    
    
    @setting(51, 'Reset Input Buffer', returns='')
    def reset_input_buffer(self,c):
        if not c['Device']:
            raise HSSError(1)
        active_device=c['Device']
        active_device.input_buffer=bytearray(b'')
    
    @setting(52, 'Reset Output Buffer', returns='')
    def reset_output_buffer(self,c):
        if not c['Device']:
            raise HSSError(1)
        active_device=c['Device']
        active_device.output_buffer=bytearray(b'')

    @setting(61, 'Select Device', node='s', port='s', returns='')
    def select_device(self,c,node,port):
        c['Device']=self.devices[(node,port)]

      
    @setting(62, 'Deselect Device',returns='')
    def deselect_device(self,c,node):    
        c['Device']=None


    @setting(71, 'Baudrate', val=[': Query current baudrate', 'w: Set baudrate'], returns='w: Selected baudrate')
    def baudrate(self,c,val):
        active_device=c['Device']
        if val:
            if val!=active_device.required_baudrate:
                raise SimulatedDeviceError(1)
            else:
                active_device.actual_baudrate=val
        return active_device.actual_baudrate
        
    @setting(72, 'Bytesize',val=[': Query current stopbits', 'w: Set bytesize'], returns='w: Selected bytesize')
    def bytesize(self,c,val):
        active_device=c['Device']
        if val:
            if val!=active_device.required_bytesize:
                raise SimulatedDeviceError(1)
            else:
                active_device.actual_bytesize=val
        return active_device.actual_bytesize
        
    @setting(73, 'Parity', val=[': Query current parity', 'w: Set parity'], returns='w: Selected parity')
    def parity(self,c,val):
        active_device=c['Device']
        if val:
            if val!=active_device.required_parity:
                raise SimulatedDeviceError(1)
            else:
                active_device.actual_parity=val
        return active_device.actual_parity
        
    @setting(74, 'Stopbits', val=[': Query current stopbits', 'w: Set stopbits'], returns='w: Selected stopbits')
    def stopbits(self,c,val):
        active_device=c['Device']
        if val!=active_device.required_stopbits:
            raise SimulatedDeviceError(1)
        else:
            active_device.actual_stopbits=val
        return active_device.actual_stopbits
        
    @setting(75, 'RTS', val='b', returns='b')
    def rts(self,c,val):
        active_device=c['Device']
 
        if val!=active_device.required_rts:
            raise SimulatedDeviceError(1)
        else:
            active_device.actual_rts=val
        return active_device.actual_rts
        
    @setting(76, 'DTR', val='b', returns='b')
    def dtr(self,c,val):
        active_device=c['Device']
 
        if val!=active_device.required_dtr:
            raise SimulatedDeviceError(1)
        else:
            active_device.actual_dtr=val
        return active_device.actual_dtr
        
        
    @setting(81, 'Buffer Size', returns='')
    def buffer_size(self,c):
        if not c['Device']:
            raise HSSError(1)
        return 0
        
      
    @setting(92, 'Get Device Types',returns='s')
    def available_device_types(self, c):
        """Get information about all servers on this node."""
        return "Serial Devices:\n" + "\n\n".join(["Name: "+model.name +"\nVersion: " + model.version+ "\nDescription: " +model.description for model in self.sim_instr_models.values() if not (issubclass(model.cls,GPIBDeviceModel))]) + "\n\n" +"GPIB Devices:\n" + "\n\n".join(["Name: "+model.name +"\nVersion: " + model.version+ "\nDescription: " +model.description for model in self.sim_instr_models.values() if (issubclass(model.cls,GPIBDeviceModel))])

    @setting(100, "reload_available_scripts")
    def reload_available_scripts(self, c):
        reload(hss_config)
        self.load_scripts()
        
    def serverConnected(self, ID, name):
        """
        Attempt to connect to last connected serial bus server upon server connection.
        """
        # check if we aren't connected to a device, port and node are fully specified,
        # and connected server is the required serial bus server
        for node, port in self.devices.keys():
            if name==node:
               self.device_added((node,port))
               break
                    
        

        
       

__server__ = CSHardwareSimulatingServer()

if __name__ == '__main__':
    from labrad import util
    util.runServer(__server__)

