from ..simulated_signals import SimulatedOutputSignal
    

__all__=["SimulatedPiezoPMTOutputSignal"]
class SimulatedPiezoPMTOutputSignal(SimulatedOutputSignal):

    def __init__(self):
        super().__init__()
        self.current_voltage=0.0
    
    @property
    def voltage(self):
        return self.current_voltage
    
    @voltage.setter
    def voltage(self,val):
        self.current_voltage=val
        self.update_signal_function()
    
        
    def generate_constant_signal_func(self,voltage):
        return (lambda times: np.full(len(times),voltage))
        
        
    def calculate_signal_function(self):
        return self.generate_constant_signal_func(self.current_voltage)
