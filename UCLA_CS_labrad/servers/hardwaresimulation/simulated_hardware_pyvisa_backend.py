
def SimulatedDeviceBackend(VisaLibraryBase):

    def __init__(self,node,cli,HSS,sim_devices_list):
        self.node=node
        self.cli=cli
        self.ser=HSS
        self.sim_devices_list=sim_devices_list

    def open_default_resource_manager(self):
        return []
        
    def list_resources(self,session,query='?*::INSTR'):
        return tuple(sim_devices_list)

    def open(self, session, resource_name,
             access_mode=constants.AccessModes.no_lock, open_timeout=constants.VI_TMO_IMMEDIATE):
        instr_session=self.cli.context()
        self.HSS.select_device(self.node, resource_name,context=instr_session)

        return instr_session,resource_name

    def close(self, session):
        """Closes the specified session, event, or find list.

        Corresponds to viClose function of the VISA library."""
        if session==[]:
            pass

        else:
            self.HSS.deselect_device(self.node, resource_name,context=session)

    def read(self,session,count): #asynchronously??
        self.ser.serial_read(session,count)

    def write(self,session,data):
        self.ser.serial_write(session,data)
