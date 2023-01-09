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

from labrad.server import LabradServe9r, Signal, setting
from labrad import util

from twisted.internet.defer import returnValue, inlineCallbacks

from importlib import reload, import_module

import collections
import sys

import UCLA_CS_labrad.config.hardwaresimulationserver_config as hss_config
from UCLA_CS_labrad.servers.hardwaresimulation import SimulatedGPIBInstrumentInterface, SimulatedSerialInstrumentInterface
from UCLA_CS_labrad.servers.hardwaresimulation.simulated_communication_interfaces import SimulatedGPIBCommunicationInterface,SimulatedSerialCommunicationInterface

from UCLA_CS_labrad.servers.hardwaresimulation.cablesimulation.simulated_signals import CableError

STATUS_TYPE = '*(s{name} s{desc} s{ver})'


#error class for HSS server (does not include errors inside simulated devices, to see these one must use the error queue)
class HSSError(Exception):
    errorDict ={0:'Device already exists at specified node and address',1:'No device exists at specified node and address',2: 'Device type not supported.',3:'No simulated device models were successfully imported.',4:'Device already selected.', 5:'Tried to set serial connection parameter for GPIB device.',6:'Error connecting cable: one of the channels already has a cable plugged in.',7:'Error (dis)connecting cable: one of the channels does not exist',8:'Error disconnecting cable: input channel did not have a cable plugged in.'}

    def __init__(self, code):
        self.code = code

    def __str__(self):
        if self.code in self.errorDict:
            return self.errorDict[self.code]
            
#structure to hold information about a successfully imported instrument model. name, version, and description are the same as written
#by specific device writer. cls is where the imported class itself is stored, so it's used to instantiate simulated devices of that model
SimInstrModel = collections.namedtuple('SimInstrModel', ['name','version','description','cls'])

        
# DEVICE CLASS
class HardwareSimulationServer(LabradServer):

    name='Hardware Simulation Server'
    
    #LabRAD signals this server can broadcast.
    device_added=Signal(565656,'Signal: Device Added','(s,i)')
    device_removed=Signal(676767,'Signal: Device Removed','(s,i)')

    def initServer(self):
        super().initServer()
        #dictionary mapping from 2-tuple (string representing bus server,positive int representing SimAddress) to wrapped simulated device (SerialCommunicationWrapper or GPIBCommunicationWrapper)
        self.wrapped_simulated_devices={}
       
        #dictionary mapping from names of imported instrument models (same as "name" class
        #property of imported pecific device class) to corresponding SimInstrModel
        self.sim_instr_models={}

        self.load_simulated_instrument_models()
        
        #if no instrument model classes were successfully imported, an error is raised and the server does not start, as the server is useless
        #if no simulated instruments can be created
        if not self.sim_instr_models:
            raise HSSError(4)

    def initContext(self,c):
        c['Device']=None
            
    #upon startup or whenever clients call a reload setting, using the dynamic importing capabilities provided by Python’s importlib
    # library, attempt to import each specific instrument class specified in the config file. each successfully imported class is stored in the server's sim_instr_models dictionary
    #(with warning strings being printed to alert the client about unsuccessful imports).
    def load_simulated_instrument_models(self): #Credit: Michael Ramm, writer of ScriptScanner
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
                
                # gets the specific device class from the module
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
        """
        Read from the input buffer of the CommunicationWrapper for the selected simulated instrument.
        Arguments:
            count (int) : number of bytes to read. if no count provided, read entire input buffer.
   
        Returns:
                    (str) : bytes that were read, converted to string
        """
        if not c['Device']:
            raise HSSError(1) #no device selected
        active_device=c['Device'] #get selected wrapped device (either SerialCommunicationWrapper or GPIBCommunicationWrapper)via client's context
        yield active_device.lock.acquire()
        # allow parallelization between context IDs with different selected simulated devices, but force the server to handle requests from context IDs with the same selected device sequentially.
        try:
            resp=active_device.read(count) #call CommunicationWrapper's read method
        finally:
            active_device.lock.release()
        returnValue(resp.decode()) #decode to convert from bytes to string
        

    @setting(14, 'Simulated Write', data='s', returns='i')
    def simulated_write(self,c,data):
    
        """
        Writes data to the selected wrapped device. Every time a write occurs, the device's CommunicationWrapper's output_buffer is extended with the data to be written. This buffer is then parsed to get a list of commands. For each command, the command is “interpreted” with the communication wrapper's interpret_command method, a task that is deferred to a non-reactor thread. If the interpretation gives an error, we add it to the error_queue. If it gives a response, we extend the input_buffer with this response. Once all commands have been interpreted and the CommunicationWrapper's input_buffer is fully updated, writing is considered to be done. See SerialCommunicationWrapper and GPIBCommunicationWrapper for differences between the two regarding buffer parsing, how instruments interpret commands, and how errors are handled.

        Arguments:
            data    (str)   : data to write (after converting to bytes)
        Returns:
                    (int) : number of bytes written
        """
        if not c['Device']:
            raise HSSError(1)
        active_device=c['Device']
        yield active_device.lock.acquire()
        try:
            yield active_device.write(data.encode()) #convert data to bytes, then pass it to CommunicationWrapper's write method
        finally:
            active_device.lock.release()
        returnValue(len(data))
        

        
    @setting(31, 'Add Device', node='s',address='i', instr_model='s',is_gpib='b',returns='')
    def add_device(self, c, node, address,instr_model,is_gpib):
    
        """
        Create new "simulated device" (object instantiated from imported specific simulated device class) and "plug it in" at a simulated location based on a bus server name and SimAddress (positive integer)
        Arguments:
            node    (str)   : should be name of real bus server responsible for device (i.e., which computer, and which bus of that computer, simulated device "plugged into"). however, can theoretically be anything if one plans to communicate with device directly using HSS.
            address   (int)   : SimAddress to add device at (this can be thought of as a port number for Serial devices, and a GPIB primary address for GPIB devices)
            instr_model (str): which instrument model added simulated device should be, matching "name" field in specific device class / SimInstrModel (meant to be sanity check to ensure user knows what type of device they're adding)
            
            is_gpib (bool): whether instrument is a gpib device or not
        Returns:
                    None
        """
        if (node,address) in self.wrapped_simulated_devices:
            raise HSSError(0) #device already present at that bus and simaddress
        if instr_model not in self.sim_instr_models or (issubclass(self.sim_instr_models[instr_model].cls,SimulatedGPIBInstrumentInterface))!=is_gpib:
            raise HSSError(2) #cannot add instrument of requested model since it either wasn't imported, or because type of instrument specified by is_gpib argument was inconsistent with actual type of device imported (based on interface used to write generic device)
            
        if issubclass(self.sim_instr_models[instr_model].cls,SimulatedGPIBInstrumentInterface):
            self.wrapped_simulated_devices[(node,address)]=SimulatedGPIBCommunicationInterface(self.sim_instr_models[instr_model].cls()) #if gpib device, wrap in GPIBCommunicationWrapper and add to sim_instr_models dictionary
        else:
            self.wrapped_simulated_devices[(node,address)]=SimulatedSerialCommunicationInterface(self.sim_instr_models[instr_model].cls()) #otherwise,serial device, so wrap in SerialCommunicationWrapper and add to sim_instr_models dictionary
        self.device_added((node,address)) #send out LabRAD Signal to interested servers indicating a simulated device being added, containing information about the computer/bus simulated device added at, and its SimAddress.
        
        
        
        
    @setting(32, 'Remove Device', node='s', address='i', returns='')
    def remove_device(self,c, node, address):
    
        """
        Remove "simulated device" at simulated location, also deleting device object (and thus losing its state)
        
        Arguments:
             node    (str)   : should be name of real bus server responsible for device (i.e., which computer, and which bus of that computer, simulated device "plugged into"). however, can theoretically be anything if one plans to communicate with device directly using HSS.
            address   (int)   : SimAddress of device (this can be thought of as a port number for Serial devices, and a GPIB primary address for GPIB devices)
        Returns:
                    None
        """
        if (node,address) not in self.wrapped_simulated_devices:
            raise HSSError(1) #no device at simulated location
        
        for context_obj in self.contexts.values():
            if context_obj.data['Device'] is self.wrapped_simulated_devices[(node,address)]:
                context_obj.data['Device']=None
                break #remove device from context of any clients that had it selected
        del self.wrapped_simulated_devices[(node,address)] #remove wrapped device from dictionary
        
        self.device_removed((node,address)) #send out LabRAD Signal to interested servers indicating a simulated device being removed, containing information about the computer/bus simulated device was at, and its SimAddress.
        
    
    @setting(41, 'Get In-Waiting', returns='i')
    def get_in_waiting(self,c):
    
        """
        Get number of bytes in selected device's CommunicationWrapper's input buffer
        Arguments:
            None
        Returns:
                    (int): number of bytes in buffer
        """
        if not c['Device']:
            raise HSSError(1)
        active_device=c['Device']
        yield active_device.lock.acquire()
        try:
            buf_len=len(active_device.input_buffer)
        finally:
            active_device.lock.release()
        returnValue(buf_len)
    
    @setting(42, 'Get Out-Waiting', returns='i')
    def get_out_waiting(self,c):
        """
        Get number of bytes in selected device's CommunicationWrapper's output buffer
        Arguments:
            None
        Returns:
                    (int): number of bytes in buffer
        """
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
        """
        Remove all bytes from selected device's CommunicationWrapper's input buffer
        Arguments:
            None
        Returns:
            None
        """
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
        """
        Remove all bytes from selected device's CommunicationWrapper's output buffer
        Arguments:
            None
        Returns:
            None
        """
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
        """
        Select a device by supplying its simulated location. Wrapped device placed in client's context dictionary to communicate with in future requests.
        Arguments:
             node    (str)   : should be name of real bus server responsible for device (i.e., which computer, and which bus of that computer, simulated device "plugged into"). however, can theoretically be anything if one plans to communicate with device directly using HSS.
            address   (int)   : SimAddress of device (this can be thought of as a port number for Serial devices, and a GPIB primary address for GPIB devices)
        Returns:
                    None
        """
        if c['Device']:
            raise HSSError(4) #a device is already selected
        c['Device']=self.wrapped_simulated_devices[(node,address)] #get wrapped device from wrapped_simulated_devices and add to client's context dictionary
    
      
    @setting(62, 'Deselect Device',returns='')
    def deselect_device(self,c):
        """
        Deselect selected instrument.
        Arguments:
            None
        Returns:
            None
        """
        c['Device']=None #remove device from client's context dictionary


    #Part of the HSS API is specific to getting or setting communication parameters for simulated serial devices, such as baudrate.
    # Each such parameter is stored as a property in the SerialCommunicationWrapper, so here implementing the HSS API is as simple as writing a setting for each parameter
    # that sets the communication parameter in the selected device’s wrapper to the provided value, or gets the current value.
    #Baudrate setting is commented; same logic is used in all the settings for serial communication parameters
    
    @setting(71, 'Baudrate', val=[': Query current baudrate', 'w: Set baudrate'], returns='w: Selected baudrate')
    def baudrate(self,c,val):
        """
        Get/set baudrate to use when communicating with selected simulated serial instrument.
        Arguments:
            val (int): Baudrate to set. If None, do not change current baudrate used.
        Returns:
            (int) Communication baudrate being used, after setting to new baudrate if applicable.
        """
        if not c['Device']:
            raise HSSError(1)
        active_device=c['Device']
        yield active_device.lock.acquire()
        try:
            if active_device.type=="GPIB":
                raise HSSError(5) #not a serial device, so no need to worry about serial communication parameters
            if val:
                active_device.comm_baudrate=val #set value for communication parameter in SerialCommunicationWrapper
            resp=active_device.comm_baudrate #get value for communication parameter in SerialCommunicationWrapper
        finally:
            active_device.lock.release()
        return resp
        
    @setting(72, 'Bytesize',val=[': Query current stopbits', 'w: Set bytesize'], returns='w: Selected bytesize')
    def bytesize(self,c,val):
        if not c['Device']:
            raise HSSError(1)
        active_device=c['Device']
        yield active_device.lock.acquire()
        try:
            if active_device.type=="GPIB":
                raise HSSError(5)
            if val:
                active_device.comm_bytesize=val
            resp=active_device.comm_bytesize
        finally:
            active_device.lock.release()
        return resp
        
    @setting(73, 'Parity', val=[': Query current parity', 'w: Set parity'], returns='w: Selected parity')
    def parity(self,c,val):
        if not c['Device']:
            raise HSSError(1)
        active_device=c['Device']
        yield active_device.lock.acquire()
        try:
            if active_device.type=="GPIB":
                raise HSSError(5)
            if val:
                active_device.comm_parity=val
            resp=active_device.comm_parity
        finally:
            active_device.lock.release()
        return resp
        
    @setting(74, 'Stopbits', val=[': Query current stopbits', 'w: Set stopbits'], returns='w: Selected stopbits')
    def stopbits(self,c,val):
        if not c['Device']:
            raise HSSError(1)
        active_device=c['Device']
        yield active_device.lock.acquire()
        try:
            if active_device.type=="GPIB":
                raise HSSError(5)
            if val:
                active_device.comm_stopbits=val
            resp=active_device.comm_stopbits
        finally:
            active_device.lock.release()
        return resp
        
    @setting(75, 'RTS', val='b', returns='b')
    def rts(self,c,val):
        if not c['Device']:
            raise HSSError(1)
        active_device=c['Device']
        yield active_device.lock.acquire()
        try:
            if active_device.type=="GPIB":
                raise HSSError(5)
            if val:
                active_device.comm_rts=val
            resp=active_device.comm_rts
        finally:
            active_device.lock.release()
        return rts
        
    @setting(76, 'DTR', val='b', returns='b')
    def dtr(self,c,val):
        if not c['Device']:
            raise HSSError(1)
        active_device=c['Device']
        yield active_device.lock.acquire()
        try:
            if active_device.type=="GPIB":
                raise HSSError(5)
            if val:
                active_device.comm_dtr=val
            resp=active_device.comm_dtr
        finally:
            active_device.lock.release()
        return resp
        
    @setting(81, 'Buffer Size',size='w', returns='w')
    def buffer_size(self,c,size=None):
        """
        Get/set max buffer size used for input and output buffers in CommunicationWrapper for selected device.  If there are currently more bytes in buffer than the new max to use, bytes at end of buffer are lost.
        Arguments:
            size (int): new max buffer size to use for both input buffer and output buffer, in bytes.
        Returns:
            Max buffer size used for both input buffer and output buffer, after setting to new value if applicable.
        """
        if not c['Device']:
            raise HSSError(1)
        active_device=c['Device']
        yield active_device.lock.acquire()
        try:
            if size:
                active_device.buffer_size=size
            resp=active_device.buffer_size
             
        finally:
             active_device.lock.release()
        returnValue(resp)
        
      
    @setting(92, 'Get Available Device Types',returns='*(ssb)')
    def get_available_device_types(self, c):
        """
        Get information about the valid models of instruments that can be added.
        Arguments:
            None
        Returns:
            (list of 3-tuples of form (str,str,bool) ): Returns information about each successfully imported specific device class, as a 3-tuple of form (name and version, description, GPIB or Serial).
        """
        return [(model.name +' v'+model.version, model.description, (issubclass(model.cls,SimulatedGPIBInstrumentInterface))) for model in self.sim_instr_models.values()]



    @setting(100, "Reload Available Device Types")
    def reload_available_scripts(self, c):
        """
        Using the dynamic importing capabilities provided by Python’s importlib library, attempt to import each specific instrument
        class specified in the HSS_config file. each successfully imported class is stored in the server's sim_instr_models dictionary
        (with warning strings being printed to alert the client about unsuccessful imports). Based on changes to config file or the specific device classes themselves, this will add
        new models (or fixed ones), remove old ones (or broken ones), or overwrite existing ones based on the "name" field of the class.
        All already-instantiated devices will not change.
        
        Arguments:
            None
            
        Returns:
            None
        """
        reload(hss_config)
        self.load_simulated_instrument_models()
        
    @setting(110, "Add Simulated Wire",out_node='s',out_address='i',out_channel='i',in_node='s',in_address='i',in_channel='i')
    def add_simulated_wire(self,c,out_node,out_address,out_channel,in_node,in_address,in_channel):
        """
        Connect a new simulated cable between an output channel of a simulated device, and an input channel of another simulated device.
        
        Arguments:
            out_node (str): Bus where device is whose output channel cable will be plugged into (as bus server name)
            out_address (int): SimAddress of device whose output channel cable will be plugged into
            out_channel (int): Which output channel of device to plug cable into (numbering starts at 1)
            in_node (str): Bus where device is whose input channel cable will be plugged into (as bus server name)
            in_address (int): SimAddress of device whose input channel cable will be plugged into
            in_channel (int): Which input channel of device to plug cable into (numbering starts at 1)
        Returns:
            None
        """
        out_dev=self.wrapped_simulated_devices[(out_node,out_address)]
        #get device whose output channel cable will be plugged into
        in_dev=self.wrapped_simulated_devices[(in_node,in_address)]
        #get device whose input channel cable will be plugged into
        
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
                
                
                #go to the channels list, and grab a reference to the OutputSignal at specified channel number.
                out_conn=out_dev.channels[out_channel-1]
                in_conn=in_dev.channels[in_channel-1]
                
                #go to the client-specified channel number for the input channel in the device’s channels list.
                #Call a method on this InputSignal called plug_in, passing it the OutputSignal reference (see InputSignal). Now, voltage is "flowing" from the output channel to the input channel via the shared SignalLog.
                in_conn.plug_in(out_conn)
            except CableError as e:
                raise HSSError(6) #see CableError in simulatedsignals file
            except (IndexError,AttributeError) as e:
                raise HSSError(7) #input or output channel number doesn't exist on specified device, or tried to treat an output channel as an input channel or vice versa
            finally:
                in_dev.lock.release()
                out_dev.lock.release()
           
    
    @setting(111, "Remove Simulated Wire",out_node='s',out_address='i',out_channel='i',in_node='s',in_address='i',in_channel='i')
    def remove_simulated_wire(self,c,out_node,out_address,out_channel,in_node,in_address,in_channel):
        """
        Disconnect an existing simulated cable between an output channel of a simulated device, and an input channel of another simulated device.
        
        Arguments:
            out_node (str): Bus where device is whose output channel cable will be plugged into (as bus server name)
            out_address (int): SimAddress of device whose output channel cable will be plugged into
            out_channel (int): Which output channel of device to plug cable into (numbering starts at 1)
            in_node (str): Bus where device is whose input channel cable will be plugged into (as bus server name)
            in_address (int): SimAddress of device whose input channel cable will be plugged into
            in_channel (int): Which input channel of device to plug cable into (numbering starts at 1)
        Returns:
            None
        """
        out_dev=self.wrapped_simulated_devices[(out_node,out_address)]
        in_dev=self.wrapped_simulated_devices[(in_node,in_address)]
        yield out_dev.lock.acquire()
        try:
            yield in_dev.lock.acquire()
        except:
            out_dev.lock.release()
        else:
            try:
            
                #go to the client-specified channel number for the input channel in the device’s channels list.
                #Call a method on this InputSignal called unplug (see InputSignal). Now, voltage is no longer "flowing" from the output channel to the input channel via the shared SignalLog and both channels are now available to have  new cables plugged in.
                out_conn=out_dev.channels[out_channel-1]
                in_conn=in_dev.channels[in_channel-1]
                in_conn.unplug()
            except (IndexError,AttributeError) as e:
                raise HSSError(7)
            except CableError as e:
                raise HSSError(8)
            finally:
                in_dev.lock.release()
                out_dev.lock.release()
        

            
    @setting(121, "List Buses",returns='*s')
    def list_buses(self,c):
        """
        Lists set of buses (each bus server name used to add device) that have 1 or more wrapped simulated devices "plugged in"
        Arguments:
            None
        Returns:
            (list of str): buses which 1 or more wrapped simulated devices "plugged in", found using keys of wrapped_simulated_devices
        """
        return list(set([loc[0] for loc in self.wrapped_simulated_devices]))
        
    @setting(122, "List Devices", bus='s', returns='*(iss)')
    def list_devices(self,c,bus):
        """
        Lists information about all simulated devices at a specific bus on a specific computer.
        Arguments:
            bus (str): bus server name (representing a GPIB or Serial Bus of a specific computer)
        Returns:
            (list of 3-tuples of form (int, str, str) ): information about each wrapped simulated device "plugged into" that bus (added using that bus server name); of form (sim address, instrument model name, instrument model description).
        """
        return [(loc[1],dev.name,dev.description) for loc,dev in self.wrapped_simulated_devices.items() if loc[0]==bus]


    @setting(130, "Get Device Error List", returns='*(sss)')
    def get_device_error_list(self,c):
        """
        Get error list of selected device from CommunicationWrapper, clearing the list. Every time a SimulatedInstrumentError is raised in either the CommunicationWrapper or inside the device itself, it's added to this list.
        Arguments:
            None
        Returns:
            (list of (str,str,str) ): list of 3-tuples, each representing a SimulatedInstrumentError that arose in the CommunicationWrapper or inside the device object while the device was interpreting a command; these are of the form (time stamp, command causing error, error string)
        """
        if not c['Device']:
            raise HSSError(1)
        active_device=c['Device']
        yield active_device.lock.acquire()
        try:
            err_list=list(active_device.error_list)
            active_device.error_list=[] #empty device's error list
        finally:
            active_device.lock.release()
        returnValue(err_list)
    
    def serverConnected(self, ID, name):
        """
        LabRAD Signal Handler for signal from manager when a new server starts. Used for case when a Bus Server starts when HSS already has simulated devices connected on that bus.
        """

        for node, address in self.wrapped_simulated_devices.keys():
            if name==node:
               self.device_added((node,address))
               #if a bus server was connected, for all simulated devices on that bus (meaning, all simulated devices added using that bus server name)
               #send out a DeviceAdded Signal to all interested servers saying a new device was added, containing information about the computer/bus simulated device added at,
               #and its SimAddress. These Signals will only matter to the newly started bus server, and will make it
               #aware of the simulated devices on its bus.
                    
        


    #TODO: Add setting to list simulated cables

__server__ = HardwareSimulationServer()

if __name__ == '__main__':
    from labrad import util
    util.runServer(__server__)

