
from ..simulated_instruments import SimulatedSerialInstrumentInterface, SimulatedInstrumentError

from UCLA_CS_labrad.servers.hardwaresimulation import SimulatedPiezoOutputSignal

__all__=['SimulatedPiezoInstrument','SimulatedPiezoError']

#Add new error messages specific to Piezo instruments here. See SimulatedInstrumentError
class SimulatedPiezoError(SimulatedInstrumentError):
    user_defined_errors={}

#Generic device class for Simulated Piezo Instrument.
#Serial device with output channels which each output a constant voltage. It supports serial commands
#to toggle a channel on or off, ask whether a channel is on or off, set a new voltage for a channel to
#constantly output, or get the voltage that a channel is currently constantly outputting.
#Must be subclassed for any piezo instrument model used in the lab.
#Any class variable set to None needs to be defined when subclassing with values specific to the model,
#unless otherwise specified. See simulated AMO3 specific device class for an example.
class SimulatedPiezoInstrument(SimulatedSerialInstrumentInterface):
    name= None
    version = None
    description= None
    
    #see SimulatedSerialInstrumentInterface (a serial communication parameter
    #does not need to be defined unless instrument requires a specific value for said parameter
    required_baudrate=None
    required_bytesize=None
    required_parity=None
    required_stopbits=None
    required_rts=None
    required_dtr=None
    
    #valid range for constant voltage output from a channel (2-tuple of floats of form (min,max))
    voltage_range=None
    
    
    #Unlike GPIB devices, which have standardized query response formats, serial devices may respond with any
    # random message such as “the voltage has been set to x”, so we need the specific device writer to specify every
    #response string (using {} for x so we can use Python’s string format function to plug in x)
    
    #string returned by instrument model when voltage set (should have two instances of {}, the first for the channel and the second for the voltage)
    
    set_voltage_string=None
    
    #strings returned by instrument model when channel turned on/off (should each have an instance of {} for the channel number)
    set_toggle_on_string=None
    set_toggle_off_string=None

    #see SimulatedInstrumentInterface
    channel_count=None
    
    #see SimulatedInstrumentInterface
    signal_type=SimulatedPiezoOutputSignal
    
    #see SimulatedInstrumentInterface. No default values need to be initialized when extending this as all properties are
    #output signal properties
    def set_default_settings(self):
        super().set_default_settings()
        
    #see SimulatedInstrumentInterface. No model-specific values for output signal properties, so nothing to do when extending
    def set_signal_properties_starting_values(self,signal):
        super().set_signal_properties_starting_values(signal)
    
        
    
    #channel status getter command handler
    #takes in a channel number, checking it is of type int and in valid range, and returns the outputting property of the specified channel,
    #plugged into the model-specific status-getter response string.
    def get_channel_status(self,channel):
        channel=self.enforce_type_and_range(channel,(int,(1,4)),"channel")
        return (str(int(self.channels[channel-1].outputting)))

                    
    #channel status setter command handler
    # takes in a channel number and a status int (0 for “off”, 1 for “on”), checking it is of type int and in
    #valid range, and sets the outputting property of the specified channel to this new status. It then returns
    #this new status plugged into the model-specific status-setter response string.
    def set_channel_status(self,channel,status):
        channel=self.enforce_type_and_range(channel,(int,(1,4)),"channel")
        status=self.enforce_type_and_range(status,(int,(0,1)),"status")
        self.channels[channel-1].outputting=bool(status) #output turned on/off automatically using python property setter decorator
        if status==0:
            return self.set_toggle_off_string.format(channel)
        elif status==1:
            return self.set_toggle_on_string.format(channel)
                        
                        
    #handles the voltage-getting serial command.
    #takes in a channel number, checking it is of type int and in valid range, and responds with the voltage
    #property of the specified channel in channels, plugged into the model-specific voltage-getter response string
    def get_channel_voltage(self,channel):
        channel=self.enforce_type_and_range(channel,(int,(1,4)),"channel")
        current_voltage=self.channels[channel-1].voltage
        return "{:.2f}".format(current_voltage)
                
    #handles the voltage-setting serial command.
    #takes in a channel number and voltage, checking they are of types int and float respectively and in valid range,
    #and then sets the voltage property of the specified channel in channels to this new voltage. Then, it plugs
    #in this new voltage to the model-specific voltage-setter response string and responds with this string
    def set_channel_voltage(self,channel,voltage):
        channel=self.enforce_type_and_range(channel,(int,(1,4)),"channel")
        
        voltage=self.enforce_type_and_range(voltage,(float,self.calculate_voltage_range()),"voltage")
        self.channels[channel-1].voltage=voltage #output signal updated automatically using python property setter decorator

        return self.set_voltage_string.format(channel,voltage)
        
        
    def calculate_voltage_range(self):
        return self.voltage_range
