from ..simulated_signals import SimulatedOutputSignal
import numpy as np

__all__=["SimulatedPiezoOutputSignal"]

#output channel class for piezo boxes
class SimulatedPiezoOutputSignal(SimulatedOutputSignal):

    def initialize_signal_properties(self):
        super().initialize_signal_properties()
        
        #declare instance attributes of channel (see initialize_signal_properties in SimulatedOutputSignal)
        #example of a hardcoded default value: all channels on all piezo boxes will output 0 volts by default
        self.voltage_val=0.0
        
    #see comment for calculate_signal in SimulatedOutputSignal for info about property getters and setters
    
    #only output signal property is voltage
    @property
    def voltage(self):
        return self.voltage_val
    
    @voltage.setter
    def voltage(self,val):
        self.voltage_val=val
        self.update_signal()
    
        
    def generate_constant_func(self,voltage):
        return (lambda times: np.full(len(times),voltage))
        
    #See calculate_signal comment in SimulatedOutputSignal.
    #We return a function that takes in any numpy array and returns an equally-sized array where every value is the same-
    #the current value of the voltage property.
    def calculate_signal(self):
        return self.generate_constant_func(self.voltage_val)
