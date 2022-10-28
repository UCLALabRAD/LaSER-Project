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
    errorDict ={ 0:'Device already exists at specified node and address',1:'No device exists at specified node and address',2: 'Device type not supaddressed.',3: 'No directories for Simulated Device files found in registry',4:'One or more simulated device info blocks were not successfully parsed in directory.', 5:'Unable to find class for desired device in module'}

    def __init__(self, code):
        self.code = code

    def __str__(self):
        if self.code in self.errorDict:
            return self.errorDict[self.code]
            
class SimulatedDeviceError(Exception):
    errorDict ={0:'Serial command not supaddressed by device.', 1: 'Unsupaddressed Value for Serial Connection Parameter'}

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
            except importError as e:
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
                    


    

        
        

    @setting(14, 'Simulated Write', data='s', returns='')
    def simulated_write(self,c,data):
        if not c['Device']:
            returnValue(None)
        active_device=c['Device']
        active_device.write()
        resp=yield active_device.read()
        returnValue(resp)
        

        
    @setting(31, 'Add Device', node='s',address='s', instr_model='s',is_gpib='b',returns='')
    def add_device(self, c, node, address,instr_model,is_gpib):
        if (node,address) in self.devices:
            raise HSSError(0)
        if instr_model not in self.sim_instr_models or (issubclass(self.sim_instr_models[instr_model].cls,GPIBDeviceModel))!=is_gpib:
            raise HSSError(2)
            
        if issubclass(self.sim_instr_models[instr_model].cls,GPIBDeviceModel)):
            self.devices[(node,address)]=GPIBDeviceCommInterface(self.sim_instr_models[instr_model].cls())
        else:
            self.devices[(node,address)]=SerialDeviceCommInterface(self.sim_instr_models[instr_model].cls())
        self.device_added((node,address))
        
        
        
        
    @setting(32, 'Remove Device', node='s', address='s', returns='')
    def remove_device(self,c, node, address):
        if (node,address) not in self.devices:
            raise HSSError(1)
        
        for context_obj in self.contexts.values():
            if context_obj.data['Device'] is self.devices[(node,address)]:
                context_obj.data['Device']=None
                break
        del self.devices[(node,address)]
        
        self.device_removed((node,address))
    
    @setting(41, 'Get In-Waiting', returns='i')
    def get_in_waiting(self,c):
        if not c['Device']:
            raise HSSError(1)
        active_device=c['Device']
        return active_device.in_waiting
    
    @setting(42, 'Get Out-Waiting', returns='i')
    def get_out_waiting(self,c):
        if not c['Device']:
            raise HSSError(1)
        active_device=c['Device']
        return active_device.out_waiting
    
    
    @setting(51, 'Reset Device Input Buffer', returns='')
    def reset_input_buffer(self,c):
        if not c['Device']:
            raise HSSError(1)
        active_device=c['Device']
        active_device.reset_input_buffer()
        
        
    @setting(52, 'Reset Device Output Buffer', returns='')
    def reset_output_buffer(self,c):
        if not c['Device']:
            raise HSSError(1)
        active_device=c['Device']
        active_device.reset_output_buffer()
        
        
    @setting(61, 'Select Device', node='s', address='s', returns='')
    def select_device(self,c,node,address):
        c['Device']=self.devices[(node,address)]

      
    @setting(62, 'Deselect Device',returns='')
    def deselect_device(self,c):    
        c['Device']=None


    @setting(71, 'Baudrate', val=[': Query current baudrate', 'w: Set baudrate'], returns='w: Selected baudrate')
    def baudrate(self,c,val):
        active_device=c['Device']
        if val:
            active_device.comm_baudrate=val
        return active_device.comm_baudrate
        
    @setting(72, 'Bytesize',val=[': Query current stopbits', 'w: Set bytesize'], returns='w: Selected bytesize')
    def bytesize(self,c,val):
        active_device=c['Device']
        if val:
            active_device.comm_bytesize=val
        return active_device.comm_bytesize
        
    @setting(73, 'Parity', val=[': Query current parity', 'w: Set parity'], returns='w: Selected parity')
    def parity(self,c,val):
        active_device=c['Device']
        if val:
            active_device.comm_parity=val
        return active_device.comm_parity
        
    @setting(74, 'Stopbits', val=[': Query current stopbits', 'w: Set stopbits'], returns='w: Selected stopbits')
    def stopbits(self,c,val):
        active_device=c['Device']
        if val:
            active_device.comm_stopbits=val
        return active_device.comm_stopbits
        
    @setting(75, 'RTS', val='b', returns='b')
    def rts(self,c,val):
        active_device=c['Device']
        if val:
            active_device.comm_rts=val
        return active_device.comm_rts
        
    @setting(76, 'DTR', val='b', returns='b')
    def dtr(self,c,val):
        active_device=c['Device']
        if val:
            active_device.comm_dtr=val
        return active_device.comm_dtr
        
    @setting(81, 'Buffer Size',returns='')
    def buffer_size(self,c,size):
        if not c['Device']:
            raise HSSError(1)
        active_device=c['Device']
        active_device.buffer_size=size
        return active_device.buffer_size
        
      
    @setting(92, 'Get Available Device Types',returns='*(ssb)')
    def get_available_device_types(self, c):
        return [(model.name +' v'+model.version, model.description, (issubclass(model.cls,GPIBDeviceModel))) for model in self.sim_instr_models.values()]

    @setting(100, "Reload Available Device Types")
    def reload_available_scripts(self, c):
        reload(hss_config)
        self.load_scripts()
        
    @setting(110, "Add Simulated Wire",out_node='s',out_address='s',out_channel='i',in_node='s',in_address='s',in_channel='i')
    def add_simulated_wire(self,c,out_node,out_address,out_channel,in_node,in_address,in_channel):
        out_dev=(out_node,out_address)
        in_dev=(in_node,in_address)
        #if out_dev not in self.devices or in_dev not in self.devices:
        #raise HSSError(1)
       # try:
        out_conn=self.devices[out_dev].channels[out_channel-1]
        in_conn=self.devices[in_dev].channels[in_channel-1]
        in_conn.plug_in(out_conn)
       # except:
            #raise HSSError(1)
            
        
           
    
    @setting(111, "Remove Simulated Wire",in_node='s',in_address='s',in_channel='i')
    def remove_simulated_wire(self,c,in_node,in_address,in_channel):
        in_dev=(in_node,in_address)
        #try:
        in_conn=self.devices[in_dev].channels[in_channel-1]
        in_conn.unplug()
        #except:
            #raise HSSError(1)
            
    @setting(121, "List Buses",returns='*s')
    def list_buses(self,c):
        return set([loc[0] for loc in self.devices])
        
    @setting(122, "List Devices", bus='s', returns='*(iss)')
    def list_devices(self,c,bus):
        return [(loc[1],dev.name,dev.description) for loc,dev in self.devices.items() if loc[0]==bus]
        
    
    
    def serverConnected(self, ID, name):
        """
        Attempt to connect to last connected serial bus server upon server connection.
        """
        # check if we aren't connected to a device, address and node are fully specified,
        # and connected server is the required serial bus server
        for node, address in self.devices.keys():
            if name==node:
               self.device_added((node,address))
               break
                    
        


    #list simulated cables

__server__ = CSHardwareSimulatingServer()

if __name__ == '__main__':
    from labrad import util
    util.runServer(__server__)

