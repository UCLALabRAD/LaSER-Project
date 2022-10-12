from pyvisa.highlevel import VisaLibraryBase
class SimulatedDeviceVisaLibrary(VisaLibraryBase):
        
    def _init(self):
        self.node=None
        self.cli=None
        self.ser=None
        self.sim_devices_list=None

    def open_default_resource_manager(self):
        return "DefaultResourceManagerSession", 1
        
    def list_resources(self,session,query='?*::INSTR'):
        return tuple(self.sim_devices_list)

    def open(self, session, resource_name,
             access_mode=None, open_timeout=None):
        instr_session=self.cli.context()
        self.ser.select_device(self.node, resource_name,context=instr_session)
        
        return instr_session,resource_name

    def close(self, session):
        """Closes the specified session, event, or find list.

        Corresponds to viClose function of the VISA library."""
        if session=="DefaultResourceManagerSession":
            pass

        else:
            d=self.HSS.deselect_device(self.node, resource_name,context=session)
            d.callback(True)

    def read(self,session,count): #asynchronously??
        d=self.ser.serial_read(session,count)
        d.callback(True)
        return d.result

    def write(self,session,data):
        d=self.ser.serial_write(session,data)
        d.callback(True)
        return d.result
        
    def get_attribute(self,session,attribute):
        if session=="DefaultResourceManagerSession":
            return getattr(self,attribute)
                
    def set_attribute(self,session,attribute,attribute_state):
        if session=="DefaultResourceManagerSession":
            if hasattr(self,attribute):
                setattr(self,attribute,attribute_state)
                
                
             
            
            
        

        
        
WRAPPER_CLASS=SimulatedDeviceVisaLibrary
