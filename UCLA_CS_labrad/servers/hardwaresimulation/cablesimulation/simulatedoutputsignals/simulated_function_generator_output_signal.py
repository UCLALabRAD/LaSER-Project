from ..simulated_signals import SimulatedOutputSignal
import numpy as np
__all__=["SimulatedFunctionGeneratorOutputSignal"]
class SimulatedFunctionGeneratorOutputSignal(SimulatedOutputSignal):

    def initialize_signal_properties(self):
        super().initialize_signal_properties()
        self.function_val=None
        self.amplitude_val=None
        self.frequency_val=None
        self.offset_val=0.0
        
        
    def generate_periodic_signal_func(self,func,frequency,amplitude,offset):
        return (lambda arr: (func((2*np.pi*frequency*arr)))*amplitude+offset)
        
    def calculate_signal(self):
        return self.generate_periodic_signal_func(self.function[1],self.frequency,self.amplitude,self.offset)
       
        
    @property
    def function(self):
        return self.function_val
        
    @function.setter
    def function(self,val):
        self.function_val=val
        self.update_signal()
        
    @property
    def frequency(self):
        return self.frequency_val
        
    @frequency.setter
    def frequency(self,val):
        self.frequency_val=val
        self.update_signal()
            
    @property
    def amplitude(self):
        return self.amplitude_val
        
    @amplitude.setter
    def amplitude(self,val):
        self.amplitude_val=val
        self.update_signal()
            
    @property
    def offset(self):
        return self.offset_val
        
    @offset.setter
    def offset(self,val):
        self.offset_val=val
        self.update_signal()
    
    
