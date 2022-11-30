from ..simulated_signals import SimulatedOutputSignal
import numpy as np

__all__=["SimulatedPiezoOutputSignal"]


class SimulatedPiezoOutputSignal(SimulatedOutputSignal):

    def initialize_signal_properties(self):
        super().initialize_signal_properties()
        self.voltage_val=0.0    
    
    @property
    def voltage(self):
        return self.voltage_val
    
    @voltage.setter
    def voltage(self,val):
        self.voltage_val=val
        self.update_signal()
    
        
    def generate_constant_func(self,voltage):
        return (lambda times: np.full(len(times),voltage))
        
        
    def calculate_signal(self):
        return self.generate_constant_func(self.voltage_val)
