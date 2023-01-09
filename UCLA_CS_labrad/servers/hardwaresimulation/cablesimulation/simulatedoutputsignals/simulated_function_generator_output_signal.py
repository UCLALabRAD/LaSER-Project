from ..simulated_signals import SimulatedOutputSignal
import numpy as np
__all__=["SimulatedFunctionGeneratorOutputSignal"]

#output channel class for function generators
class SimulatedFunctionGeneratorOutputSignal(SimulatedOutputSignal):

    def initialize_signal_properties(self):
        super().initialize_signal_properties()
        #declare instance attributes of channel (see initialize_signal_properties in SimulatedOutputSignal)
        
        #model specific
        self.function_val=None
        self.amplitude_val=None
        self.frequency_val=None
        
        #example of a hardcoded default value: by default there's no dc offset no
        # matter the function generator value
        self.offset_val=0.0
        
        
    
    def generate_periodic_signal_func(self,func,frequency,amplitude,offset):
        return (lambda arr: (func((2*np.pi*frequency*arr)))*amplitude+offset)
    
    #See calculate_signal comment in SimulatedOutputSignal.
    #we write a lambda function and return it. This lambda function takes in a numpy array
    #input, multiplies it by 2*pi, applies the function currently stored by the “function” property
    #(which will be vectorized), multiplies the result by the signal’s amplitude,
    #and adds the “offset” property to every value in the array,
    #resulting in an electrical signal with the correct properties
    def calculate_signal(self):
        return self.generate_periodic_signal_func(self.function[1],self.frequency,self.amplitude,self.offset)
      
      
    #see comment for calculate_signal in SimulatedOutputSignal for info about property getters and setters
     
     
    #output signal properties are the waveform shape (function), the frequency, the amplitude, and the DC offset
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
    
    
