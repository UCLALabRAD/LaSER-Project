__all__=['SimulatedInstrumentError','SimulatedGPIBInstrumentInterface','SimulatedSerialInstrumentInterface']

#Core of error logging system.
#This can be subclassed for each generic device, and errors of this subclass can be raised at any time in the generic device command-handling code.
#This error takes in a number and a list of values. The number represents a key that maps to an error string in a dictionary possessed by the
#SimulatedInstrumentError subclass. This error string may contain one or more instances of “{}”. The length of the list of values provided
#should match the number of instances of “{}” in that error string, as when the error is raised, before canceling the command the communication
#wrapper will automatically add the corresponding error string, with the “{}” instances filled with the provided values, to the device’s wrapper’s
# error_queue. Also added to the error queue will be a timestamp and the bytestring of the command that caused the error.
#All one must do is create a class extending SimulatedInstrumentError and give it just one new class property called user_defined_errors.
class SimulatedInstrumentError(Exception):
    
    #Meant to be overridden by generic-device-writer subclassing this class, with errors specific to a class of instruments (say, oscilloscopes).
    #Dictionary should be in the same format as the SimulatedInstrumentError’s base error dictionary,
    #and each key-value entry will simply be added to the base_error_dict to get the subclass' full error dict (so keys should not conflict).
    user_defined_errors={}
    
    
    
    
    #base device errors-these are automatically taken care of so generic device writer does not need to worry about them.
    # (except 4 and 5, see enforce_type_and_range for  more info. here, all the user must do is call a provided helper function,
    # giving the function the expected type and legal range respectively)
    
    
    #1 is for incorrect serial parameters, first blank is for parameter type (example: baudrate), second is for value controller tried to use
    #to communicate, third is for required value
    
    #2 is for invalid command (no match found in command dict for a command)
    
    #3 is for when a GPIB query is written to a device, but nothing is returned #TODO: maybe remove this since it's more a mistake by the generic-device-writer
    #whereas this system is meant to be more for errors related to the command written to the device at runtime
    
    #4 is for when an argument is of incorrect type, 5 is for when argument is out of range (automatically taken care of as long as enforce_type_and_range used)
    #6 is for input or output buffer overflow based on max buffer size (automatically taken care of)
    base_error_dict={1: 'Trying to communicate with device with {} of {}; expected {}.',2: 'Command not recognized', 3: 'GPIB Query returned empty string.',4: 'Type of parameter {} should be {}', 5:'Value of {} for {} out of range',6: 'Buffer of size {} overflowed.'}
   
    def __init__(self, code,parameters=[]):
        self.code = code
        self.errorDict =dict(self.base_error_dict)
        self.errorDict.update(self.user_defined_errors) #add user-defined errors for their error subclass
        self.parameters=parameters
    
    

    def __str__(self):
        if self.code in self.errorDict: #if valid error code...
            return self.errorDict[self.code].format(*self.parameters) #pass in provided parameters to fill in {} instances
            


    
    
    
    
#base class for simulated devices
class SimulatedInstrumentInterface(object):

    # Dictionary written by the specific-device-writer, mapping specific-device commands to generic-device handler methods.
    # The keys are two-tuples which represent valid command structures. The first element of each such key is a valid command header
    # in the serial case, or a SCPI command header structure in the GPIB case (which encodes many different valid command headers that all are treated the same).
    # This be found in the instrument model’s Programmer’s Manual.
    # The second element is an integer or a list of integers specifying the different numbers of arguments that command can have.
    # The value a key maps to is the function from the generic device base class that the specific-device-writer wants to handle the command.
    # The generic device functionality (a method) is called, with the command’s arguments being passed to the method.
    # The device's communication wrapper will check if a received command meets one of the valid command structures. If so, the generic device
    # functionality (a method) that the user attached to that command structure when writing the command_dict will be called,
    # with the command’s arguments being passed to the method.
    command_dict=None
    
    
    #byte used to separate commands received by device
    input_termination_byte=None
    
    #byte used to separate responses from device
    output_termination_byte=None
    
    #Represents the command used to ask the device to return its ID string. For GPIB devices this is always *IDN?. For serial devices this can
    # be anything.
    id_command=None
    
    #Defined by specific-device-writers. Represents model of device.
    #Required for GPIB devices to be communicated with via a GPIB Managed Device Server. Otherwise, the GPIB Device Manager will not be
    #able to take accurate note of the model of the device, and thus will not message the interested GPIB Managed Device Servers.
    id_string=None
 

    #Defined by generic device writer. The channels list will be filled with objects of this class during instantiation; this can be InputSignal or a subclass of OutputSignal.
    signal_type=None

    #Nonnegative integer value. During simulated device initialization, an object variable called channels will be automatically instantiated as a list of OutputSignal or InputSignal objects of length channel_count.
    channel_count=None
    
    def __init__(self):
        if self.channel_count: #if none, assume no channels
            self.channels=[]
            for i in range(self.channel_count):
                self.channels.append(self.signal_type()) #fills list with (channel_count)-many channel objects of type signal_type
        self.set_default_settings() #initialize device's object properties with default values

    #Meant to be extended by generic-device-writer. Used to initialize device's object variables with starting values.
    #Object variables the user initializes here represent properties that
    #will change based on commands sent to the device and they collectively represent its state.  set_default_settings will automatically be
    #called when a device is added to the HSS and, in the GPIB case, when the universal SCPI reset command “*RST?” is sent to it.
    #Some default values will be the same across all models of instruments of that type, and these can just be hardcoded in.
    #However, the default values for some properties are specific to device models- these should be written as class variables set to None
    #and the properties should be set to these variables in set_default_settings. Valid ranges for properties should also be written as class
    #variables set to None (as should any other property whose value is specific to a device model and will never change when commands are sent to the device).
    def set_default_settings(self):
        for signal in self.channels:
            self.set_signal_properties_starting_values(signal) #initialize all of device's channels' object properties with default values
        
    #Meant to be extended by generic-device-writer. Added logic should define the channel's object variables that were declared in initialize_signal_properties
    # (except those that were already defined there via hardcoding the value)
    def set_signal_properties_starting_values(self,signal):
        signal.initialize_signal_properties()
        
    #called by communication wrapper, this is where the instrument actually reacts to the command so it's made a device method
    # and not a wrapper one purely ceremoniously. func is the command's corresponding generic device method grabbed from the command dict,
    # and args is a list of the args provided when the command was written to the device
    def execute_command(self,func,args):
        return func(self,*args)
    
    
    #helper function that can be used by generic-device-writers to check that an
    # argument to a generic device method (which, as we call, will always be a string, since the arguments
    #come from the command written to the device) can be cast to the required type and is in range.
    #If the argument is the right type and in range, it will be cast to this
    #correct type, and if it is not, an error will be added to the error queue.
    #val is the string for the argument parsed from the command.
    #options is a list of 2-tuples of form (type,range) which represent legal type-and-range pairs for that argument
    #    here, type is a Python class or built-in type
    #    and range can either be a list of valid values, or a two-tuple of form (min,max).
    #multiple options could be useful when argument can be of more than one type, or when valid range is weird
    #param is a string stating what the argument represents (say, voltage) to be used in the logged error
    def enforce_type_and_range(self,val,options,param):
        if type(options)==tuple:
            options=[options] #if only one option given, make sure it's a list
        correct_type=False
        for val_type,val_range in options: #only needs to fit one option
            try:
                casted_val=val_type(val) #attempt to cast
                correct_type=True #cast succeeded so argument is of correct type for at least one option
            except:
                continue #cast didn't succeed, argument doesn't fit this option
            if type(val_range)==tuple: #(min,max) range used
                val_low,val_high=val_range
                if not (val_low <= casted_val <= val_high):
                    continue #not in range, option doesn't work
            else: #enumeration range used for this option
                if not (casted_val in val_range):
                    continue #not in range, option doesn't work
            return casted_val
        if not correct_type:
            raise SimulatedInstrumentError(4,[param,options[0]]) #if no options met, assume type error unless type correct for at least one option.
        raise SimulatedInstrumentError(5,[val, param])  #range error
    
    
    
#interface to write generic simulated serial instruments
class SimulatedSerialInstrumentInterface(SimulatedInstrumentInterface):

    #see SimulatedInstrumentInterface
    input_termination_byte=b'\r\n'
    output_termination_byte=b'\n'
    
    #serial communication parameters required by device. Leave as None if device is indifferent to the value of the parameter.
    required_baudrate=None
    required_bytesize=None
    required_parity=None
    required_stopbits=None
    required_dtr=None
    required_rts=None
    
    #see SimulatedInstrumentInterface
    signal_type=None
    
    #see SimulatedInstrumentInterface, noting that this a command_dict for a serial device, so the first element of each key is simply a valid serial command header
    command_dict=None

    
    # see SimulatedInstrumentInterface
    def set_default_settings(self):
        super().set_default_settings()
        
    # see SimulatedInstrumentInterface
    def set_signal_properties_starting_values(self,signal):
        super().set_signal_properties_starting_values(signal)
        
    #defines how the device reacts to an incorrect serial communication parameter- the default behavior is to give an error if any parameter it cares
    #about has an incorrect value, but the specific-device-writer may want to change this by overriding
    def process_communication_parameters(self,baudrate,bytesize,parity,stopbits,dtr,rts):
        if self.required_baudrate and baudrate!= self.required_baudrate:
                raise SimulatedInstrumentError(1,["baudrate",baudrate,self.required_baudrate]) #add to error queue
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

        
                
#interface to write generic simulated GPIB instruments
class SimulatedGPIBInstrumentInterface(SimulatedInstrumentInterface):

    #see SimulatedInstrumentInterface
    input_termination_byte=b';:'
    output_termination_byte=b';'
    
    #see SimulatedInstrumentInterface
    signal_type=None
    
    #See SimulatedInstrumentInterface. This is the universal SCPI command for identification used by all GPIB devices
    id_command=b'*IDN?'
    
    #Universal SCPI command to clear buffers used by all GPIB devices
    clear_command=b'*CLS'
    
    #Universal SCPI command to reset device used by all GPIB devices
    reset_command=b'*RST'
    id_string=None
    
    #see SimulatedInstrumentInterface, noting that this a command_dict for a GPIB device, so the first element of each key should be a valid
    #SCPI command header structure, which is a bytestring written in a specific format that encodes multiple valid ways the command header can be written
    #to lead to the same device functionality
    command_dict=None
    
    #see SimulatedInstrumentInterface
    def set_default_settings(self):
        super().set_default_settings()
      
    #see SimulatedInstrumentInterface
    def set_signal_properties_starting_values(self,signal):
        super().set_signal_properties_starting_values(signal)
        
