from ..simulated_signals import SimulatedOutputSignal
import numpy as np
__all__=["SimulatedFunctionGeneratorOutputSignal"]
class SimulatedFunctionGeneratorOutputSignal(SimulatedOutputSignal):
    def __init__(self):
        super().__init__()
        self.current_function="SIN"
        self.current_frequency=1.0
        self.current_amplitude=1.0
        self.current_offset=0.0
        
        
    def generate_periodic_signal_func(self,func,frequency,amplitude,offset):
        return (lambda arr: (func((2*np.pi*frequency*arr)-offset))*amplitude)
        
    def calculate_signal_function(self):
        return self.generate_periodic_signal_func(self.function,self.frequency,self.amplitude,self.offset)
       
        
    @property
    def function(self):
        return self.current_function
        
    @function.setter
    def function(self,val):
        self.current_function=val
        self.update_signal_function()
        
    @property
    def frequency(self):
        return self.current_frequency
        
    @frequency.setter
    def frequency(self,val):
        self.current_frequency=val
        self.update_signal_function()
            
    @property
    def amplitude(self):
        return self.current_amplitude
        
    @amplitude.setter
    def amplitude(self,val):
        self.current_amplitude=val
        self.update_signal_function()
            
    @property
    def offset(self):
        return self.current_offset
        
    @offset.setter
    def offset(self,val):
        self.current_offset=val
        self.update_signal_function()
    
    
