"""
### BEGIN NODE INFO
[info]
name = Hardware Simulation Server
version = 1.1
description = Gives access to serial devices via pyserial.
instancename = Hardware Simulation Server

[startup]
cmdline = %PYTHON% %FILE%
timeout = 20

[shutdown]
message = 987654321
timeout = 20
### END NODE INFO
"""

from labrad.server import LabradServer, Signal, setting
from labrad import util

from twisted.internet.defer import returnValue, inlineCallbacks

from importlib import reload, import_module

import collections
import sys

import UCLA_CS_labrad.config.hardwaresimulationserver_config as hss_config
from UCLA_CS_labrad.servers.hardwaresimulation import SimulatedGPIBInstrument, SimulatedSerialInstrument
from UCLA_CS_labrad.servers.hardwaresimulation.simulated_communication_interfaces import SimulatedGPIBCommunicationInterface,SimulatedSerialCommunicationInterface


STATUS_TYPE = '*(s{name} s{desc} s{ver})'

class HSSError(Exception):
    errorDict ={ 0:'Device already exists at specified node and address',1:'No device exists at specified node and address',2: 'Device type not supaddressed.',3: 'No directories for Simulated Device files found in registry',4:'One or more simulated device info blocks were not successfully parsed in directory.', 5:'Unable to find class for desired device in module'}

    def __init__(self, code):
        self.code = code

    def __str__(self):
        if self.code in self.errorDict:
            return self.errorDict[self.code]
            
            
SimInstrModel = collections.namedtuple('SimInstrModel', ['name','version','description','cls'])

        
# DEVICE CLASS
class HardwareSimulationServer(LabradServer):

    name='Hardware Simulation Server'
    device_added=Signal(565656,'Signal: Device Added','(s,i)')
    device_removed=Signal(676767,'Signal: Device Removed','(s,i)')

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
                    


    
    @setting(13, 'Simulated Read', count='i', returns='s')
    def simulated_read(self,c,count=None):
        if not c['Device']:
            return None
        active_device=c['Device']
        yield active_device.lock.acquire()
        try:
            resp=active_device.read(count)
        finally:
            active_device.lock.release()
        returnValue(resp.decode())
        

    @setting(14, 'Simulated Write', data='s', returns='i')
    def simulated_write(self,c,data):
        if not c['Device']:
            return None
        active_device=c['Device']
        yield active_device.lock.acquire()
        try:
            yield active_device.write(data.encode())
        finally:
            active_device.lock.release()
        returnValue(len(data))
        

        
    @setting(31, 'Add Device', node='s',address='i', instr_model='s',is_gpib='b',returns='')
    def add_device(self, c, node, address,instr_model,is_gpib):
        if (node,address) in self.devices:
            raise HSSError(0)
        if instr_model not in self.sim_instr_models or (issubclass(self.sim_instr_models[instr_model].cls,SimulatedGPIBInstrument))!=is_gpib:
            raise HSSError(2)
            
        if issubclass(self.sim_instr_models[instr_model].cls,SimulatedGPIBInstrument):
            self.devices[(node,address)]=SimulatedGPIBCommunicationInterface(self.sim_instr_models[instr_model].cls())
        else:
            self.devices[(node,address)]=SimulatedSerialCommunicationInterface(self.sim_instr_models[instr_model].cls())
        self.device_added((node,address))
        
        
        
        
    @setting(32, 'Remove Device', node='s', address='i', returns='')
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
        yield active_device.lock.acquire()
        try:
            buf_len=len(active_device.input_buffer)
        finally:
            active_device.lock.release()
        returnValue(buf_len)
    
    @setting(42, 'Get Out-Waiting', returns='i')
    def get_out_waiting(self,c):
        if not c['Device']:
            raise HSSError(1)
        active_device=c['Device']
        yield active_device.lock.acquire()
        try:
            buf_len=len(active_device.output_buffer)
        finally:
            active_device.lock.release()
        returnValue(buf_len)
    
    
    @setting(51, 'Reset Input Buffer', returns='')
    def reset_input_buffer(self,c):
        if not c['Device']:
            raise HSSError(1)
        active_device=c['Device']
        yield active_device.lock.acquire()
        try:
            active_device.reset_input_buffer()
        finally:
            active_device.lock.release()
        
        
    @setting(52, 'Reset Output Buffer', returns='')
    def reset_output_buffer(self,c):
        if not c['Device']:
            raise HSSError(1)
        active_device=c['Device']
        yield active_device.lock.acquire()
        try:
            active_device.reset_output_buffer()
        finally:
            active_device.lock.release()
        
    @setting(61, 'Select Device', node='s', address='i', returns='')
    def select_device(self,c,node,address):
        c['Device']=self.devices[(node,address)]
    
      
    @setting(62, 'Deselect Device',returns='')
    def deselect_device(self,c):    
        c['Device']=None


    @setting(71, 'Baudrate', val=[': Query current baudrate', 'w: Set baudrate'], returns='w: Selected baudrate')
    def baudrate(self,c,val):
        active_device=c['Device']
        yield active_device.lock.acquire()
        try:
            if val:
                active_device.comm_baudrate=val
            resp=active_device.comm_baudrate
        finally:
            active_device.lock.release()
        return resp
        
    @setting(72, 'Bytesize',val=[': Query current stopbits', 'w: Set bytesize'], returns='w: Selected bytesize')
    def bytesize(self,c,val):
        active_device=c['Device']
        yield active_device.lock.acquire()
        try:
            if val:
                active_device.comm_bytesize=val
            resp=active_device.comm_bytesize
        finally:
            active_device.lock.release()
        return resp
        
    @setting(73, 'Parity', val=[': Query current parity', 'w: Set parity'], returns='w: Selected parity')
    def parity(self,c,val):
        active_device=c['Device']
        yield active_device.lock.acquire()
        try:
            if val:
                active_device.comm_parity=val
            resp=active_device.comm_parity
        finally:
            active_device.lock.release()
        return resp
        
    @setting(74, 'Stopbits', val=[': Query current stopbits', 'w: Set stopbits'], returns='w: Selected stopbits')
    def stopbits(self,c,val):
        active_device=c['Device']
        yield active_device.lock.acquire()
        try:
            if val:
                active_device.comm_stopbits=val
            resp=active_device.comm_stopbits
        finally:
            active_device.lock.release()
        return resp
        
    @setting(75, 'RTS', val='b', returns='b')
    def rts(self,c,val):
        active_device=c['Device']
        yield active_device.lock.acquire()
        try:
            if val:
                active_device.comm_rts=val
            resp=active_device.comm_rts
        finally:
            active_device.lock.release()
        return rts
        
    @setting(76, 'DTR', val='b', returns='b')
    def dtr(self,c,val):
        active_device=c['Device']
        yield active_device.lock.acquire()
        try:
            if val:
                active_device.comm_dtr=val
            resp=active_device.comm_dtr
        finally:
            active_device.lock.release()
        return resp
        
    @setting(81, 'Buffer Size',returns='w')
    def buffer_size(self,c,size=None):
        if not c['Device']:
            raise HSSError(1)
        active_device=c['Device']
        yield active_device.lock.acquire()
        try:
             if size:
                 active_device.buffer_size=size
             resp=active_device.buffer_size
             
        finally:
             active_device.buffer_size.release()
        returnValue(resp)
        
      
    @setting(92, 'Get Available Device Types',returns='*(ssb)')
    def get_available_device_types(self, c):
        return [(model.name +' v'+model.version, model.description, (issubclass(model.cls,GPIBDeviceModel))) for model in self.sim_instr_models.values()]

    @setting(100, "Reload Available Device Types")
    def reload_available_scripts(self, c):
        reload(hss_config)
        self.load_simulated_instrument_models()
        
    @setting(110, "Add Simulated Wire",out_node='s',out_address='i',out_channel='i',in_node='s',in_address='i',in_channel='i')
    def add_simulated_wire(self,c,out_node,out_address,out_channel,in_node,in_address,in_channel):
        out_dev=self.devices[(out_node,out_address)]
        in_dev=self.devices[(in_node,in_address)]
        
        yield out_dev.lock.acquire()
        try:
            yield in_dev.lock.acquire()
        except:
            out_dev.lock.release()
        else:
            try:
                #out_dev_lock= out_dev.lock.acquire()
                #in_dev_lock=in_dev.lock.acquire()
                #yield DeferredList([out_dev_lock,in_dev_lock])
                out_conn=out_dev.channels[out_channel-1]
                in_conn=in_dev.channels[in_channel-1]
                in_conn.plug_in(out_conn)
            finally:
                in_dev.lock.release()
                out_dev.lock.release()
           
    
    @setting(111, "Remove Simulated Wire",out_node='s',out_address='i',out_channel='i',in_node='s',in_address='i',in_channel='i')
    def remove_simulated_wire(self,c,out_node,out_address,out_channel,in_node,in_address,in_channel):
        out_dev=self.devices[(out_node,out_address)]
        in_dev=self.devices[(in_node,in_address)]
        yield out_dev.lock.acquire()
        try:
            yield in_dev.lock.acquire()
        except:
            out_dev.lock.release()
        else:
            try:
                #out_dev_lock=out_dev.lock.acquire()
                #in_dev_lock=in_dev.lock.acquire()
                #yield DeferredList([out_dev_lock,in_dev_lock])
                in_conn=in_dev.channels[in_channel-1]
                in_conn.unplug()
            finally:
                in_dev.lock.release()
                out_dev.lock.release()
        

            
    @setting(121, "List Buses",returns='*s')
    def list_buses(self,c):
        return list(set([loc[0] for loc in self.devices]))
        
    @setting(122, "List Devices", bus='s', returns='*(iss)')
    def list_devices(self,c,bus):
        return [(loc[1],dev.name,dev.description) for loc,dev in self.devices.items() if loc[0]==bus]


    @setting(130, "Get Device Error List", returns='*(sss)')
    def get_device_error_list(self,c):
        if not c['Device']:
            raise HSSError(1)
        active_device=c['Device']
        yield active_device.lock.acquire()
        try:
            err_list=list(active_device.error_list)
            active_device.error_list=[]
        finally:
            active_device.lock.release()
        returnValue(err_list)
    
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

__server__ = HardwareSimulationServer()

if __name__ == '__main__':
    from labrad import util
    util.runServer(__server__)

