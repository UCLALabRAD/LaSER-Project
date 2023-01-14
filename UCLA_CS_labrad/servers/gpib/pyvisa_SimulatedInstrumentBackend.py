from labrad import util

from twisted.internet.defer import returnValue, inlineCallbacks, DeferredLock

from pyvisa import attributes, constants, errors
from pyvisa.highlevel import VisaLibraryBase
from pyvisa.resources.resource import Resource

import time


#TODO: Rename to SimulatedBackend
#backend used by ResourceManager for simulated devices in GPIB Bus Server
class SimulatedInstrumentVisaLibrary(VisaLibraryBase):
        
    def _init(self):
        self.node=None
        self.cli=None
        self.ser=None
        self.sim_addresses=None
        self.timeout=2.0
        

    def open_default_resource_manager(self):
        return "DefaultResourceManagerSession", constants.StatusCode.success
        
        
    #The backend’s list_resources method is called by the ResourceManager. It takes no arguments but needs to return a list of all simulated devices
    #in the HSS whose simulated address is at the same GPIB Bus Server that ResourceManager is on.
    def list_resources(self,session,query='?*::INSTR'):
        return tuple(["SIM::"+str(address)+"::INSTR" for address in self.sim_addresses])
        #we give the simulated devices resource names of form “SIM::x::INSTR” (similar to “GPIB::x::INSTR”, the real VISA resource name for a GPIB
        #device at primary address x), where x was the SimAddress the GPIB Bus Server was informed of via the HSS LabRAD Signal received when
        #the simulated device was “plugged in” to the computer’s GPIB bus.
        #When the ResourceManager with the SimulatedBackend is initialized during GPIB Bus Server startup, we load it with the server’s simulated_device_list
        #and since Python is pass-by-reference-value this will update in the SimulatedBackend whenever it updates in the server
        #(when device_added/device_removed LabRAD Signals are picked up from the HSS). Thus, we just need to return this list.


    #The backend’s open method is required for the ResourceManager to work at all since the ResourceManager uses it to make the Resource object
    #returned when open_resource is called. This method takes the VISA “resource name” of the resource to be opened as an argument, and the
    #ResourceManager will take care of passing on the resource name provided as the argument to open when calling it. This method must return a new
    #session number to the resource, and the backend must associate this number with the correct device.
    def open(self, session, resource_name,
             access_mode=None, open_timeout=None):
            
        #The first step to writing our HSS-communicating backend is to think about what a session to a resource (simulated device) means
        #based on how we communicate with the HSS. A VISA Session is simply an identifier (number) that a Resource provides whenever a VISA
        #library function is called, so the backend can store information about the Resource’s previous interactions with it and grab this
        #information based on the Resource’s session number. Immediately, this was reminiscent of a context ID in LabRAD that a client provides to a
        #server, so we  have each SimulatedInstrumentResource have its own context ID with the HSS and have the VISA session number simply be the
        #same as the context ID.  we create a new context ID.
        instr_session=self.cli.context()
        
        #Recalling that a simulated VISA resource name is of the form “SIM::x::INSTR”, we parse to get x, the “simulated GPIB primary address” used
        #in the SimAddress of the simulated device in the HSS,
        addr=resource_name.split('::')[1]
        
        #make a select_device request to the HSS with the new context ID to select the device at SimAddress ‘x’ , providing the name of the
        #GPIB Bus Server using this backend. This represents the GPIB Bus this GPIB Bus Server’s computer is controlling. If we had to yield the
        #select_device request, this wouldn’t work, as the ResourceManager isn’t written to work with this asynchronous logic and wouldn’t be able to
        #yield our SimulatedBackend’s open call. Fortunately, recalling that all requests from the same context ID are handled sequentially, we
        #know that the simulated device will be selected for the session by the HSS before our SimulatedBackend makes any more HSS requests in the
        #process of serving that session. Because of this and the fact that the select_device setting in the HSS doesn’t have any return value
        #that we need to respond to our GPIB Bus Server client with, we don’t have to yield.
        self.ser.select_device(self.node, int(addr),context=instr_session)
        
        
        #We then return this context ID. Then, the SimulatedInstrumentResource will store this context ID as its session and provide this to the
        #SimulatedBackend whenever it calls its methods, so the SimulatedBackend can then just use the provided context ID to communicate with the HSS.
        #This effectively makes each SimulatedInstrumentResource a separate HSS client.
        return instr_session, constants.StatusCode.success

    def close(self, session):
        pass
        
            
            
    #This takes two arguments: a session and the number of bytes to read in from the device’s input_buffer. If no byte count is supplied, bytes are
    #read in until the termination character ‘\n’. The method does not return until the requested number of bytes is read in (as the timeout logic is
    #taken care of in the Resource object).  The good news for us is that the read calls on real devices performed in the GPIB Bus Server on the clients’
    #MessageBasedResources actually are blocking until the timeout, and don’t use deferToThread! This means that our implementation of the read method in the
    # SimulatedInstrumentResource can use Deferred logic and inlineCallbacks logic, so our SimulatedBackend’s read method can too- in fact, our simulated
    #reads will be better in terms of parallelization than reading from real devices, since the SBS can keep serving other clients’ requests while the client
    #waits on a read request.

    @inlineCallbacks
    def read(self,session,count):
    
           #make yielded read request to the HSS with the same byte count provided as the argument. Now, there seems to be an issue here- the backend read
           #method doesn’t return until the requested number of bytes has been read in, but the read setting in the HSS may return less bytes than this,
           #since it will return all the bytes in the GPIBCommunicationWrapper’s input_buffer if it has length less than the number of bytes in the read
           #setting’s count argument. So at first glance, it seems like the SimulatedBackend’s read implementation needs to send read requests to the HSS
           #over and over until it can accumulate enough bytes to return, which could be quite complicated. However, for two reasons we do not need to do
           #this. First, since all requests from the same context ID are handled sequentially by servers, the HSS won’t handle any read request in the
           #middle of handling a write request if these requests are made by our SimulatedBackend to serve the same session. Second, if we recall, if there are still device output bytes in the input_buffer of the GPIBCommunicationWrapper and another write is made to the simulated device, this input buffer is cleared. For these two reasons, there is no chance that a HSS read request can be made “too early” and be responded to with less than the number of requested bytes, where more bytes were eventually going to show up in the device’s GPIBCommunicationWrapper’s input_buffer that, added on, would’ve caused the read method in the SimulatedBackend to be able to return with all the requested bytes. So, we can just make one read request and yield it, and if it fails to give us all the bytes we need, it’s fine if we yield forever.  Also, since a non-empty input_buffer will always have exactly one ‘\n’ character and it will be at the end, if the read call has no byte count supplied the SimulatedBackend can send the single HSS read request with no byte count argument, without otherwise changing any of this logic, if the byte count argument is not provided to the SimulatedBackend’s read method.
            resp=yield self.ser.simulated_read(count,context=session)
            if count and len(resp) < count:
                raise errors.VisaIOError(constants.StatusCode.error_timeout)
            returnValue(resp)

    #This takes in the session and the data to be written to the device.
    def write(self,session,data):
        #make a write request to the HSS without yielding (as just like in the Serial Bus Server, the response will be None anyways and we
        #don’t want the client to have to wait for the simulated device to process the written data). We don’t need to attach any callbacks,
        #and instead we can just leave the simulated device’s output in the input_buffer in its GPIBCommunicationWrapper.
        self.ser.simulated_write(data,context=session)
        

    #To finish up the methods that are needed to work with any type of Resource, we have get_attribute and set_attribute. These backend methods take as
    #arguments a session, an attribute identifier, and (in the set case) a value. In the get case, it returns the value of the specified attribute.
    #An attribute identifier is a constant number used by the VISA library to specify a global or local attribute (property of the session), and
    #PyVISA makes all the attribute identifiers easily accessible through a constants module.  In general, a VISA library is supposed to treat
    #some attributes as session-specific (local), and some as attributes shared by all sessions to the same resource (global). However, as the
    #GPIB Bus Server only has the ResourceManager create one Resource per device (and as we recall, one Resource = one session) and has all its
    #clients share it, there’s really no difference between local and global attributes for our purposes.
    #We only used one (local) attribute for our SimulatedBackend: timeout.
    
    #TODO: we need to store a dictionary from session numbers (context IDs) to timeout values, and then when get/set_attribute is called, check if the
    #attribute identifier is the timeout one and return/set the session’s timeout accordingly if so. right now, all resources have the same timeout value,
    #which needs to be fixed

    def get_attribute(self,session,attribute):
        if attribute==constants.ResourceAttribute.timeout_value:
            return self.timeout, constants.StatusCode.success
        else:
            return getattr(self,attribute), constants.StatusCode.success
                
    def set_attribute(self,session,attribute,attribute_state):
        if attribute==constants.ResourceAttribute.timeout_value:
            self.timeout=attribute_state
        else:
            if hasattr(self,attribute):
                setattr(self,attribute,attribute_state)
        return constants.StatusCode.success
    
    #Finally, we have the backend’s clear method; this just clears the input and output buffers.
    #TODO: For this we just make reset_input_buffer and reset_output_buffer requests to the HSS without yielding them, since they
    #don’t return anything and requests from the same context ID are always handled sequentially (so any future requests with that context ID will
    #only be handled once the buffers have already cleared).
    @inlineCallbacks
    def clear(self,session):
        yield self.ser.reset_input_buffer(context=session)
        yield self.ser.reset_output_buffer(context=session)
 
    
    
#object that mimics MessageBasedResource, for simulated devices. Uses SimulatedBackend instead of NI-Visa library
class SimulatedInstrumentResource(Resource):

   def __init__(self, resource_manager, resource_name):
       super().__init__(resource_manager,resource_name)
       
       #the writer of the GPIB Bus Server stresses atomicity of each setting in the comments of the original code. It is for this reason that the
       #original GPIB Bus Server has no yields of any kind (if no setting yields/returns a Deferred, every setting has to be atomic as there’s no way
       #for the server to switch to handling a different request until it responds to the current one).
       #how can we make the GPIB Bus Server allow parallelization between context IDs with different selected simulated devices, but force the server to handle
       #requests from context IDs with the same selected device sequentially? For situations like these, Twisted offers an object called a DeferredLock.
       #This is like a mutex lock for asynchronous programming. Trying to acquire it returns a Deferred that will fire when the lock is available.
       #A first-come first-serve list is maintained if setting calls from multiple clients are trying to acquire a locked DeferredLock.
       #Yielding the Deferred returned by the acquire method will allow other clients to be served until the lock is available.
       #we give each SimulatedInstrumentResource object a DeferredLock. At the beginning of each SimulatedInstrumentResource method the lock is
       #acquired and at the end it is released. Since each GPIB Bus Server setting only calls one method of the client’s Resource object,
       #this will give us the asynchronous “thread” safety we want.

       self.async_lock=DeferredLock()
   
   #to read, we yield a call to our SimulatedBackend’s read method, passing our session number and the same byte count as arguments.
   #However, we need to implement the timeout logic and make it work with our asynchronous simulated read approach.
   #GPIB communication treats success as all or nothing: when the MessageBasedResource calls the backend’s read method,
   #it either gets all the requested bytes and returns them, or it cannot get all the requested bytes and thus the call times out
   #and an error is raised. This means whatever bytes were available are thrown out.
   @inlineCallbacks
   def read_with_timeout(self,byte_count=None):

       rec=self.visalib.read(self.session,byte_count)
       
       #calls the SimulatedBackend’s read method and stores its return value, which is a Deferred  (since it uses inlineCallbacks).
       #Instead of yielding this Deferred directly, we plug it into maybeTimeout (which we learned from the Serial Bus Server) with our session’s timeout,
       #and yield the Deferred returned by maybeTimeout. This Deferred will fire when either the timeout has passed or the read in the SimulatedBackend
       #returns with all the requested bytes; whichever comes first.
       timeout_object=[]
       resp=yield util.maybeTimeout(rec, min(self.timeout, 300), timeout_object)
       #Then, since we can now write the code as if it was synchronous, we check if the result is the timeout indicator or the bytes we wanted.
       #If it’s the timeout indicator we raise the VISA timeout error. Otherwise, we return the bytes.
       if resp==timeout_object:
            raise errors.VisaIOError(constants.StatusCode.error_timeout)
       returnValue(resp)
       
   #exactly the same as read_bytes except no byte count is provided, and it reads until the newline character;
   #here we can just do the exact same thing we did to implement the read_bytes function but pass no argument to the SimulatedBackend’s  read method.
   @inlineCallbacks
   def read_raw(self):
       yield self.async_lock.acquire()
       resp=yield self.read_with_timeout()
       self.async_lock.release()
       returnValue(resp.encode())
       
   #takes in the requested number of bytes to read
   @inlineCallbacks
   def read_bytes(self,byte_count):
       yield self.async_lock.acquire()
       
       resp=yield self.read_with_timeout(byte_count)
       self.async_lock.release()
       returnValue(resp.encode())
   
   #takes in the data being written and is in charge of writing it to the device through the backend, not needing to return anything
   @inlineCallbacks
   def write(self,data):
       yield self.async_lock.acquire()
       #call the SimulatedBackend write method with this Resource object's session and this data
       yield self.visalib.write(self.session,data)
       self.async_lock.release()
       
       
   @inlineCallbacks
   def write_raw(self,data):
       yield self.async_lock.acquire()
       self.visalib.write(self.session,data.decode())
       self.async_lock.release()
   
   #This takes one argument, data to be written to the device, waits for a query_delay (which is represented by an object variable belonging
   #to the Resource, with the value being in seconds), and then reads until the newline character with the timeout from the session’s timeout attribute,
   #and then returns the result or gives a timeout error accordingly.
   @inlineCallbacks
   def query(self,data):
       yield self.async_lock.acquire()
       #use the SimulatedInstrumentResource’s write method to write, and then yield the SimulatedInstrumentResource’s read method (not the backend’s).

       self.visalib.write(self.session,data)
       start_time=time.time()
       #block for the query delay time (as this is usually a very,very short amount of time just to give a device time to catch up,
       #we opted not to yield here, but theoretically we could)
       while (time.time())-start_time<self.query_delay:
           pass
           
       #yield the SimulatedInstrumentResource’s read_with_timeout method (not the backend’s)
       resp=yield self.visalib.read_with_timeout()
       self.async_lock.release()
       returnValue(resp.encode())
       
   #this just calls the SimulatedBackend’s clear method, which takes in the  SimulatedInstrumentResource’s session number and resets the
   #input and output buffers for the device using non-yielded HSS requests
   #TODO: remove yields
   @inlineCallbacks
   def clear(self):
       yield self.async_lock.acquire()
       yield self.visalib.clear(self.session)
       self.async_lock.release()
   

   
        
WRAPPER_CLASS=SimulatedInstrumentVisaLibrary
