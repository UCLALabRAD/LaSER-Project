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

from UCLA_CS_labrad.servers.serial import sim_device_config_parser
import os
import importlib
from labrad import auth, protocol, util, types as T, constants as C
STATUS_TYPE = '*(s{name} s{desc} s{ver})'
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
       
        
    def __init__(self):
        self.output_buffer=bytearray(b'')
        self.input_buffer=bytearray(b'')
   
    def interpret_serial_command(self, cmd):
        cmd,*args=cmd.split(" ")
        if (cmd,len(args)) not in self.command_dict:
            print('wrong')
        else:
            return self.command_dict[(cmd,len(args))](*args)
        
    
# DEVICE CLASS
class CSHardwareSimulatingServer(LabradServer):
    name='CS Hardware Simulating Server'
    device_added=Signal(565656,'Signal: Simulated Device Added','(s,s)')
    device_removed=Signal(676767,'Signal: Simulated Device Removed','(s,s)')
   
    registryDirectory = ['', 'Servers', 'CS Hardware Simulating Server','Simulated Devices']

    @inlineCallbacks
    def initServer(self):
        super().initServer()
        self.devices={}
        self.HSS_config_dirs=yield self._getSimDeviceDirectories(self.registryDirectory)
        self.refreshDeviceTypes()
            
            
    def refreshDeviceTypes(self):
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
        self.device_configs = device_configs
        # Send a message with the current server list. We pre-flatten the server
        # status information to the correct type to work around a problem with
        # type inference while flattening (#342).
        status_data = T.flatten(self.status(), STATUS_TYPE)
        self._relayMessage('status', devices=status_data)

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



    @setting(11, 'Read', count='i', returns='s')
    def read(self,c,count):
        active_device=c['Device']
        write_out,rest=active_device.input_buffer[:count],active_device.input_buffer[count:]
        active_device.input_buffer=rest
        return write_out.decode()

    
    @setting(12, 'Write', data='s', returns='')
    def write(self,c,data):
        active_device=c['Device']
        active_device.output_buffer.extend(data.encode())
        *cmds, rest=active_device.output_buffer.decode().split("\r\n")
        for cmd in cmds:
            command_interpretation=active_device.interpret_serial_command(cmd)
            active_device.input_buffer.extend(command_interpretation.encode())

            
            
            
                
        active_device.output_buffer=bytearray(rest.encode())
    
   


    
    @setting(31, 'Add Simulated Device', node='s',port='s', device_type='s',returns='')
    def add_device(self, c, node, port,device_type):
        if port in self.devices:
            raise HSSError(0)
        if device_type not in self.device_configs:
            raise HSSError(0)
        spec = importlib.util.spec_from_file_location(self.device_configs[device_type].module_name,self.device_configs[device_type].module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        DevClass=getattr(module,device_type)
        self.devices[(node,port)]=DevClass()
        self.device_added((node,port))
        
        
    @setting(32, 'Remove Simulated Device', node='s', port='s', returns='')
    def remove_device(self,c, node, port):
        if (node,port) in self.devices: 
                  for context_obj in self.contexts.values():
                    if 'Device' in context_obj.data and context_obj.data['Device'] is self.devices[(node,port)]:
                        del context_obj.data['Device']
                        break
                  del self.devices[(node,port)]
        else:
            raise HSSError(1)
        self.device_removed((node,port))
    
    @setting(41, 'Get In-Waiting', returns='i')
    def get_in_waiting(self,c):
        active_device=c['Device']
        return len(active_device.input_buffer)
    
    @setting(42, 'Get Out-Waiting', returns='i')
    def get_out_waiting(self,c):
        active_device=c['Device']
        return len(active_device.output_buffer)
    
    
    @setting(51, 'Reset Input Buffer', returns='')
    def reset_input_buffer(self,c):
        active_device=c['Device']
        active_device.input_buffer=bytearray(b'')
    
    @setting(52, 'Reset Output Buffer', returns='')
    def reset_output_buffer(self,c):
        active_device=c['Device']
        active_device.output_buffer=bytearray(b'')

    @setting(61, 'Select Device', node='s', port='s', returns='')
    def select_device(self,c,node,port):
        if 'Device' in c:
            pass
        if (node,port) not in self.devices:
            pass
        c['Device']=self.devices[(node,port)]
        print(len(self.contexts))
        self.device_removed((node,port))
      
    @setting(62, 'Deselect Device',returns='')
    def deselect_device(self,c,node):
        if 'Device' in c:
                  for node,port in self.devices:
                        if self.devices[(node,port)]==c['Device']:
                            self.device_added((node,port))
                            break
                        
                  del c['Device']
        else:
            pass

    @setting(71, 'Baudrate', val=[': Query current baudrate', 'w: Set baudrate'], returns='w: Selected baudrate')
    def baudrate(self,c,val):
        active_device=c['Device']
        if val:
            if val!=active_device.required_baudrate:
                raise SimulatedDeviceError(0)
            else:
                active_device.actual_baudrate=val
        return active_device.actual_baudrate
        
    @setting(72, 'Bytesize',val=[': Query current stopbits', 'w: Set bytesize'], returns='w: Selected bytesize')
    def bytesize(self,c,val):
        active_device=c['Device']
        if val:
            if val!=active_device.required_bytesize:
                raise SimulatedDeviceError(0)
            else:
                active_device.actual_bytesize=val
        return active_device.actual_bytesize
        
    @setting(73, 'Parity', val=[': Query current parity', 'w: Set parity'], returns='w: Selected parity')
    def parity(self,c,val):
        active_device=c['Device']
        if val:
            if val!=active_device.required_parity:
                raise SimulatedDeviceError(0)
            else:
                active_device.actual_parity=val
        return active_device.actual_parity
        
    @setting(74, 'Stopbits', val=[': Query current stopbits', 'w: Set stopbits'], returns='w: Selected stopbits')
    def stopbits(self,c,val):
        active_device=c['Device']
        if val!=active_device.required_stopbits:
            raise SimulatedDeviceError(0)
        else:
            active_device.actual_stopbits=val
        return active_device.actual_stopbits
        
    @setting(75, 'RTS', val='b', returns='b')
    def rts(self,c,val):
        active_device=c['Device']
 
        if val!=active_device.required_rts:
            raise SimulatedDeviceError(0)
        else:
            active_device.actual_rts=val
        return active_device.actual_rts
        
    @setting(76, 'DTR', val='b', returns='b')
    def dtr(self,c,val):
        active_device=c['Device']
 
        if val!=active_device.required_dtr:
            raise SimulatedDeviceError(0)
        else:
            active_device.actual_dtr=val
        return active_device.actual_dtr
        
        
    @setting(81, 'Buffer Size', returns='')
    def buffer_size(self,c):
        return 0
        
    @setting(91, 'Get Devices List',node_name='s', returns='*s')
    def get_devices_list(self,c,node_name):
        return list([port for (node,port) in self.devices if node==node_name])
      
    @setting(92, 'Get Device Types',returns='*s')
    def available_device_types(self, c):
        """Get information about all servers on this node."""
        def device_info(config):
            return config.name + " "+ (config.description or '') +" "+ config.version
        return [device_info(config) for _name, config in sorted(self.device_configs.items())]

    @inlineCallbacks
    def _getSimDeviceDirectories(self, path):
        """
        A recursive function that gets any parameters in the given directory.
        Arguments:
            topPath (list(str)): the top-level directory that Parameter vault has access to.
                                    this isn't modified by any recursive calls.
            subPath (list(str)): the subdirectory from which to get parameters.
        """
        # get everything in the given directory
        yield self.client.registry.cd(path)
        _, keys = yield self.client.registry.dir()
        dirs= yield self.client.registry.get('directories')
        returnValue(dirs)
       

__server__ = CSHardwareSimulatingServer()

if __name__ == '__main__':
    from labrad import util
    util.runServer(__server__)

