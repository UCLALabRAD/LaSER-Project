"""
### BEGIN NODE INFO
[info]
name = CS Serial Server
version = 1.5.1
description = Gives access to serial devices via pyserial.
instancename = %LABRADNODE% CS Serial Server

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
from twisted.internet.defer import inlineCallbacks, returnValue

from serial import Serial
from serial.tools import list_ports
from serial.serialutil import SerialException

from UCLA_CS_labrad.servers import CSPollingServer


SerialDevice = collections.namedtuple('SerialDevice', ['name', 'devicepath', 'HSS'])
PORTSIGNAL = 539410



class CSSerialServer(CSPollingServer):
    """
    Provides access to a computer's serial (COM) ports.
    """

    name = '%LABRADNODE% CS Serial Server'
    POLL_ON_STARTUP = True
    port_update = Signal(PORTSIGNAL, 'signal: port update', '(s,*s)')


    class DeviceConnection(object):
        """
        Wrapper for our server's client connection to the serial server.
        @raise labrad.types.Error: Error in opening serial connection
        """
        def __init__(self, hss, node, port):
        
        
            self.name="Simulated Device at Node " node ", Port "+ port
            
            self.timeout=1
			
			self.open= lambda: hss.select_device(node, port)
			
			self.open()
            

			
			self.close = lambda: hss.deselect_device(node)
            
            self.reset_input_buffer= lambda: hss.reset_input_buffer
            self.reset_output_buffer= lambda: hss.reset_output_buffer
            
            
            self.set_buffer_size= lambda size: None
            
			

            
            
            
        @property
        @inlineCallbacks
        def in_waiting(self):
            val= yield self.ser.get_in_waiting(context=self.ctxt)
            returnValue(val)

        @property
        @inlineCallbacks
        def out_waiting(self):
            val= yield self.ser.get_out_waiting(context=self.ctxt)
            returnValue(val)
            
        @inlineCallbacks
        def read(self,bytes):
            resp= yield self.ser.read(bytes, context=self.ctxt)
            returnValue(resp.encode())
                
        @inlineCallbacks
        def write(self,data):
            yield self.ser.write(data, context=self.ctxt)


        @property
        @inlineCallbacks
        def baudrate(self):
            resp=yield self.ser.baudrate(None,context=self.ctxt)
            returnValue(resp)
             
        @baudrate.setter
        @inlineCallbacks
        def baudrate(self, val):
            yield self.ser.baudrate(val, context=self.ctxt)
            
                
        @property
        @inlineCallbacks
        def bytesize(self):
            resp=yield self.ser.bytesize(None, context=self.ctxt)
            returnValue(resp)
                
                
        @bytesize.setter
        @inlineCallbacks
        def bytesize(self, val):
            yield self.ser.bytesize(val, context=self.ctxt)

        @property
        @inlineCallbacks
        def parity(self):
            resp=yield self.ser.parity(None, context=self.ctxt)
            returnValue(resp)
                
                
        @parity.setter
        @inlineCallbacks
        def parity(self, val):
            yield self.ser.parity(val, context=self.ctxt)


        @property
        @inlineCallbacks
        def stopbits(self):
            resp=yield self.ser.stopbits(None, context=self.ctxt)
            returnValue(resp)
                
        @stopbits.setter
        @inlineCallbacks
        def stopbits(self, val):
            yield self.ser.stopbits(val, context=self.ctxt)
             
        @property
        def dtr(self):
            pass

        
        @dtr.setter
        @inlineCallbacks
        def dtr(self, val):
            yield self.ser.dtr(val, context=self.ctxt)

        
        @property
        def rts(self):
            pass

        @rts.setter
        @inlineCallbacks
        def rts(self, val):
            yield self.ser.rts(val, context=self.ctxt)
                




    @inlineCallbacks
    def initServer(self):
        super().initServer()
        self.sim_devices=[]
        servers=yield self.client.manager.servers()
		if 'CS Hardware Simulating Server' in [HSS_name for _,HSS_name in servers]:
			HSS=self.client.servers['CS Hardware Simulating Server']
            existing_device_list=yield HSS.get_devices_list(self.name)
            self.sim_devices+=[SerialDevice(port,HSS) for port in existing_device_list]
            yield HSS.signal__simulated_device_added(8675309)
            yield HSS.signal__simulated_device_removed(8675310)
            yield HSS.addListener(listener=self.simDeviceAdded,source = None,ID=8675309)
            yield HSS.addListener(listener=self.simDeviceRemoved, source=None, ID=8675310)
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

        dev_list = list_ports.comports()
        not_in_use_dev_list=[]
        in_use_port_list=[context_obj.data['PortObject'].port  for context_obj in self.contexts.values() if (('PortObject' in context_obj.data) and context_obj.data['PortObject'])]
        #print(in_use_port_list)
        for dev in dev_list:
            #print(dev[0])
            if dev[0] not in in_use_port_list:
                not_in_use_dev_list.append(dev)
        connected_phys_devices=[]
        for d in not_in_use_dev_list:
            dev_path = d[0]
            try:
                ser = Serial(dev_path)
                ser.close()
            except SerialException as e:
                pass
            else:
                _, _, dev_name = dev_path.rpartition(os.sep)
                connected_phys_devices.append(SerialDevice(dev_name,dev_path,None))
        # send out signal
        self.SerialPorts=connected_phys_devices+[dev for dev in self.sim_devices if dev.name not in in_use_port_list]
        port_list_tmp = [x.name for x in self.SerialPorts]
        self.port_update(self.name, port_list_tmp)

    def expireContext(self, c):
        if 'PortObject' in c:
            yield c['PortObject'].close()
            
    def getPort(self,c):
        try:
            port_obj=c['PortObject']
            #would be nice to do a dummy write or read here so we can handle an error right here if device was "unplugged"
            return c['PortObject']
        except Exception as e:
            raise Error(code=3,msg=e.message)
            
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
        
        if 'PortObject' in c:
            yield c['PortObject'].close()
            del c['PortObject']
            
        for x in self.SerialPorts:
            if os.path.normcase(x.name) == os.path.normcase(port) or x.name==port:
                    try:
                        c['PortObject'] = yield self.create_serial_connection(x)
                        returnValue(x.name)

                    except SerialException as e:
                        if e.message.find('cannot find') >= 0:
                            raise Error(code=1, msg=e.message)
                        else:
                            raise Error(code=3, msg=e.message)
                            
                    except SimSerialDeviceError as e:
                        raise Error(code=2, msg=e.message) #should this be combined with error code 3?

        raise Error(code=1, msg='Unknown port %s' % (port,))

    
    
    @setting(11, 'Close Port', returns='')
    def close(self, c):
        """
        Closes the current serial port.
        """
        if 'PortObject' in c:
            yield c['PortObject'].close()
            del c['PortObject']

    



    def create_serial_connection(self,serial_device):
        if serial_device.HSS:
            return self.DeviceConnection(serial_device.HSS,serial_device.name)
        else:
            return Serial(serial_device.devicepath, timeout=0)
                


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
        resp.addCallback(lambda x: int(x))
        return resp
        
    @setting(34, 'Stopbits', data=[': Query current stopbits', 'w: Set stopbits'], returns='w: Selected stopbits')
    def stopbits(self, c, data=None):
        """
        Sets the number of stop bits.
        """
        ser = self.getPort(c)

        if data:
            ser.stopbits=data
        resp.addCallback(lambda x: int(x))
        return resp
        
        
    @setting(35, 'Timeout', data=[': Return immediately', 'v[s]: Timeout to use (max: 5min)'],
             returns=['v[s]: Timeout being used (0 for immediate return)'])
    def timeout(self, c, data=Value(0, 's')):
        """
        Sets a timeout for read operations.
        """
        ser = self.getPort(c)
        timeout_val=min(data['s'], 300)
        ser.timeout=timeout_val
        return Value(ser.timeout, 's')


    # FLOW CONTROL
    @setting(37, 'RTS', data=['b'], returns=['b'])
    def RTS(self, c, data):
        """
        Sets the state of the RTS line.
        """
        ser = self.getPort(c)
        ser.rts=int(data)
        return data

    @setting(38, 'DTR', data=['b'], returns=['b'])
    def DTR(self, c, data):
        """
        Sets the state of the DTR line.
        """
        ser = self.getPort(c)
        ser.dtr=int(data)
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
        yield ser.write(data)

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
        yield ser.write(data)

        return int(len(data))

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
        
        @inlineCallbacks
        def doRead(count):
            """
            Waits until it reads <count> characters or is told to stop.
            """
            d = b''
            while not killit:
                d = yield ser.read(count)
                if d:
                    break
                time.sleep(0.001)
            returnValue(d)
        
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
            r = yield ser.read(count)

        returnValue(r)

    @inlineCallbacks
    def readSome(self, c, count=0):
    
        ser = self.getPort(c)
        if count == 0:
            resp=yield ser.read(10000)
            returnValue(resp)

        timeout = ser.timeout
        if timeout == 0:
            resp=yield ser.read(count)
            returnValue(resp)
            

        # read until we either hit timeout or meet character count
        recd = b''
        while len(recd) < count:
            # try to read remaining characters
            r = yield ser.read(count - len(recd))
            # if nothing, keep reading until timeout
            if r == b'':
                r = yield self.deferredRead(ser, timeout, count - len(recd))
                if r == b'':
                    yield ser.close()
                    yield ser.open()
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
        timeout = ser.timeout
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
            r = yield ser.read(1)
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
        yield ser.reset_input_buffer()

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
        val = ser.out_waiting
        return val

    @setting(71, 'Add Simulated Device', port='s', returns='')
    def add_simulated_device(self, c, port,device_type):
        servers=yield self.client.manager.servers()
		if 'CS Hardware Simulating Server' in [HSS_name for _,HSS_name in servers]:
			HSS=self.client.servers['CS Hardware Simulating Server']
            yield HSS.add_simulated_device(self.name,port,device_type)
        
    @setting(72, 'Remove Simulated Device', port='s', returns='')
    def remove_simulated_device(self, c, port):
        servers=yield self.client.manager.servers()
		if 'CS Hardware Simulating Server' in [HSS_name for _,HSS_name in servers]:
			HSS=self.client.servers['CS Hardware Simulating Server']
            yield HSS.remove_simulated_device(self.name,port)    


    # SIGNALS
    @inlineCallbacks
    def serverConnected(self, ID, name):
        """
        Attempt to connect to last connected serial bus server upon server connection.
        """
        # check if we aren't connected to a device, port and node are fully specified,
        # and connected server is the required serial bus server
		if name=='CS Hardware Simulating Server':
			yield self.client.refresh()
			HSS=self.client.servers['CS Hardware Simulating Server']
            yield HSS.signal__simulated_device_added(8675309)
            yield HSS.signal__simulated_device_removed(8675310)
            yield HSS.addListener(listener=self.simDeviceAdded,source = None,ID=8675309)
            yield HSS.addListener(listener=self.simDeviceRemoved, source=None, ID=8675310)
            
    # SIGNALS
    def serverDisconnected(self, ID, name):
		if name=='CS Hardware Simulating Server':
            self.sim_devices=[]
        
            
    


    def simDeviceAdded(self, c,data):
        node, port=data
        cli=self.client
        if node==self.name:
            HSS=cli.servers['CS Hardware Simulating Server']
            self.sim_devices.append(SerialDevice(port,None, HSS()))
   
   
    def simDeviceRemoved(self, c, data):
		node, port=data
        if node==self.name:
			for device in self.sim_devices:
				if device.name==port:
					self.sim_devices.remove(device)
					break
   
   
   
__server__ = CSSerialServer()

if __name__ == '__main__':
    from labrad import util
    util.runServer(__server__)
