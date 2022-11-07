from pyvisa.highlevel import VisaLibraryBase
from pyvisa.resources.resource import Resource
import time



from pyvisa import attributes, constants, errors, logger

from labrad import util


from twisted.internet.defer import returnValue, inlineCallbacks, DeferredLock

class SimulatedDeviceVisaLibrary(VisaLibraryBase):
        
    def _init(self):
        self.node=None
        self.cli=None
        self.ser=None
        self.sim_addresses=None
        self.timeout=2.0
        

    def open_default_resource_manager(self):
        return "DefaultResourceManagerSession", constants.StatusCode.success
        
    def list_resources(self,session,query='?*::INSTR'):
        return tuple(["SIM::"+str(address)+"::INSTR" for address in self.sim_addresses])

    def open(self, session, resource_name,
             access_mode=None, open_timeout=None):
            
        instr_session=self.cli.context()
        addr=resource_name.split('::')[1]
        self.ser.select_device(self.node, int(addr),context=instr_session)
        return instr_session, constants.StatusCode.success

    def close(self, session):
        pass
        
            
            
            
    @inlineCallbacks
    def read(self,session,count):
            resp=yield self.ser.simulated_read(count,context=session)
            if count and len(resp) < count:
                raise errors.VisaIOError(constants.StatusCode.error_timeout)
            returnValue(resp)

            
    def write(self,session,data):
        self.ser.simulated_write(data,context=session)
        

        
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
    

    @inlineCallbacks
    def clear(self,session):
        yield self.ser.reset_input_buffer(context=session)
        yield self.ser.reset_output_buffer(context=session)
 
    
    
        
class SimInstrumentResource(Resource):
   def __init__(self, resource_manager, resource_name):
       super().__init__(resource_manager,resource_name)
       self.async_lock=DeferredLock()
   
   @inlineCallbacks
   def read_with_timeout(self,byte_count=None):
       rec=self.visalib.read(self.session,byte_count)
       timeout_object=[]
       resp=yield util.maybeTimeout(rec, min(self.timeout, 300), timeout_object)
       if resp==timeout_object:
            raise errors.VisaIOError(constants.StatusCode.error_timeout)
       returnValue(resp)
       
   @inlineCallbacks
   def read_raw(self):
       yield self.async_lock.acquire()
       resp=yield self.read_with_timeout()
       self.async_lock.release()
       returnValue(resp.encode())
       
   @inlineCallbacks
   def read_bytes(self,byte_count):
       yield self.async_lock.acquire()
       resp=yield self.read_with_timeout(byte_count)
       self.async_lock.release()
       returnValue(resp.encode())
   
   @inlineCallbacks
   def write(self,data):
       yield self.async_lock.acquire()
       yield self.visalib.write(self.session,data)
       self.async_lock.release()
       
       
   @inlineCallbacks
   def write_raw(self,data):
       yield self.async_lock.acquire()
       self.visalib.write(self.session,data.decode())
       self.async_lock.release()
   
   @inlineCallbacks
   def query(self,data):
       yield self.async_lock.acquire()
       self.visalib.write(self.session,data)
       start_time=time.time()
       while (time.time())-start_time<self.query_delay:
           pass
       resp=yield self.visalib.read_with_timeout()
       self.async_lock.release()
       returnValue(resp.encode())
       
   @inlineCallbacks
   def clear(self):
       yield self.async_lock.acquire()
       yield self.visalib.clear(self.session)
       self.async_lock.release()
   

   
        
WRAPPER_CLASS=SimulatedDeviceVisaLibrary
