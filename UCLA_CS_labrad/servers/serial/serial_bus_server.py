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
from twisted.internet.defer import inlineCallbacks, returnValue, DeferredLock

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
        
        active_device_connections=[]
        def __init__(self, hss, node, name,context):
            
            if name in self.active_device_connections:
                raise Error()
                
            self.name=name
            self.ctxt=context
            self.ser=hss
            self.input_buffer=bytearray(b'')
            
            
            self.open= lambda: self.ser.select_device(node, int(self.name[-1]), context=self.ctxt)
            self.reset_output_buffer= lambda: self.ser.reset_output_buffer(context=self.ctxt)
            
            
            self.set_buffer_size= lambda size: self.ser.set_buffer_size(context=self.ctxt)
            
            
                
            self.buff_lock=DeferredLock()
            self.active_device_connections.append(self.name)
            if self.ser:
                self.open()
                

          
        def reset_input_buffer(self):
            self.input_buffer=bytearray()
            
        @inlineCallbacks
        def break_connection(self):
            if self.name in self.active_device_connections:
                self.active_device_connections.remove(self.name)
            if self.ser:
                yield self.ser.deselect_device(context=self.ctxt)
 
        @inlineCallbacks
        def close(self):
            yield self.break_connection()
         
        @property
        def in_waiting(self):
            return len(self.input_buffer)

        @property
        def out_waiting(self):
            return self.ser.get_out_waiting(context=self.ctxt)
            

        def read(self,byte_count):
            if not self.buff_lock.locked:
                self.buff_lock.acquire()
                resp,rest=self.input_buffer[:byte_count],self.input_buffer[byte_count:]
                self.input_buffer=rest
                self.buff_lock.release()
                return bytes(resp)
            else:
                return b''
        
        def write(self,data):
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

        @property
        def baudrate(self):
            return self.ser.baudrate(None,context=self.ctxt)


             
        @baudrate.setter
        def baudrate(self, val):
            self.ser.baudrate(val,context=self.ctxt)

            
                
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
            return self.ser.stopbits(val,context=self.ctxt)
             
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
        if 'CS Hardware Simulating Server' in [HSS_name for _,HSS_name in servers]:
            self.HSS=self.client.servers['CS Hardware Simulating Server']
            yield self.HSS.signal__device_added(8675309)
            yield self.HSS.signal__device_removed(8675310)
            yield self.HSS.addListener(listener=self.simDeviceAdded,source = None,ID=8675309)
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
                self.SerialPorts.append(SerialDevice(dev_name,dev_path,None))
            
        for d in self.sim_dev_list:
            try:
                ser = self.DeviceConnection(None,self.name,d,None)
                ser.close()
            except:
                pass
                
                
            else:
                self.SerialPorts.append(SerialDevice(d,None,self.HSS))
                

        port_list_tmp = [x.name for x in self.SerialPorts]
        self.port_update(self.name, port_list_tmp)


    def expireContext(self, c):
        if 'PortObject' in c:
            yield c['PortObject'].close()
            
    def getPort(self,c):
        if not c['PortObject']:
            raise Error()
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
        if serial_device.HSS:
            return self.DeviceConnection(serial_device.HSS,self.name,serial_device.name,self.client.context())
        else:
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
        return int(resp)
    
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
        if self.HSS:
            yield self.HSS.add_device(self.name,port,device_type,False)
        
    @setting(72, 'Remove Simulated Device', port='i', returns='')
    def remove_simulated_device(self, c, port):
        if self.HSS:
            yield self.HSS.remove_device(self.name,port)


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
            self.HSS=self.client.servers['CS Hardware Simulating Server']
            yield self.HSS.signal__device_added(8675309)
            yield self.HSS.signal__device_removed(8675310)
            yield self.HSS.addListener(listener=self.simDeviceAdded,source = None,ID=8675309)
            yield self.HSS.addListener(listener=self.simDeviceRemoved, source=None, ID=8675310)
            
    # SIGNALS
    @inlineCallbacks
    def serverDisconnected(self, ID, name):
        if name=='CS Hardware Simulating Server':
            self.sim_dev_list=[]
            yield self.HSS.removeListener(listener=self.simDeviceAdded,source = None,ID=8675309)
            yield self.HSS.removeListener(listener=self.simDeviceRemoved, source=None, ID=8675310)
            self.HSS=None
            for ctxt_dict in [ctxt.data for ctxt in self.contexts.values()]:
                port_obj=ctxt_dict['PortObject']
                if not port_obj:
                    continue
                elif isinstance(port_obj,self.DeviceConnection):
                    port_obj.break_connection()
        
    
        


    def simDeviceAdded(self, c,data):
        node, port=data
        cli=self.client
        if node==self.name:
            self.sim_dev_list.append("SIMCOM"+str(port))

   
   
    def simDeviceRemoved(self, c, data):
        node, port=data
        if node==self.name:
            self.sim_dev_list.remove("SIMCOM"+str(port))
            for ctxt_dict in [ctxt.data for ctxt in self.contexts.values()]:
                port_obj=ctxt_dict['PortObject']
                if not port_obj:
                    continue
                elif isinstance(port_obj,self.DeviceConnection) and port_obj.name=="SIMCOM"+str(port):
                    port_obj.break_connection()
                    break
                    
        
   
   
   
__server__ = CSSerialServer()

if __name__ == '__main__':
    from labrad import util
    util.runServer(__server__)
