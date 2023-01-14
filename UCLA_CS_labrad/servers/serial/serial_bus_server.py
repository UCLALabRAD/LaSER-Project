"""
### BEGIN NODE INFO
[info]
name = Serial Server
version = 1.5.1
description = Gives access to serial devices via pyserial.
instancename = %LABRADNODE% Serial Server

[startup]
cmdline = %PYTHON% %FILE%
timeout = 20

[shutdown]
message = 987654321
timeout = 20
### END NODE INFO
"""
import os
import time
import collections

from labrad.units import Value
from labrad.errors import Error
from labrad.server import setting, Signal
from twisted.internet import reactor, threads
from twisted.internet.task import deferLater
from twisted.internet.defer import inlineCallbacks, returnValue, DeferredLock

from serial import Serial
from serial.tools import list_ports
from serial.serialutil import SerialException

from UCLA_CS_labrad.servers import PollingServer


SerialDevice = collections.namedtuple('SerialDevice', ['name', 'devicepath', 'HSS'])
PORTSIGNAL = 539410

class NoPortSelectedError(Error):
    """
    Please open a port first.
    """
    code = 1


class SerialServer(PollingServer):
    """
    Provides access to a computer's serial (COM) ports.
    """

    name = '%LABRADNODE% Serial Server'
    POLL_ON_STARTUP = True
    port_update = Signal(PORTSIGNAL, 'signal: port update', '(s,*s)')


    #TODO: Rename to SimulatedPort. This is our HSS-communicating object that mimics a Serial object.
    class DeviceConnection(object):
        
        active_device_connections=[]
        def __init__(self, hss, node, name,context):
            
            if name in self.active_device_connections: #this list is shared across all SimulatedPorts. If different client has already selected simulated device, it will be in this list and can't make new connection to it
                raise Error()
                
            self.name=name
            
            
            self.ctxt=context
            self.ser=hss #server wrapper for HSS,
            self.input_buffer=bytearray(b'')
            self.error_list=[]
            self.node=node
            self.is_broken=False #device has been removed from HSS, or HSS stopped running. this connection cannot be opened again.
            self.is_closed=False #device connection has been closed, but another client can connect to it still
            self.reset_output_buffer= lambda: self.ser.reset_output_buffer(context=self.ctxt)
            
            self.get_error_list=lambda: self.ser.get_device_error_list(context=self.ctxt)
            self.set_buffer_size= lambda size: self.ser.set_buffer_size(context=self.ctxt)
            
            
                
            self.buff_lock=DeferredLock()
            

            self.open()
                

          
        def reset_input_buffer(self):
            self.input_buffer=bytearray()
        
        def open(self):
            self.active_device_connections.append(self.name) #this list is shared across all SimulatedPorts. add this port to list so no other clients can make a simulatedport connection to the simulated device at this port
            if not self.is_broken and self.ser: #makes it so connection can't be opened again when broken
                self.ser.select_device(self.node, int(self.name[-1]), context=self.ctxt) #see create_serial_connection
                self.is_closed=False
                
                

        def break_connection(self):
            self.is_broken=True
            self.close()
 

        def close(self):
            if self.name in self.active_device_connections:
                self.active_device_connections.remove(self.name) #make device available to clients again if it still exists. otherwise, make it so clients are able to connect to a new device plugged in at this device's former simulated location
            if self.ser:
                self.ser.deselect_device(context=self.ctxt)
            self.is_closed=True
         
         
        @property
        def in_waiting(self):
            return len(self.input_buffer)

        
        @property
        def out_waiting(self):
            return self.ser.get_out_waiting(context=self.ctxt)
            
      
        #There’s a big bold warning in the Twisted documentation that basically says not to use Deferred/callback logic inside a function passed to deferToThread.
        #This means that the separate thread that executes deferredRead to use the client’s port object to check the port’s input buffer for available bytes,
        #cannot ever make requests to the HSS if the client has a SimulatedPort-but deferredRead clearly calls the read method of the client’s port object.
        #So the read method of our SimulatedPort cannot check for bytes in its device’s SerialCommunicationWrapper’s input_buffer in the HSS! Instead, we have our SimulatedPort’s
        #write method make a write request to the HSS, which the HSS will respond to only when the selected device’s full output is ready in its SerialCommunicationWrapper’s
        #input_buffer, and then attach callbacks to the returned Deferred instead of yielding. The first callback would be a read request to the HSS asking for the full
        #contents of that input buffer. The input buffer will always be ready by the time the read request is handled because requests from the same context ID are always
        #handled in order. The next callback would add the data from the full read to an input_buffer stored in the SimulatedPort object. Then, we do not yield or return
        #this Deferred, so it does not end up being returned by the setting (which instead just returns the length of the data the client provided as an argument when making
        #the read request). Thus, the effect is that since the Deferred was created in the reactor thread, its callback chain will be scheduled as a task when it fires, but
        #since the setting did not return it, the SBS will respond to the write request immediately. Thus, the bytes the device output  eventually show up in the
        #client’s SimulatedPort’s input_buffer, but the client can move on, just like with a real device! The only difference would be that all the bytes the device
        #output corresponding to each write operation would show up in the SimulatedPort’s input_buffer as a group. To implement the read method for our SimulatedPort, we
        # act exactly like the real Serial object (with the timeout of 0) does- just look at the byte count in the argument and immediately grab
        #from the SimulatedPort’s input_buffer the minimum between that amount or the full input_buffer, and since it’s on the SBS side no Deferreds are involved!
        def read(self,byte_count):
            if self.is_closed:
                raise Error()
            if not self.buff_lock.locked:
                self.buff_lock.acquire()
                resp,rest=self.input_buffer[:byte_count],self.input_buffer[byte_count:]
                self.input_buffer=rest
                self.buff_lock.release()
                return bytes(resp)
            else:
                return b''
        
        
        def write(self,data):
            if self.is_closed:
                raise Error()
            self.ser.simulated_write(data,context=self.ctxt)
            d=self.ser.simulated_read(context=self.ctxt)
            d.addCallback(lambda x: x.encode())
            d.addCallback(self.addtoBuffer)
            #print(int(len(data)))
            #return int(len(data))
            
        @inlineCallbacks
        def addtoBuffer(self,data):
            yield self.buff_lock.acquire()
            #print(data)
            self.input_buffer.extend(data)
            #print(self.input_buffer)
            self.buff_lock.release()
           
           
           
         #baudrate is a property of the Serial object, not one of its methods, so the client’s argument is assigned to the Serial object’s baudrate
         #property instead of being passed into a function. This poses a problem because in our SimulatedPort, baudrate needs to be a function,
         #because it needs to make a request to the HSS to change the simulated device’s SerialCommunicationWrapper’s baudrate. Fortunately, the
         #Python property decorator exists to help out programmers who find themselves in this dilemma. To use this decorator, we have to write two
         #methods in the SimulatedPort object, one having no arguments and being decorated as a “baudrate property getter” and the other having one
         #argument and being decorated as a “baudrate property setter”. This makes it so that if somebody tries to access baudrate as a property of
         #the object, the getter function is secretly called and its return value is what the attempt to get the “property” gives.
         #Similarly, if someone tries to set the object’s baudrate property, the value they try to set it to is secretly passed to the
         #setter as its argument, and the setter is executed. This is one of those areas, however, where using inlineCallbacks and
         #keeping the real-hardware-communication code intact clashed. Essentially, the Python interpreter does not allow one to write yield ser.baudrate=x or
         #x=yield ser.baudrate, giving a syntax error for each. Fortunately, our knowledge of how servers treat context IDs and how parallelization
         #works in LabRAD saves us here- we will not use inlineCallbacks. When the setting sets the baudrate property of the client’s SimulatedPort,
         #the  SimulatedPort makes a request to the HSS to set the selected device’s SerialCommunicationWrapper’s baudrate, which returns a Deferred.
         #We know this Deferred will fire with a value of None, which we don’t care about. We do not yield or return this Deferred.
         #Next, when the setting gets the baudrate “property” of the client’s port, the SimulatedPort makes a request to the HSS to get the simulated device’s
         #SerialCommunicationWrapper’s baudrate, which returns a Deferred that will eventually fire with that baudrate value. This we do care about,
         #so the SimulatedPort’s baudrate getter returns it- based on how the property decorator works, this means getting the SimulatedPort’s b
         #audrate “property” returns this Deferred. The baudrate SBS setting returns the client’s port object’s baudrate property, so it returns the
         #Deferred. Because requests from the same context ID are always handled in order, the HSS will completely finish setting the simulated d
         #evice’s baudrate and respond to the SimulatedPort before it accepts the next request from the SimulatedPort to get the baudrate. Because the
         #baudrate SBS setting returned a Deferred, a new task is scheduled with the SBS’ reactor to return the baudrate value of the selected port’s d
         #evice’s SerialCommunicationWrapper when the HSS responds to the request to get the baudrate and the Deferred fires.

        @property
        def baudrate(self):
            return self.ser.baudrate(None,context=self.ctxt)


             
        @baudrate.setter
        def baudrate(self, val):
            self.ser.baudrate(val,context=self.ctxt)

            
        #same idea for  all serial communication parameters
        @property
        def bytesize(self):
            return self.ser.bytesize(None,context=self.ctxt)


                
        @bytesize.setter
        def bytesize(self, val):
            self.ser.bytesize(val,context=self.ctxt)

        @property
        def parity(self):
            return self.ser.bytesize(None,context=self.ctxt)

                
                
        @parity.setter
        def parity(self, val):
            self.ser.parity(val,context=self.ctxt)


        @property
        def stopbits(self):
            return self.ser.stopbits(None,context=self.ctxt)
            
      
                
        @stopbits.setter
        def stopbits(self, val):
            self.ser.stopbits(val,context=self.ctxt)
             
        @property
        def dtr(self):
            pass

        
        @dtr.setter
        def dtr(self, val):
            self.ser.dtr(val,context=self.ctxt)

        
        @property
        def rts(self):
            pass

        @rts.setter
        def rts(self, val):
            self.ser.rts(val,context=self.ctxt)
               



               
    def initContext(self,c):
        c['PortObject']=None
        
        
    @inlineCallbacks
    def initServer(self):
        super().initServer()
        self.HSS=None
        self.sim_dev_list=[]
        servers=yield self.client.manager.servers()
        
        #case where HSS already running
        if 'Hardware Simulation Server' in [HSS_name for _,HSS_name in servers]:
            self.HSS=self.client.servers['Hardware Simulation Server']
            #Serial Bus Servers subscribe to two types of LabRAD Signals of Hardware Simulation Server (HSS) while booting up: device addition and device removal LabRAD Signals.
            yield self.HSS.signal__device_added(8675309)
            yield self.HSS.signal__device_removed(8675310)
            yield self.HSS.addListener(listener=self.simDeviceAdded,source = None,ID=8675309) #assign Signal handlers
            yield self.HSS.addListener(listener=self.simDeviceRemoved, source=None, ID=8675310)
        self.enumerate_serial_pyserial()
        

    def _poll(self):
        self.enumerate_serial_pyserial()

    def enumerate_serial_pyserial(self):
        """
        This uses the pyserial built-in device enumeration.

        We ignore the pyserial "human readable" device name
        because that appears to make no sense.  For instance, a
        particular FTDI USB-Serial adapter shows up as 'Microsoft
        Corp. Optical Mouse 200'.

        Following the example from the above windows version, we try to open
        each port and ignore it if we can't.
        """
        self.SerialPorts=[]      
        phys_dev_list = list_ports.comports()
        for d in phys_dev_list:
            dev_path = d[0]
            try:
                ser = Serial(dev_path)
                ser.close()
            except SerialException as e:
                pass
            else:
                _, _, dev_name = dev_path.rpartition(os.sep)
                self.SerialPorts.append(SerialDevice(dev_name,dev_path,None)) #no HSS  since serial device (acts as flag indicating real device)
            
        for d in self.sim_dev_list:
            try:
                ser = self.DeviceConnection(None,self.name,d,None) #try to make SimulatedPort object for simulated port (a.k.a. "open Serial Port").
                ser.close() #succeeded, so close and go to else branch
            except:
                pass #failed, so a different client already selected the device
                
                
            else:
                self.SerialPorts.append(SerialDevice(d,None,self.HSS)) #make SerialDevice object and add to serial ports list
                

        port_list_tmp = [x.name for x in self.SerialPorts]
        self.port_update(self.name, port_list_tmp)


    def expireContext(self, c):
        if 'PortObject' in c:
            yield c['PortObject'].close()
            
    def getPort(self,c):
        if not c['PortObject']:
            raise NoPortSelectedError()
        return c['PortObject']
            
#Get Information About Ports
    @setting(10, 'List Serial Ports', returns='*s: List of serial ports')
    def list_serial_ports(self, c):
        """
        Retrieves a list of all serial ports.
        NOTES:
        This list contains all ports installed on the computer,
        including ones that are already in use by other programs.
        """
        port_list = [x.name for x in self.SerialPorts]
        return port_list
       




    # PORT CONNECTION
    @setting(21, 'Open', port='s: Port to open, e.g. COM4',
             returns='s: device_id of initial device')
    def open(self, c, port):
        """
        Opens a serial port in the current context.

        args:
        port   device name as returned by list_serial_ports.

        On windows, the device name will generally be of the form
        COM1 or COM42 (i.e., without the device prefix \\\\.\\).  On
        linux, it will be the device node name (ttyUSB0) without the
        /dev/ prefix.  This is case insensitive on windows, case sensitive
        on Linux.  For compatibility, always use the same case.
        """
        c['Timeout'] = 0
        if 'PortObject' in c and c['PortObject']:
            yield c['PortObject'].close()
            c['PortObject']=None
            
        for x in self.SerialPorts:
            if os.path.normcase(x.name) == os.path.normcase(port) or x.name==port:
                    try:
                        c['PortObject'] = self.create_serial_connection(x)
                        return x.name

                    except SerialException as e:
                        if e.message.find('cannot find') >= 0:
                            raise Error(code=1, msg=e.message)
                        else:
                            raise Error(code=3, msg=e.message) 
        raise Error(code=1, msg='Unknown port %s' % (port))

    
    
    @setting(11, 'Close Port', returns='')
    def close(self, c):
        """
        Closes the current serial port.
        """
        if c['PortObject']:
            yield c['PortObject'].close()
            c['PortObject']=None

    


   
    def create_serial_connection(self,serial_device):
        if serial_device.HSS: #simulated port
        
            #During instantiation of the SimulatedPort object during the port-opening process, we could have the SBS generate a new context ID (client),
            #store that context ID as an object variable in the SimulatedPort, and make a select_simulated_device request to the HSS to select
            #the SimulatedPort’s corresponding simulated device, passing that new context ID. Then, any other HSS requests made in that SimulatedPort
            #just need to pass that stored context ID! Each SBS client in each SBS is now a different client from the perspective of the HSS,
            #each having their own context ID and dictionary.
            return self.DeviceConnection(serial_device.HSS,self.name,serial_device.name,self.client.context())
        else:
        
            #real port
            return Serial(serial_device.devicepath, timeout=0,exclusive=True)
                


    # CONNECTION PARAMETERS
    @setting(31, 'Baudrate', data=[': Query current baudrate', 'w: Set baudrate'], returns='w: Selected baudrate')
    def baudrate(self, c, data=None):
        """
        Sets the baudrate.
        """
        ser = self.getPort(c)
        if data:
            ser.baudrate=data
        resp= ser.baudrate
        return resp
    
    @setting(32, 'Bytesize', data=[': Query current bytesize', 'w: Set bytesize'], returns='w: Selected bytesize')
    def bytesize(self, c, data=None):
        """
        Sets the bytesize.
        """
        ser = self.getPort(c)

        if data:
            ser.bytesize=data
        resp= ser.bytesize
        return resp
        
    @setting(33, 'Parity', data=[': Query current parity', 'w: Set parity'], returns='w: Selected parity')
    def parity(self, c, data=None):
        """
        Sets the parity.
        """
        ser = self.getPort(c)

        if data:
            ser.parity=data
        resp= ser.parity
        return resp
        
    @setting(34, 'Stopbits', data=[': Query current stopbits', 'w: Set stopbits'], returns='w: Selected stopbits')
    def stopbits(self, c, data=None):
        """
        Sets the number of stop bits.
        """
        ser = self.getPort(c)

        if data:
            ser.stopbits=data
        resp=ser.stopbits
        return resp
        
        
    @setting(35, 'Timeout', data=[': Return immediately', 'v[s]: Timeout to use (max: 5min)'],
             returns=['v[s]: Timeout being used (0 for immediate return)'])
    def timeout(self, c, data=Value(0, 's')):
        """
        Sets a timeout for read operations.
        """
        c['Timeout'] = min(data['s'], 300)
        return Value(c['Timeout'], 's')


    # FLOW CONTROL
    @setting(37, 'RTS', data=['b'], returns=['b'])
    def RTS(self, c, data):
        """
        Sets the state of the RTS line.
        """
        ser = self.getPort(c)
        ser.rts=data
        return data

    @setting(38, 'DTR', data=['b'], returns=['b'])
    def DTR(self, c, data):
        """
        Sets the state of the DTR line.
        """
        ser = self.getPort(c)
        ser.dtr=data
        return data


    # WRITE
    @setting(41, 'Write', data=['s: Data to send', '*w: Byte-data to send'],
             returns=['w: Bytes sent'])
    def write(self, c, data):
        """
        Sends data over the port.
        """
        
        ser = self.getPort(c)
        # encode as needed
        if type(data) == str:
            data = data.encode()
        ser.write(data)
        
        return int(len(data))

    @setting(42, 'Write Line', data=['s: Data to send'], returns=['w: Bytes sent'])
    def write_line(self, c, data,simulated=None):
        """
        Sends data over the port appending <CR><LF>.
        """
        
        ser = self.getPort(c)
        # encode as needed
        if type(data) == str:
            data = data.encode()
        data += b'\r\n'
        ser.write(data)

        returnValue(int(len(data)))

    @setting(43, 'Pause', duration='v[s]: Time to pause', returns=[])
    def pause(self, c, duration):
        _ = yield deferLater(reactor, duration['s'], lambda: None)
        return


    # READ
    @inlineCallbacks
    def deferredRead(self, ser, timeout, count=1):
        """
        todo: document
        """
        # killit stops the read
        killit = False
        
        def doRead(count):
            """
            Waits until it reads <count> characters or is told to stop.
            """
            d = b''
            while not killit:
                d = ser.read(count)
                if d:
                    break
                time.sleep(0.001)
            return d
        
        # read until the timeout
        
        data = threads.deferToThread(doRead, count)
        timeout_object = []
        start_time = time.time()
        r = yield util.maybeTimeout(data, min(timeout, 300), timeout_object)
        killit = True

        # check if we have timed out
        if r == timeout_object:
            elapsed = time.time() - start_time
            print("deferredRead timed out after {} seconds".format(elapsed))
            r = b''
        if r == b'':
            r = ser.read(count)

        returnValue(r)

    @inlineCallbacks
    def readSome(self, c, count=0):

        ser = self.getPort(c)
        if count == 0:
            resp= ser.read(10000)
            returnValue(resp)

        timeout = c['Timeout']
        if timeout == 0:
            resp= ser.read(count)
            returnValue(resp)
            

        # read until we either hit timeout or meet character count
        recd = b''

        while len(recd) < count:
            # try to read remaining characters
            r = ser.read(count - len(recd))
            # if nothing, keep reading until timeout
            if r == b'':
                r = yield self.deferredRead(ser, timeout, count - len(recd))
                if r == b'':
                    ser.close()
                    ser.open()
                    break
            recd += r
        returnValue(recd)

    @setting(51, 'Read', count=[': Read all bytes in buffer', 'w: Read this many bytes'],
             returns=['s: Received data'])
    def read(self, c, count=0):
        """
        Read data from the port.
        If count = 0, reads the contents of the buffer (non-blocking). Otherwise,
        reads for up to <count> characters or the timeout, whichever is first
        Arguments:
            count:   bytes to read.
        """
        ans = yield self.readSome(c, count)
        
        returnValue(ans)

    @setting(52, 'Read as Words', data=[': Read all bytes in buffer', 'w: Read this many bytes'],
             returns=['*w: Received data'])
    def read_as_words(self, c, data=0):
        """
        Read data from the port.
        """
        ans = yield self.readSome(c, data)
        ans = [int(ord(x)) for x in ans]

        
        ser_name = self.getPort(c).name

        returnValue(ans)

    @setting(53, 'Read Line', data=[': Read until LF, ignoring CRs', 's: Other delimiter to use'],
             returns=['s: Received data'])
    def read_line(self, c, data=''):
        """
        Read data from the port, up to but not including the specified delimiter.
        """
        
        ser = self.getPort(c)
        timeout = c['Timeout']
        # set default end character if not specified
        if data:
            # ensure end character is of type byte
            if type(data) != bytes:
                data = bytes(data, encoding='utf-8')
            delim, skip = data, b''
        else:
            delim, skip = b'\n', b'\r'

        recd = b''
        while True:
            r = ser.read(1)
            # only try a deferred read if there is a timeout
            if r == b'' and timeout > 0:
                r = yield self.deferredRead(ser, timeout)

            # stop if r is empty or the delimiter
            if r in (b'', delim):
                break
            elif r != skip:
                recd += r
            
        returnValue(recd)


    # BUFFER
    @setting(61, 'Flush Input', returns='')
    def flush_input(self, c):
        """
        Flush the input buffer.
        """
        
        ser = self.getPort(c)
        ser.reset_input_buffer()

    @setting(62, 'Flush Output', returns='')
    def flush_output(self, c):
        """
        Flush the output buffer.
        """
        
        ser = self.getPort(c)
        yield ser.reset_output_buffer()

    @setting(63, 'Buffer Size', size='i', returns='')
    def buffer_size(self, c, size):
        """
        Set the serial buffer size.
        Arguments:
            size    (int)   : the serial buffer size.
        """
        ser=self.getPort(c)
        yield ser.set_buffer_size(size)


    @setting(64, 'Buffer Waiting Input', returns='i')
    def input_waiting(self, c):
        """
        Get the number of bytes waiting at the input port.
        Returns:
            (int)   : the number of bytes waiting at the input port.
        """
        
        ser = self.getPort(c)
        val = ser.in_waiting
        return val
        
        
    @setting(65, 'Buffer Waiting Output', returns='i')
    def output_waiting(self, c):
        """
        Get the number of bytes waiting at the output port.
        Returns:
            (int)   : the number of bytes waiting at the output port.
        """
        
        ser = self.getPort(c)
        val = yield ser.out_waiting
        returnValue(val)

    @setting(71, 'Add Simulated Device', port='i', device_type='s',returns='')
    def add_simulated_device(self, c, port,device_type):
    '''
    Indirectly make an add_simulated_device request to the HSS,
    only needing to provide the SimAddress since this server's internal client will automatically use the server’s name in the request.
    
    Arguments:
        port (int): simaddress to add device at on HSS (so if x is provided, device will be added at SIMCOMx on this computer's serial bus)
        device_type (str): simulated instument model to add
    Returns:
        None
    '''
        if self.HSS:
            yield self.HSS.add_device(self.name,port,device_type,False)
            
        
        
    @setting(72, 'Remove Simulated Device', port='i', returns='')
    def remove_simulated_device(self, c, port):
    '''
    Indirectly make an remove_simulated_device request to the HSS,
    only needing to provide the SimAddress since this server's internal client will automatically use the server’s name in the request.
    
    Arguments:
        port (int): simaddress to remove device from on HSS (so if x is provided, device will be removed from SIMCOMx on this computer's serial bus
    Returns:
        None
    '''
        if self.HSS:
            yield self.HSS.remove_device(self.name,port)


    @setting(80, 'Get Device Errors', returns='*(sss)')
    def get_device_errors(self, c):
        ser = self.getPort(c)
        resp=yield ser.get_error_list()
        returnValue(resp)
    
    @setting(81, 'Test restart', returns='')
    def test_restart(self,c):
        ser = self.getPort(c)
        ser.close()
        ser.open()
        
        

    # SIGNALS
    @inlineCallbacks
    def serverConnected(self, ID, name):
        #when we start this SBS the HSS may not have been started yet. so we subscribe to signals here
        if name=='Hardware Simulation Server':
            yield self.client.refresh()
            self.HSS=self.client.servers['Hardware Simulation Server']
            yield self.HSS.signal__device_added(8675309)
            yield self.HSS.signal__device_removed(8675310)
            yield self.HSS.addListener(listener=self.simDeviceAdded,source = None,ID=8675309)
            yield self.HSS.addListener(listener=self.simDeviceRemoved, source=None, ID=8675310)
            
    # SIGNALS
    @inlineCallbacks
    def serverDisconnected(self, ID, name):
        if name=='Hardware Simulation Server':
            self.sim_dev_list=[]
            yield self.HSS.removeListener(listener=self.simDeviceAdded,source = None,ID=8675309)
            yield self.HSS.removeListener(listener=self.simDeviceRemoved, source=None, ID=8675310) #unsubscribe from signals (important so as to not double-subscribe)
            self.HSS=None
            for ctxt_dict in [ctxt.data for ctxt in self.contexts.values()]:
                port_obj=ctxt_dict['PortObject']
                if not port_obj:
                    continue
                elif isinstance(port_obj,self.DeviceConnection):
                    port_obj.ser=None
                    port_obj.break_connection() # break all connections to all simulated devices
        
    
        

    #Handler for "Device Added" LabRAD signal from HSS.
    def simDeviceAdded(self, c,data):
        #data is a two-tuple of form (string, int).
        #the string represents the bus server responsible for the device (based on the computer and which bus on the computer the device is being "plugged into").
        #the int represents the device's SimAddress on the HSS (representing the port the device is "plugged into" on the bus).
        #collectively these make the simulated location of the device on the HSS.
        node, port=data
        cli=self.client
        
        
        #discard any signal about a device being added to a different bus (either a Serial bus on a different computer, or any GPIB bus).
        #But if the server name matches, treat it as being “plugged in” to a new “simulated port” on the serial bus on this computer,
        #treating the SimAddress as a simulated port number.
        if node==self.name:
            #Add this simulated port to this server's simulated serial ports list, which will be polled at the same time as real ports are polled for real devices.
            #To maintain a similar syntax for port names but avoid name clashes between real ports
            #on the bus and simulated ones, we call simulated ports “SIMCOMx” (instead of “COMx” which is used for real ports on Windows) where ‘x’ is the SimAddress. To make things simple,
            #a simulated port lives and dies with the device attached to it; there’s no such thing as a simulated port with no simulated device
            #connected.
            self.sim_dev_list.append("SIMCOM"+str(port))

   
    #Handler for "Device Removed" LabRAD signal from HSS.
    def simDeviceRemoved(self, c, data):
        node, port=data
        if node==self.name:
            #Remove this simulated port from this server's simulated serial ports list, which will be polled at the same time as real ports are polled for real devices.
            self.sim_dev_list.remove("SIMCOM"+str(port))
            
            #find client with the removed device in their context dictionary (the one communicating with the device). there will only be at most one such client
            #since the device disappears from the serial ports list once selected. break the SimulatedPort between the SBS and the HSS, so this client gets an error if they try to continue using the device, and so this simaddress can be used again when a new device is connected at that simulated location.
            for ctxt_dict in [ctxt.data for ctxt in self.contexts.values()]:
                port_obj=ctxt_dict['PortObject']
                if not port_obj:
                    continue
                elif isinstance(port_obj,self.DeviceConnection) and port_obj.name=="SIMCOM"+str(port):
                    port_obj.break_connection()
                    break
                    
    
   
   
   
__server__ = SerialServer()

if __name__ == '__main__':
    from labrad import util
    util.runServer(__server__)
