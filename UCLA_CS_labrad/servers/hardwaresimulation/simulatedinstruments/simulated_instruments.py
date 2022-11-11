__all__=['SimulatedInstrumentError','SimulatedGPIBInstrument','SimulatedSerialInstrument']
class SimulatedInstrumentError(Exception):

    user_defined_errors={}
    
    base_error_dict={1: 'Trying to communicate with device with {} of {}; expected {}.',2: 'Command not recognized', 3: 'GPIB Query returned empty string.',4: 'Type of parameter {} is {} but should be {}', 5:'Value of {} for {} out of range'}
    def __init__(self, code,parameters=[]):
        self.code = code
        self.errorDict =dict(self.base_error_dict)
        self.errorDict.update(self.user_defined_errors)
        self.parameters=parameters
    
    

    def __str__(self):
        if self.code in self.errorDict:
            return self.errorDict[self.code].format(*self.parameters)
            


    
    
    
    
    
class SimulatedInstrument(object):
    command_dict=None
    
    input_termination_byte=None
    output_termination_byte=None
    id_command=None
    id_string=None
    
    def set_default_settings(self):
        pass
    
    def execute_command(self,func,args):
        return func(self,*args)
    
class SimulatedSerialInstrument(SimulatedInstrument):


    input_termination_byte=b'\r\n'
    output_termination_byte=b'\n'
    
    required_baudrate=None
    required_bytesize=None
    required_parity=None
    required_stopbits=None
    required_dtr=None
    required_rts=None

    command_dict=None

    
        
    def set_default_settings(self):
        pass
        
    def process_communication_parameters(self,baudrate,bytesize,parity,stopbits,dtr,rts):
        if self.required_baudrate and baudrate!= self.required_baudrate:
                raise SimulatedInstrumentError(1,["baudrate",baudrate,self.required_baudrate])
        if self.required_bytesize and bytesize!= self.required_bytesize:
                raise SimulatedInstrumentError(1,["bytesize",bytesize,self.required_bytesize])
        if self.required_parity and parity!= self.required_parity:
                raise SimulatedInstrumentError(1,["parity",parity,self.required_parity])
        if self.required_stopbits and stopbits!= self.required_stopbits:
                raise SimulatedInstrumentError(1,["stopbits",stopbits,self.required_stopbits])
        if self.required_dtr and dtr!= self.required_dtr:
                raise SimulatedInstrumentError(1,["dtr",dtr,self.required_dtr])
        if self.required_rts and rts!= self.required_rts:
                raise SimulatedInstrumentError(1,["rts",rts,self.required_rts])

        
                
            
class SimulatedGPIBInstrument(SimulatedInstrument):

    input_termination_byte=b';:'
    output_termination_byte=b';'
    
    id_command=b'*IDN?'
    clear_command=b'*CLS'
    reset_command=b'*RST'
    id_string=None
    
    command_dict=None

    def set_default_settings(self):
        pass

            

                
