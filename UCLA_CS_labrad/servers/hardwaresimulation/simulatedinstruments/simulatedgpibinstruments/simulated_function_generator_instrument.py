
from ..simulated_instruments import SimulatedGPIBInstrumentInterface, SimulatedInstrumentError
from UCLA_CS_labrad.servers.hardwaresimulation.cablesimulation.simulatedoutputsignals.simulated_function_generator_output_signal import SimulatedFunctionGeneratorOutputSignal

__all__=["SimulatedFunctionGeneratorInstrument","SimulatedFunctionGeneratorError"]

#Add new error messages specific to Function Generator instruments here. See SimulatedInstrumentError
class SimulatedFunctionGeneratorError(SimulatedInstrumentError):
    user_defined_errors={}

#Generic device class for Simulated Function Generator Instrument.
#GPIB device with one output channel
#TODO: should probably accomodate any amount of channels like the piezo generic class does. However, Function Generator GPIB managed server assumes one channel, so here we assume 1. Would be easy to fix though, just need to change channel count
#Channel outputs an electrical signal whose waveform is periodic. This can be a sine wave, square wave,
#sawtooth wave, and more. The instrument supports GPIB commands for getting or setting the
#amplitude or frequency of the signal,  toggling its lone channel on and off, asking whether the channel is on
#or off, or changing the type of periodic function used to generate the wave (sine, square, etc.).
# Must be subclassed for any FG instrument model used in the lab.
#Any class variable set to None needs to be defined when subclassing with values specific to the model,
#unless otherwise specified. See simulated Agilent33210A specific device class for an example.
class SimulatedFunctionGeneratorInstrument(SimulatedGPIBInstrumentInterface):
    name=None
    version=None
    description=None
    
    #see SimulatedGPIBInstrumentInterface
    id_string=None
    
    #max voltage (absolute value) that can be output by channel
    max_voltage=None
    
    #maps from the string used to represent a waveform type by the device,
    #to a 2-tuple containing the periodic Python function representing that waveform type,
    #and a valid frequency range for that function (which can be found in the Programmer’s
    #Manual for the instrument model). For example, the key-value pair for the sine function
    #may look like “SIN” -> (np.sin , (.01,10000.0) ).
    function_dictionary=None
    
    #default output signal amplitude (float)
    def_amp=None
    
    ##default output signal frequency (float)
    def_freq=None
    
    #default output signal function, a.k.a. waveform shape (string from function dictionary)
    def_func=None
    
    #see SimulatedInstrumentInterface
    channel_count=1
    
    #see SimulatedInstrumentInterface
    signal_type=SimulatedFunctionGeneratorOutputSignal

    #see SimulatedInstrumentInterface. No default values need to be initialized when extending this as all properties are
    #output signal properties
    def set_default_settings(self):
        super().set_default_settings()
    
    #see SimulatedInstrumentInterface.
    def set_signal_properties_starting_values(self,signal):
        super().set_signal_properties_starting_values(signal)
        signal.function=(self.def_func,self.function_dictionary[self.def_func][0]) #form is (string representing function, actual function from numpy arr-> numpy arr)
        signal.amplitude=self.def_amp
        signal.frequency=self.def_freq
        
    
    #handler for set/query GPIB commands for the output channel status. The query handler just returns the status of the channel’s outputting property,
    #and the set command handler takes one argument (the new status), checks the range and type of this argument, and sets the outputting property
    #of the channel to this new status.
    def toggle(self,status=None):
        if status: #set command
            status=self.enforce_type_and_range(status,[(int,(0,1)),(str,["ON","OFF"])],"status") #example of multiple options for valid arguments.
            #The status argument for the setter can be “ON” (or 1) to turn on the channel output, or “OFF” (or 0) to turn it off.
            if status=='ON' or status==1:
                self.channels[0].outputting=True
            elif status=='OFF' or status==0:
                self.channels[0].outputting=False
        else: #query command
            return str(int(self.channels[0].outputting))
        
    #handler for set/query commands for the output signal’s frequency.
    #The setter takes one argument, a float representing a new frequency, and checks the range and type of this argument.
    #To determine the valid range for this argument, we get the function-representing-string for the current output function via the function property of the channel,
    #and use the function_dictionary to get the valid frequency range for the current output function
    #The set and query handlers simply set/get the frequency property of the output signal.
    def frequency(self,freq=None):
        if freq: #set command
            freq=self.enforce_type_and_range(freq,(float,self.calculate_freq_range()),"frequency")
            self.channels[0].frequency=freq
        else: #query command
            return str(self.channels[0].frequency)
            
    #handlers for the set/query commands for the output signal’s amplitude.
    #The setter takes one argument, a float representing a new peak-to-peak amplitude for the output signal, and checks the range and type of this argument.
    #To determine the valid range for the new amplitude argument for the setter, we get the offset property of the channel and ensure, by adding the absolute
    #value of the offset to the half the new amplitude (noting that amplitude is measured peak-to-peak), that changing to this new amplitude wouldn’t cause us
    #our voltage output to ever go beyond the max voltage in either the positive or negative direction. The set and query handlers simply set/get the amplitude
    #property of the output signal.
    def amplitude(self,amp=None):
        if amp:
            amp=self.enforce_type_and_range(amp,(float,self.calculate_amp_range()),"frequency")
            self.channels[0].amplitude=amp
        else:
            return str(self.channels[0].amplitude)
           
    #handlers for the set/query commands for the output signal DC offset. The setter takes one argument, a float representing a new DC offset, and checks
    # the range and type of this argument. To determine the valid range for the new offset argument for the setter, we get the amplitude property of the channel
    #and ensure, by adding the absolute value of the offset to the half the amplitude, that changing to this new offset wouldn’t cause us our voltage output to
    #ever go beyond the max voltage in either the positive or negative direction. The set and query handlers simply set/get the offset property of the output signal.
    def offset(self,offs=None):
        if offs: #set command
            offs=self.enforce_type_and_range(offs,(float,self.calculate_offs_range()),"offset")
            self.channels[0].offset=offs
        else: #query command
            return str(self.channels[0].offset)
        
    #handler for the set/query commands for the waveform type of the electrical output signal. The set command handler takes one argument,
    #func,a string representing a waveform type, and checks the range and type of this argument. This argument’s value can be any of the keys in the
    #function_dictionary. The function property of the channel is set to the 2-tuple (func, corresponding actual function found in function dict)
    #The query handler gets the function property of the channel and returns the function-representing-string string from it
    def function(self,func=None):
        if func: #set command
            func=self.enforce_type_and_range(func,(str,self.function_dictionary.keys()),"function")
            self.channels[0].function=(func,self.function_dictionary[func][0])
        else: #query command
            return self.channels[0].function[0]

    def calculate_freq_range(self):
        func_str=self.channels[0].function[0]
        return self.function_dictionary[func_str][1]
            
    def calculate_amp_range(self):
        return (0,2*(self.max_voltage-abs(self.channels[0].offset)))
        
    def calculate_offs_range(self):
        abs_val=(self.max_voltage-(self.channels[0].amplitude/2.0))
        return (-1*abs_val,abs_val)
            
            
                    
