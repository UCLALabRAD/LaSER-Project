from twisted.internet.defer import returnValue, inlineCallbacks, DeferredLock

from labrad.errors import Error
from labrad.server import LabradServer, setting

__all__ = ["CSSerialDeviceServerSim"]

        
class CSSerialDeviceServerSim(LabradServer):
    """
    Base class for serial device servers.
    
    Contains a number of methods useful for using labrad's serial server.
    Functionality comes from ser attribute, which represents a connection that performs reading and writing to a serial port.
    Subclasses should assign some or all of the following attributes:
    
    name: Something short but descriptive
    port: Name of serial port (Better to look this up in the registry using regKey and getPortFromReg())
    regKey: Short string used to find port name in registry
    serNode: Name of node running desired serial server.  Used to identify correct serial server.
    timeOut: Time to wait for response before giving up.
    """

    # node parameters
    name = 'CSSerialDeviceServerSim'
    port = None
    regKey = None
    serNode = None

    # hardware serial connection parameters
    timeout = None
    baudrate = None
    bytesize = None
    parity = None

    # needed otherwise the whole thing breaks
    ser = None
    
    
    correct_device_check=("id?","piezo")
    
    
    class SerialConnection(object):
        """
        Wrapper for our server's client connection to the serial server.
        @raise labrad.types.Error: Error in opening serial connection
        """
        def __init__(self, ser, port, **kwargs):
        
            
            c['device_id']=ser.open_port(port,**kwargs)
            
            self.ID = ser.ID
            
            
            # serial r/w
            self.write = lambda device_id, s: ser.write(device_id,s)
            self.write_line = lambda device_id, s: ser.write_line(device_id,s)
            self.read = lambda device_id, x = 0: ser.read(device_id, x)
            self.read_line = lambda device_id, x = '': ser.read_line(device_id, x)
            self.read_as_words = lambda device_id, x = 0: ser.read_as_words(device_id, x)
            
            
            # buffer
            self.buffer_size = lambda device_id, size: ser.buffer_size(device_id, size)
            self.buffer_input_waiting = lambda device_id: ser.input_waiting(device_id)
            self.buffer_output_waiting = lambda device_id: ser.out_waiting(device_id)
            self.flush_input = lambda device_id: ser.flush_input(device_id)
            self.flush_output = lambda device_id: ser.flush_output(device_id)
            
            
            # device connection
            self.phys_device_connect=lambda : ser.phys_device_connect
            self.sim_device_connect=lambda device_id: ser.sim_device_connect(device_id)
            self.device_disconnect = lambda ser.device_disconnect(c['device_id'])
            self.get_conn_device_list= lambda: ser.get_conn_device_list
            self.get_all_device_list= lambda: ser.get_all_device_list
            self.close_port= lambda: ser.close_port

            
            self.comm_lock = DeferredLock()
            self.acquire = lambda: self.comm_lock.acquire()
            self.release = lambda: self.comm_lock.release()
            
            
            
            self.timeout=lambda timeout: ser.timeout(timeout)
            self.baudrate=lambda baudrate: ser.baudrate(baudrate)
            self.bytesize=lambda bytesize: ser.bytesize(bytesize)
            self.parity=lambda parity: ser.parity(parity)
            self.debug=lambda debug: ser.debug(debug)
            
            
            
            
            

    # SETUP
    @inlineCallbacks
    def initServer(self):
        # call parent initServer to support further subclassing
        super().initServer()
        # get default node and port from registry (this overrides hard-coded values)
        if self.regKey is not None:
            print('RegKey specified. Looking in registry for default node and port.')
            try:
                node, port = yield self.getPortFromReg(self.regKey)
                self.serNode = node
                self.port = port
            except Exception as e:
                print('Unable to find default node and port in registry. Using hard-coded values if they exist.')
        
        # open connection on startup if default node and port are specified
        if self.serNode:
            print('Default node and port specified. Connecting to device on startup.')
            try:
                serStr = yield self.findSerial(self.serNode)
                yield self.initSerial(serStr, self.port, baudrate=self.baudrate, timeout=self.timeout,
                                      bytesize=self.bytesize, parity=self.parity)
            except Error:



    @inlineCallbacks
    def stopServer(self):
        """
        Close serial connection before exiting.
        """
        super().stopServer()
        if self.ser:
            yield self.ser.acquire()
            self.ser.close()
            self.ser.release()

    @inlineCallbacks
    def getPortFromReg(self, regDir=None):
        """
        Finds default node and port values in
        the registry given the directory name.
        @param regKey: String used to find key match.
        @return: Name of port
        @raise PortRegError: Error code 0.  Registry does not have correct directory structure (['','Ports']).
        @raise PortRegError: Error code 1.  Did not find match.
        """
        reg = self.client.registry
        # There must be a 'Ports' directory at the root of the registry folder
        try:
            tmp = yield reg.cd()
            yield reg.cd(['', 'Servers', regDir])
            node = yield reg.get('default_node')
            port = yield reg.get('default_port')
            yield reg.cd(tmp)
            returnValue((node, port))
        except Exception as e:
            yield reg.cd(tmp)
            if node:
                returnValue((node,None))
            
            


    # SERIAL
    @inlineCallbacks
    def initSerial(self, serStr, port, **kwargs):
        """
        Attempts to initialize a serial connection
        using a given key for the node and port string.
        Sets server's ser attribute if successful.

        @param serStr: Key for serial server
        @param port: Name of port to connect to
        @raise SerialConnectionError: Error code 1.  Raised if we could not create serial connection.
        """
        # set default timeout if not specified
        if kwargs.get('timeout') is None and self.timeout:
            kwargs['timeout'] = self.timeout
        # print connection status
        print('Attempting to connect at:')
        print('\tserver:\t%s' % serStr)
        print('\tport:\t%s' % port)
        print('\ttimeout:\t%s\n\n' % (str(self.timeout) if kwargs.get('timeout') is not None else 'No timeout'))
        # find relevant serial server
        cli = self.client
        try:
            # get server wrapper for serial server
            ser = cli.servers[serStr]
            # instantiate SerialConnection convenience class
            self.ser = self.SerialConnection(ser=ser, port=port, **kwargs)
            # clear input and output buffers
            yield self.ser.flush_input()
            yield self.ser.flush_output()
            print('Serial connection opened.')
        except Error:
            


    @inlineCallbacks
    def findSerial(self, serNode=None):
        """
        Find appropriate serial server.
        @param serNode: Name of labrad node possessing desired serial port
        @return: Key of serial server
        @raise SerialConnectionError: Error code 0.  Could not find desired serial server in registry.
        """
        if not serNode:
            serNode = self.serNode
        cli = self.client
        # look for servers with 'serial' and serNode in the name, take first result
        servers = yield cli.manager.servers()
        try:
            returnValue([i[1] for i in servers if self._matchSerial(serNode, i[1])][0])
        except IndexError:
            raise SerialConnectionError(0)

    @staticmethod
    def _matchSerial(serNode, potMatch):
        """
        Checks if server name is the correct serial server.
        @param serNode: Name of node of desired serial server
        @param potMatch: Server name of potential match
        @return: boolean indicating comparison result
        """
        serMatch = 'serial' in potMatch.lower()
        nodeMatch = serNode.lower() in potMatch.lower()
        return serMatch and nodeMatch


    # SIGNALS
    @inlineCallbacks
    def serverConnected(self, ID, name):
        """
        Attempt to connect to last connected serial bus server upon server connection.
        """
        # check if we aren't connected to a device, port and node are fully specified,
        # and connected server is the required serial bus server
        if (self.ser is None) and (self.serNode is not None) and (self._matchSerial(self.serNode, name)):
            print(name, 'connected after we connected.')
            yield self.port_select(None)

    def serverDisconnected(self, ID, name):
        """
        Close serial device connection (if we are connected).
        """
        if self.ser and self.ser.ID == ID:
            print('Serial bus server disconnected. Relaunch the serial server')
            self.ser = None


    # SETTINGS

    #SELECTING PORT
        
    @setting(11, 'Port Select', node='s', port='s', returns=['', '(ss)'])
    def port_select(self, c, node=None, port=None):
        """
        Attempt to connect to serial device on the given node and port.
        Arguments:
            node    (str)   : the node to connect on
            port    (str)   : the port to connect to
        Returns:
                    (str,str): the connected node and port (empty if no connection)
        """
    
        # do nothing if device is already selected
        if self.ser:
            Exception('A serial device is already opened.')
        # set parameters if specified
        elif (node is not None) and (port is not None):
            self.serNode = node
            self.port = port
        # connect to default values if no arguments at all
        elif ((node is None) and (port is None)) and (self.serNode and self.port):
            pass
        # raise error if only node or port is specified
        else:
            raise Exception('Insufficient arguments.')

        # try to find the serial server and connect to the designated port
        try:
            serStr = yield self.findSerial(self.serNode)
            yield self.initSerial(serStr, self.port, baudrate=self.baudrate, timeout=self.timeout,
                                  bytesize=self.bytesize, parity=self.parity)
        
        except SerialConnectionError as e:
        returnValue((node,port))
        
        
    @setting(12, 'Close Port', returns='')
    def close_port(self, c):
        yield self.ser.acquire()
        self.ser.close_port()
        self.ser.release()
        self.ser=None
        

    @setting(13, 'Port Info', returns='(ss)')
    def port_info(self, c):
        """
        Returns the currently connected serial device's
        node and port.
        Returns:
            (str)   : the node
            (str)   : the port
        """
        
        
        if self.ser:
            return (self.serNode, self.port)
        else:
            return ("", "")
            
    

        
   
    # DIRECT SERIAL COMMUNICATION
    @setting(21, 'Serial Query', data='s', stop=['i: read a given number of characters', 's: read until the given character'], returns='s')
    def serial_query(self, c, data, stop=None):
        """
        Write any string and read the response.
        Args:
            data    (str)   : the data to write to the device
            stop            : the stop parameter (either EOL character or the # of characters to read)
        Returns:
                    (str)   : the device response (stripped of EOL characters)
        """
        yield self.ser.acquire()
        yield self.ser.write(data)
        if stop is None:
            resp = yield self.ser.read()
        elif type(stop) == int:
            resp = yield self.ser.read(stop)
        elif type(stop) == str:
            resp = yield self.ser.read_line(stop)
        self.ser.release()
        returnValue(resp)

    @setting(22, 'Serial Write', data='s', returns='')
    def serial_write(self, c, data):
        """
        Directly write to the serial device.
        Args:
            data    (str)   : the data to write to the device
        """
        yield self.ser.acquire()
        yield self.ser.write(data)
        self.ser.release()

    @setting(23, 'Serial Read', stop=['i: read a given number of characters', 's: read until the given character'], returns='s')
    def serial_read(self, c, stop=None):
        """
        Directly read the serial buffer.
        Returns:
                    (str)   : the device response (stripped of EOL characters)
        """
        yield self.ser.acquire()
        if stop is None:
            resp = yield self.ser.read()
        elif type(stop) == int:
            resp = yield self.ser.read(stop)
        elif type(stop) == str:
            resp = yield self.ser.read_line(stop)
        self.ser.release()
        returnValue(resp)


    # HELPER
    @setting(24, 'Serial Flush', returns='')
    def serial_flush(self, c):
        """
        Flush the serial input and output buffers.
        """
        yield self.ser.acquire()
        yield self.ser.flush_input()
        yield self.ser.flush_output()
        self.ser.release()

    @setting(25, 'Serial Release', returns='')
    def serial_release(self, c):
        """
        Try to release the serial comm lock in case
        we have a problem.
        """
        self.ser.release()


    # DEBUGGING
    @setting(26, 'Serial Debug', status='b', returns='b')
    def serial_debug(self, c, status=None):
        """
        Tells the serial bus server to print input/output.
        """
        return self.ser.debug(status)


#CONNECTING TO DEVICES
    
    
    
    @setting(31,'Connect Physical Device',returns='')
    def phys_device_connect(self, c):
        try:
            yield self.ser.acquire()
            yield self.ser.phys_device_connect()
            self.ser.release()
            c['device_id']='0'
            if timeout is not None: ser.timeout(timeout)
            if baudrate is not None: ser.baudrate(baudrate)
            if bytesize is not None: ser.bytesize(bytesize)
            if parity is not None: ser.parity(parity)
            if debug is not None: ser.serialDebug(debug)
        except:
        #should be in serr conn
        
        
        
    @setting(32, 'Connect Simulated Device', device_id='s', returns='')
    def sim_device_connect(self, c, device_id):
        try:
            yield self.ser.acquire()
            yield self.ser.sim_device_connect(device_id)
            self.ser.release()
            c['device_id']=device_id
            if timeout is not None: ser.timeout(timeout)
            if baudrate is not None: ser.baudrate(baudrate)
            if bytesize is not None: ser.bytesize(bytesize)
            if parity is not None: ser.parity(parity)
            if debug is not None: ser.serial_debug(debug)
        except:
        #should be in serr conn



    @setting(33, 'Disconnect from Currently Selected Device',returns='')
    def device_disconnect(self, c):
        try:
            yield self.ser.acquire()
            yield self.ser.device_disconnect(c)
            self.ser.release()
            c['device_id']=None
        except:
        #should be in serr conn
        
        
        
    @setting(34, 'List Connected Devices', returns='*s')
    def list_conn_devices(self,c):
        yield self.ser.acquire()
        device_list=yield self.ser.get_conn_device_list():
        self.ser.release()
        returnValue(device_list)



    #should be in serr conn
    @setting(35, 'List All Available Devices', returns='*s')
    def list_all_devices(self,c):
        yield self.ser.acquire()
        device_list= yield self.ser.get_all_device_list():
        self.ser.release()
        returnValue(device_list)






#SELECTING DEVICE
    @setting(41,'Select the Physical Device Connected to Port',returns='')
    def select_physical_device(self,c):
        yield self.ser.acquire()
        if device_id in self.ser.get_conn_device_list():
            c['device_id']='0'
        self.ser.release()
    
    
    @setting(42,'Select a Simulated Device in HSS Corresponding to Port',device_id='s',returns='')
    def select_sim_device(self,c,device_id='1'):
        yield self.ser.acquire()
        if device_id in self.ser.get_conn_device_list():
            c['device_id']=device_id
        self.ser.release()

        
        


    
#    @setting(111115, '', returns='(bs)')
#    def checkCorrectHardware(self, c):
#        """
        
#        Returns:
#            (bool)   :
#            (str)   :
#        """
#        if self.ser is None:
#            Exception('There is not currently a serial connection. There\'s no device to check.')
#        else:
#            yield self.ser.acquire()
#            yield self.ser.write(self.correct_device_check[0])
#            resp=yield self.ser.read()
#            is_match = correct_device_check[1].lower() in resp.lower()
#            self.ser.release()
#            returnValue((is_match,resp))
        
        
