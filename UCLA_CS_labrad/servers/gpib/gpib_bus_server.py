# CHANGELOG
#
# 2011 December 10 - Peter O'Malley & Jim Wenner
#
# Fixed bug where doesn't add devices if no SOCKETS connected.
#
# 2011 December 5 - Jim Wenner
#
# Added ability to read TCPIP (Ethernet) devices if configured to use
# sockets (i.e., fixed port address). To do this, added getSocketsList
# function and changed refresh_devices.
#
# 2011 December 3 - Jim Wenner
#
# Added ability to read TCPIP (Ethernet) devices. Must be configured
# using VXI-11 or LXI so that address ends in INSTR. Does not accept if
# configured to use sockets. To do this, changed refresh_devices.
#
# To be clear, the gpib system already supported ethernet devices just fine
# as long as they weren't using raw socket protocol. The changes that
# were made here and in the next few revisions are hacks to make socket
# connections work, and should be improved.
#
# 2021 October 17 - Clayton Ho
# Added back automatic device polling
# 2021 November 25 - Clayton Ho
# Added configurable device polling
# 2021 December 15 - Clayton Ho
# Subclassed it from PollingServer to support polling
# instead of using server methods


"""
### BEGIN NODE INFO
[info]
name = GPIB Bus
version = 1.5.2
description = Gives access to GPIB devices via pyvisa.
instancename = %LABRADNODE% GPIB Bus

[startup]
cmdline = %PYTHON% %FILE%
timeout = 20

[shutdown]
message = 987654321
timeout = 100
### END NODE INFO
"""

from labrad.units import WithUnit
from labrad.server import setting
from labrad.errors import DeviceNotSelectedError

from twisted.internet.defer import returnValue, inlineCallbacks

import pyvisa as visa
from pyvisa_SimulatedInstrumentBackend import SimulatedInstrumentResource

from UCLA_CS_labrad.servers import PollingServer




KNOWN_DEVICE_TYPES = ('GPIB', 'TCPIP', 'USB','SIM')


class GPIBBusServer(PollingServer):
    """
    Provides direct access to GPIB-enabled devices.
    """

    name = '%LABRADNODE% GPIB Bus'
    defaultTimeout = WithUnit(1.0, 's')
    POLL_ON_STARTUP = True

    @inlineCallbacks        
    def initServer(self):
        super().initServer()
        self.devices = {}
        self.sim_addresses=[]
        self.HSS=None
        servers=yield self.client.manager.servers()
        
        #HSS already running case
        if 'Hardware Simulation Server' in [HSS_name for _,HSS_name in servers]:
            yield self.client.refresh()
            self.HSS=self.client.servers['Hardware Simulation Server']
            yield self.HSS.signal__device_added(8675311)
            yield self.HSS.signal__device_removed(8675312)
            #GPIB Bus Servers subscribe to two types of LabRAD Signals of this Hardware Simulation Server (HSS) while booting up: device addition and device removal LabRAD Signals.
            yield self.HSS.addListener(listener=self.simDeviceAdded,source = None,ID=8675311)
            yield self.HSS.addListener(listener=self.simDeviceRemoved, source=None, ID=8675312) #assign handlers
        self.rm_phys = visa.ResourceManager()
        
        #second ResourceManager used in the GPIB Bus Server’s polls with a new backend (found in pyvisa_SimulatedInstrumentBackend),
        #where resources are simulated GPIB instruments in the HSS.
        #This backend is essentially a wrapper over the HSS API (settings), instead of a wrapper over the NI-VISA driver.
        #When a ResourceManager with a default backend creates a Resource object to return to a caller of its open_resource method,
        #it uses the provided resource name to determine what subclass of the base Resource class to return. For all the real GPIB devices,
        #it returns a MessageBasedResource object; thus, this object is what is always stored in a GPIB Bus Server’s client’s
        #context dictionary when they make an address (select) request. one can override the process  ResourceManager uses to pick the
        #type of Resource object to return, and provide their own Resource subclass instead.  We write our own Resource subclass,
        #called SimulatedInstrumentResource (which can be seen in pyvisa_SimulatedInstrumentBackend); this way we have to implement
        #less methods in the new backend and essentially have more control over how each method call on the client’s Resource object
        #acted from top to bottom, only using the PyVISA functionality to take care of getting Resources and managing VISA sessions.
        #even if this means we’re mostly just doing glorified duck-typing, using the PyVISA infrastructure of Resources and backends
        #in the GPIB Bus Server code provides the opportunity to move closer towards using the actual MessageBasedResource objects
        #with our new backend, by editing the separate file with the implementation of SimulatedInstrumentResource and the new backend.

        self.rm_sim = visa.ResourceManager('l@SimulatedInstrumentBackend')
        default_session=self.rm_sim.session #default resource manager session
        
        #pass tools to backend to communicate with HSS
        self.rm_sim.visalib.set_attribute(default_session,'cli',self.client)
        self.rm_sim.visalib.set_attribute(default_session,'ser',self.HSS)
        self.rm_sim.visalib.set_attribute(default_session,'node',self.name)
        # load the reference to the simulated_device_list into the new backend as its “resource collection”
        self.rm_sim.visalib.set_attribute(default_session,'sim_addresses',self.sim_addresses) #TODO: should be able to compact to one line by passing parameters when initializing resource manager
        self.refreshDevices()

        
        
    def _poll(self):
        self.refreshDevices()

    def refreshDevices(self):
        """
        Refresh the list of known devices on this bus.
        Currently supported are GPIB devices and GPIB over USB.
        """
        try:
            #instead of polling the simulated_device_list directly, and instantiating our own object for each new simulated device,
            #we have both the ResourceManagers list their resources at the same time.
            #Then, for each new resource name, we could get the Resource from the appropriate ResourceManager
            #and put it in the resource dictionary.
            addresses = [str(x) for x in self.rm_phys.list_resources()+self.rm_sim.list_resources()]
            additions = set(addresses) - set(self.devices.keys())
            deletions = set(self.devices.keys()) - set(addresses)
            
            for addr in additions:
                try:
                    if not addr.startswith(KNOWN_DEVICE_TYPES):
                        continue
                        

                    instr = self.get_resource(addr)
                    instr.write_termination = ''
                    instr.clear()
                    if addr.endswith('SOCKET'):
                        instr.write_termination = '\n'
                    self.devices[addr] = instr
                    self.sendDeviceMessage('GPIB Device Connect', addr)
                except Exception as e:
                    print('Failed to add ' + addr + ':' + str(e))
                    raise
            for addr in deletions:
                self.devices[addr].close()
                del self.devices[addr]
                self.sendDeviceMessage('GPIB Device Disconnect', addr)
            
        except Exception as e:
            print('Problem while refreshing devices:', str(e))
            raise e
            
    def get_resource(self,address):
        try:
            return self.rm_phys.open_resource(address,resource_pyclass=MessageBasedResource) #try opening physical resource
        except:
            return self.rm_sim.open_resource(address,resource_pyclass=SimulatedInstrumentResource) #if this fails, try simulated
            
    def sendDeviceMessage(self, msg, addr):
        print(msg + ': ' + addr)
        self.client.manager.send_named_message(msg, (self.name, addr))


    def getDevice(self, c):
        if 'addr' not in c:
            raise DeviceNotSelectedError("No GPIB address selected.")
        if c['addr'] not in self.devices:
            raise Exception('Could not find device ' + c['addr'])
        instr = self.devices[c['addr']]
        return instr

    @setting(0, addr='s', returns='s')
    def address(self, c, addr=None):
        """
        Get or set the GPIB address for this context.

        To get the addresses of available devices,
        use the list_devices function.
        """
        if addr is not None:
            c['addr'] = addr
        return c['addr']

    @setting(2, time='v[s]', returns='v[s]')
    def timeout(self, c, time=None):
        """
        Get or set the GPIB timeout.
        """
        if time is not None:
            self.getDevice(c).timeout=time['ms']
        return WithUnit(self.getDevice(c).timeout/1000.0,'s')

    @setting(3, data='s', returns='')
    def write(self, c, data):
        """
        Write a string to the GPIB bus.
        """
        yield self.getDevice(c).write(data)

    @setting(8, data='y', returns='')
    def write_raw(self, c, data):
        """
        Write a string to the GPIB bus.
        """
        yield self.getDevice(c).write_raw(data)

    @setting(4, n_bytes='w', returns='s')
    def read(self, c, n_bytes=None):
        """
        Read from the GPIB bus.

        Termination characters, if any, will be stripped.
        This includes any bytes corresponding to termination in
        binary data. If specified, reads only the given number
        of bytes. Otherwise, reads until the device stops sending.
        """
        instr = self.getDevice(c)
        if n_bytes is None:
            ans = yield instr.read_raw()
        else:
            ans = yield instr.read_bytes(n_bytes)
        ans = ans.strip().decode()
        returnValue(ans)


    #TODO: Update to use resource object's query method
    @setting(5, data='s', returns='s')
    def query(self, c, data):
        """
        Make a GPIB query, a write followed by a read.

        This query is atomic.  No other communication to the
        device will occur while the query is in progress.
        """
        instr = self.getDevice(c)
        yield instr.write(data)
        ans = yield instr.read_raw()
        # convert from bytes to string for python 3
        ans = ans.strip().decode()
        returnValue(ans)

    @setting(7, n_bytes='w', returns='y')
    def read_raw(self, c, n_bytes=None):
        """
        Read raw bytes from the GPIB bus.

        Termination characters, if any, will not be stripped.
        If n_bytes is specified, reads only that many bytes.
        Otherwise, reads until the device stops sending.
        """
        instr = self.getDevice(c)
        if n_bytes is None:
            ans = yield instr.read_raw()
        else:
            ans = yield instr.read_bytes(n_bytes)
        returnValue(bytes(ans))

    @setting(20, returns='*s')
    def list_devices(self, c):
        """
        Get a list of devices on this bus.
        """
        return sorted(self.devices.keys())

    @setting(21)
    def refresh_devices(self, c):
        """
        Manually refresh devices.
        """
        self.refreshDevices()

    def _poll_fail(self, failure):
        print('Polling failed.')

        
            # SIGNALS
    @inlineCallbacks
    def serverConnected(self, ID, name):
        """
        Attempt to connect to last connected serial bus server upon server connection.
        """
        # case where HSS started after this bus server
        if name=='Hardware Simulating Server':
            yield self.client.refresh()
            self.HSS=self.client.servers['Hardware Simulating Server']
			
            yield self.HSS.signal__device_added(8675311)
            yield self.HSS.signal__device_removed(8675312)
            yield self.HSS.addListener(listener=self.simDeviceAdded,source = None,ID=8675311)
            yield self.HSS.addListener(listener=self.simDeviceRemoved, source=None, ID=8675312)
            default_session=self.rm_sim.session
            self.rm_sim.visalib.set_attribute(default_session,'ser',self.HSS)
            
    # SIGNALS
    @inlineCallbacks
    def serverDisconnected(self, ID, name):
        if name=='Hardware Simulating Server':
            self.sim_addresses.clear() #all sim addresses removed
            yield self.HSS.removeListener(listener=self.simDeviceAdded,source = None,ID=8675311)
            yield self.HSS.removeListener(listener=self.simDeviceRemoved, source=None, ID=8675312)
            self.HSS=None
     
     
    #see settings with same names in SBS
    @setting(71, 'Add Simulated Device', address='i', device_type='s',returns='')
    def add_simulated_device(self, c, address,device_type):
        if self.HSS:
            yield self.HSS.add_device(self.name,address,device_type,True)
        
    @setting(72, 'Remove Simulated Device', address='i', returns='')
    def remove_simulated_device(self, c, address):
        if self.HSS:
            yield self.HSS.remove_device(self.name,address)


    def simDeviceAdded(self, c,data):
        node, address=data
        if node==self.name:
            self.sim_addresses.append(address)
            
    def simDeviceRemoved(self, c, data):
        node, address=data
        if node==self.name:
            self.sim_addresses.remove(address)
   
   
__server__ = GPIBBusServer()

if __name__ == '__main__':
    from labrad import util
    util.runServer(__server__)
