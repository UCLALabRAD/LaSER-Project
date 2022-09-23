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

from labrad.errors import Error
from labrad.server import LabradServer, Signal, setting

from UCLA_CS_labrad.servers.serial import sim_serial_device_config_parser,sim_gpib_device_config_parser
import os
import importlib
from labrad import auth, protocol, util, types as T, constants as C
STATUS_TYPE = '*(s{name} s{desc} s{ver})'
__all__ = ['SerialDevice','CSHardwareSimulatingServer','SimulatedDeviceError']

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
    
	command_dict=None
        
    def __init__(self):
        self.output_buffer=bytearray(b'')
        self.input_buffer=bytearray(b'')
   
    def interpret_serial_command(self, cmd):
        cmd,*args=cmd.split(" ")
        if (cmd,len(args)) not in self.command_dict:
            raise SimulatedDeviceError(0)
        elif not self.command_dict[(cmd,len(args))]:
            pass
        else:
            return self.command_dict[(cmd,len(args))](*args)
			
class GPIBDevice(object):

	termination_character=''
    command_dict=None
	id_command="*IDN?"
	id_string=None
	supports_command_chaining=False
	supports_any_prefix=False
    def __init__(self):
        self.output_buffer=bytearray(b'')
        self.input_buffer=bytearray(b'')
   
    def interpret_serial_command(self, cmd):
		if cmd==self.id_command:
		        return self.address
        for cmd_specs, func in self.command_dict:
		    if (is_valid_cmd(cmd,cmd_specs)):
			    resp=func(*args)
			    if resp:
				    return resp+=self.termination_character
				else:
				    return None
			    
	    
		
		
	def is_valid_cmd(self,cmd,cmd_format):
	    cmd,*args=cmd.split(' ')
	    cmd_format,num_args, query_option=cmd_format
		if not (len(args)==num_args or (query_option and len(args)==0)):
		    return False
		if (query_option and cmd_format[-1]=='?'):
		    cmd_format=cmd_format[:-1]
	    if not (cmd.toLower()==cmd or cmd.toUpper()==cmd):
		    return False
	    cmd=cmd.toLower()
		cmd_chunks_list=cmd.split(':')
		cmd_format_chunks_list=cmd_format.split(':')
		if len(cmd_chunks_list)!=len(cmd_format_chunks_list):
		    return False
		for cmd_chunk,cmd_format_chunk in cmd_format_chunks_list,:
	        prefix=str([char for char in cmd_format_chunk if char.isUpper()])
			prefix=prefix.toLower()
			cmd_format_chunk=cmd_format_chunk.toLower()
            if supports_any_prefix:
			    if not (cmd_chunk.startswith(prefix) and cmd_format_chunk.startswith(cmd_chunk)):
				   return False
			else:
			    if not (cmd_chunk==prefix or cmd_chunk==cmd_format_chunk):
				   return False
		return True
		
	    
# DEVICE CLASS
class CSHardwareSimulatingServer(LabradServer):
    name='CS Hardware Simulating Server'
    serial_device_added=Signal(565656,'Signal: Simulated Serial Device Added','(s,s)')
    serial_device_removed=Signal(676767,'Signal: Simulated Serial Device Removed','(s,s)')
    gpib_device_added=Signal(787878,'Signal: Simulated GPIB Device Added','(s,s)')
    gpib_device_removed=Signal(898989,'Signal: Simulated GPIB Device Removed','(s,s)')
   
    registryDirectory = ['', 'Servers', 'CS Hardware Simulating Server','Simulated Devices']

    @inlineCallbacks
    def initServer(self):
        super().initServer()
        self.devices={}
		self.serial_device_configs={}
		self.gpib_device_configs={}
        try:
            self.HSS_serial_config_dirs=yield self._getSimSerialDeviceDirectories(self.registryDirectory)
			self.HSS_GPIB_config_dirs=yield self._getSimGPIBDeviceDirectories(self.registryDirectory)
            if not ((self.HSS_serial_config_dirs and len(self.HSS_serial_config_dirs)>0) or (self.HSS_GPIB_config_dirs and len(self.HSS_GPIB_config_dirs)>0)):
                raise Error()
        except:
            raise HSSError(3)
        try:
            self.refreshSerialDeviceTypes()
			self.refreshGPIBDeviceTypes()
            if len(self.serial_device_configs)==0 and len(self.gpib_device_configs)==0:
                raise Error()
        except:
            raise HSSError(4)

    def initContext(self,c):
        c['Device']=None
            
            
    def refreshSerialDeviceTypes(self):
        """Refresh the list of available servers."""
        # configs is a nested map from name to version to list of classes.
        #
        # This allows us to deal with cases where there are many definitions
        # for different server versions, and possibly also redundant defitions
        # for the same version.
        configs = {}
        # look for .ini files
        for dirname in self.HSS_serial_config_dirs:
            for path, dirs, files in os.walk(dirname):
                if '.simdeviceignore' in files:
                    del dirs[:] # clear dirs list so we don't visit subdirs
                    continue
                for f in files:
                    _, ext = os.path.splitext(f)
                    if ext.lower() != ".py":
                        continue
                    else:
                        conf = sim_serial_device_config_parser.find_config_block(path, f)
                        if conf is None:
                            continue
                    config = sim_serial_device_config_parser.from_string(conf, f, path)
                    versions = configs.setdefault(config.name, {})
                    versions.setdefault(config.version, []).append(config)
           
                        

        device_configs = {}
        for versions in configs.values():
            for devices in versions.values():
                if len(devices) > 1:
                    conflicting_files = [d.filename for d in devices]
                    d = devices[0]
                    logging.warning(
                        'Found redundant device configs with same name and '
                        'version; will use {}. name={}, version={}, '
                        'conflicting_files={}'
                        .format(d.filename, d.name, d.version,
                                conflicting_files))

            devices = [ss[0] for ss in versions.values()]
            devices.sort(key=lambda s: s.version_tuple)
            if len(devices) > 1:
                # modify server name for all but the latest version
                for d in devices[:-1]:
                    d.name = '{}-{}'.format(d.name, d.version)

            for d in devices:
                device_configs[d.name] = d
				
			self.serial_device_configs.update(device_configs)
    def refreshGPIBDeviceTypes(self):
        """Refresh the list of available servers."""
        # configs is a nested map from name to version to list of classes.
        #
        # This allows us to deal with cases where there are many definitions
        # for different server versions, and possibly also redundant defitions
        # for the same version.
        configs = {}
        # look for .ini files
        for dirname in self.HSS_config_dirs:
            for path, dirs, files in os.walk(dirname):
                if '.simdeviceignore' in files:
                    del dirs[:] # clear dirs list so we don't visit subdirs
                    continue
                for f in files:
                    _, ext = os.path.splitext(f)
                    if ext.lower() != ".py":
                        continue
                    else:
                        conf = sim_device_config_parser.find_config_block(path, f)
                        if conf is None:
                            continue
                    config = sim_device_config_parser.from_string(conf, f, path)
                    versions = configs.setdefault(config.name, {})
                    versions.setdefault(config.version, []).append(config)
           
                        

        device_configs = {}
        for versions in configs.values():
            for devices in versions.values():
                if len(devices) > 1:
                    conflicting_files = [d.filename for d in devices]
                    d = devices[0]
                    logging.warning(
                        'Found redundant device configs with same name and '
                        'version; will use {}. name={}, version={}, '
                        'conflicting_files={}'
                        .format(d.filename, d.name, d.version,
                                conflicting_files))

            devices = [ss[0] for ss in versions.values()]
            devices.sort(key=lambda s: s.version_tuple)
            if len(devices) > 1:
                # modify server name for all but the latest version
                for d in devices[:-1]:
                    d.name = '{}-{}'.format(d.name, d.version)

            for d in devices:
                device_configs[d.name] = d
				
			self.gpib_device_configs.update(device_configs)
			
			
    def _relayMessage(self, signal, **kw):
        """Send messages out to LabRAD."""
        kw['node'] = self.name
        mgr = self.client.manager
        mgr.send_named_message('simdevice.' + signal, tuple(kw.items()))
   
    def status(self):
        """Get information about all servers on this node."""
        def device_info(config):
            return (config.name, config.description or '', config.version)

        return [device_info(config) for _name, config in sorted(self.device_configs.items())]



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
        active_device=c['Device']
        active_device.output_buffer.extend(data.encode())
        *cmds, rest=active_device.output_buffer.decode().split(active_device.termination_character)
        for cmd in cmds:
            command_interpretation=active_device.interpret_serial_command(cmd)
            active_device.input_buffer.extend(command_interpretation.encode())
                
        active_device.output_buffer=bytearray(rest.encode())
    
    @setting(31, 'Add Simulated Serial Device', node='s',port='s', device_type='s',returns='')
    def add_serial_device(self, c, node, port,device_type):
        if (node,port) in self.devices:
            raise HSSError(0)
        if device_type not in self.serial_device_configs:
            raise HSSError(2)
        spec = importlib.util.spec_from_file_location(self.serial_device_configs[device_type].module_name,self.serial_device_configs[device_type].module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module) #possible safety issue- shouldnt have to run ANYTHING
        try:
            DevClass=getattr(module,device_type)
            self.devices[(node,port)]=DevClass()
        except:
            raise HSSError(5)
        self.serial_device_added((node,port))
        
        
    @setting(32, 'Remove Simulated Serial Device', node='s', port='s', returns='')
    def remove_serial_device(self,c, node, port):
        if (node,port) not in self.devices: 
            raise HSSError(1)
        
        for context_obj in self.contexts.values():
            if context_obj.data['Device'] is self.devices[(node,port)]:
                context_obj.data['Device']=None
                break
        del self.devices[(node,port)]

        self.serial_device_removed((node,port))
    
    @setting(33, 'Add Simulated GPIB Device', node='s',address='s', device_type='s',returns='')
    def add_gpib_device(self, c, node, address,device_type):
        if (node,address) in self.devices:
            raise HSSError(0)
        if device_type not in self.gpib_device_configs:
            raise HSSError(2)
        spec = importlib.util.spec_from_file_location(self.gpib_device_configs[device_type].module_name,self.gpib_device_configs[device_type].module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module) #possible safety issue- shouldnt have to run ANYTHING
        try:
            DevClass=getattr(module,device_type)
            self.devices[(node,port)]=DevClass()
        except:
            raise HSSError(5)
        self.gpib_device_added((node,address))
        
        
    @setting(34, 'Remove Simulated GPIB Device', node='s', address='s', returns='')
    def remove_gpib_device(self,c, node, address):
        if (node,address) not in self.devices: 
            raise HSSError(1)
        
        for context_obj in self.contexts.values():
            if context_obj.data['Device'] is self.devices[(node,address)]:
                context_obj.data['Device']=None
                break
        del self.devices[(node,address)]

        self.gpib_device_removed((node,address))
    
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
        
      
    @setting(92, 'Get Device Types',returns='*s')
    def available_device_types(self, c):
        """Get information about all servers on this node."""
        def device_info(config):
            return config.name + " "+ (config.description or '') +" "+ config.version
        return ["Serial Device:"+device_info(config) for _name, config in sorted(self.serial_device_configs.items())]+["GPIB Device:"+device_info(config) for _name, config in sorted(self.gpib_device_configs.items())]

    @inlineCallbacks
    def _getSimSerialDeviceDirectories(self, path):
        """
        A recursive function that gets any parameters in the given directory.
        Arguments:
            topPath (list(str)): the top-level directory that Parameter vault has access to.
                                    this isn't modified by any recursive calls.
            subPath (list(str)): the subdirectory from which to get parameters.
        """
        # get everything in the given directory
        yield self.client.registry.cd(path)
		yield self.client.registry.cd('Serial')
        _, keys = yield self.client.registry.dir()
        dirs= yield self.client.registry.get('directories')
        returnValue(dirs)
		
    @inlineCallbacks
    def _getSimGPIBDeviceDirectories(self, path):
        """
        A recursive function that gets any parameters in the given directory.
        Arguments:
            topPath (list(str)): the top-level directory that Parameter vault has access to.
                                    this isn't modified by any recursive calls.
            subPath (list(str)): the subdirectory from which to get parameters.
        """
        # get everything in the given directory
        yield self.client.registry.cd(path)
		yield self.client.registry.cd('GPIB')
        _, keys = yield self.client.registry.dir()
        dirs= yield self.client.registry.get('directories')
        returnValue(dirs)
		
		
    @inlineCallbacks
    def serverConnected(self, ID, name):
        """
        Attempt to connect to last connected serial bus server upon server connection.
        """
        # check if we aren't connected to a device, port and node are fully specified,
        # and connected server is the required serial bus server
		
        if name.endswith('GPIB Bus Server'):
		    for node, port in self.devices.keys():
			    if name.startswith(node) and isinstance(self.devices[(node,port)],SimulatedGPIBDevice):
				    self.gpib_device_added((node,address))
		elif name.endswith('Serial Bus Server'):
		    for node, port in self.devices.keys():
			    if name.startswith(node) and isinstance(self.devices[(node,port)],SimulatedSerialDevice):
				    self.serial_device_added((node,address))
		
        
       

__server__ = CSHardwareSimulatingServer()

if __name__ == '__main__':
    from labrad import util
    util.runServer(__server__)

