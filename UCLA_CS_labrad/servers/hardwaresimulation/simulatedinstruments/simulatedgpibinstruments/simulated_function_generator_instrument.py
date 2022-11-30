
from ..simulated_instruments import SimulatedGPIBInstrumentInterface, SimulatedInstrumentError
from UCLA_CS_labrad.servers.hardwaresimulation.cablesimulation.simulatedoutputsignals.simulated_function_generator_output_signal import SimulatedFunctionGeneratorOutputSignal

__all__=["SimulatedFunctionGeneratorInstrument","SimulatedFunctionGeneratorError"]

class SimulatedFunctionGeneratorError(SimulatedInstrumentError):
    user_defined_errors={}

class SimulatedFunctionGeneratorInstrument(SimulatedGPIBInstrumentInterface):
    name=None
    version=None
    description=None
    id_string=None
    max_voltage=None
    function_dictionary=None
    def_amp=None
    def_freq=None
    def_func=None
    
    channel_count=1
    signal_type=SimulatedFunctionGeneratorOutputSignal

        
    def set_default_settings(self):
        super().set_default_settings()
    
    def set_signal_properties_starting_values(self,signal):
        super().set_signal_properties_starting_values(signal)
        signal.function=(self.def_func,self.function_dictionary[self.def_func][0])
        signal.amplitude=self.def_amp
        signal.frequency=self.def_freq
        
    def toggle(self,status=None):
        if status:
            status=self.enforce_type_and_range(status,[(int,(0,1)),(str,["ON","OFF"])],"status")
            if status=='ON' or status==1:
                self.channels[0].outputting=True
            elif status=='OFF' or status==0:
                self.channels[0].outputting=False
        else:
            return str(int(self.channels[0].outputting))
        

    def frequency(self,freq=None):
        if freq:
            freq=self.enforce_type_and_range(freq,(float,self.calculate_freq_range()),"frequency")
            self.channels[0].frequency=freq
        else:
            return str(self.channels[0].frequency)
            
    def amplitude(self,amp=None):
        if amp:
            amp=self.enforce_type_and_range(amp,(float,self.calculate_amp_range()),"frequency")
            self.channels[0].amplitude=amp
        else:
            return str(self.channels[0].amplitude)
            
    def offset(self,offs=None):
        if offs:
            offs=self.enforce_type_and_range(offs,(float,self.calculate_offs_range()),"offset")
            self.channels[0].offset=offs
        else:
            return str(self.channels[0].offset)
        
            
    def function(self,func=None):
        if func:
            func=self.enforce_type_and_range(func,(str,self.function_dictionary.keys()),"function")
            self.channels[0].function=(func,self.function_dictionary[func][0])
        else:
            return self.channels[0].function[0]

    def calculate_freq_range(self):
        func_str=self.channels[0].function[0]
        return self.function_dictionary[func_str][1]
            
    def calculate_amp_range(self):
        return (0,2*(self.max_voltage-abs(self.channels[0].offset)))
        
    def calculate_offs_range(self):
        abs_val=(self.max_voltage-(self.channels[0].amplitude/2.0))
        return (-1*abs_val,abs_val)
            
            
                    
