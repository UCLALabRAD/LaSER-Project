
from ..simulated_instruments import SimulatedGPIBInstrument, SimulatedInstrumentError
from UCLA_CS_labrad.servers.hardwaresimulation.cablesimulation.simulatedoutputsignals.simulated_function_generator_output_signal import SimulatedFunctionGeneratorOutputSignal

__all__=["SimulatedFunctionGeneratorInstrument","SimulatedFunctionGeneratorError"]

class SimulatedFunctionGeneratorError(SimulatedInstrumentError):
    user_defined_errors={}

class SimulatedFunctionGeneratorInstrument(SimulatedGPIBInstrument):
    name=None
    version=None
    description=None
    id_string=None
    freq_ranges=None
    max_voltage=None
    function_map=None
    def_amp=None
    def_freq=None
    def_func=None
    
    def __init__(self):
        self.channels=[]
        for i in range(1):
            self.channels.append(SimulatedFunctionGeneratorOutputSignal())
        self.set_default_settings()
        
    def set_default_settings(self):
        for chan in self.channels:
             chan.outputting=False
             chan.offset=0.0
             chan.function=(self.def_func,self.function_map[self.def_func])
             chan.amplitude=self.def_amp
             chan.frequency=self.def_freq
             
        
        
    def toggle(self,status=None):
        status=self.enforce_type_and_range(status,[(int,(0,1)),(str,["ON","OFF"])],"status")
        if status:
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
            func=self.enforce_type_and_range(func,(str,self.function_map.keys()),"function")
            self.channels[0].function=(func,self.function_map[func])
        else:
            return self.channels[0].function[0]

    def calculate_freq_range(self):
        func_str=self.channels[0].function[0]
        return freq_ranges[func_str]
            
    def calculate_amp_range(self):
        return (0,2*(self.max_voltage-abs(self.channels[0].offset)))
        
    def calculate_offs_range(self):
        abs_val=(self.max_voltage-(self.channels[0].amplitude/2.0))
        return (-1*abs_val,abs_val)
            
            
                    
