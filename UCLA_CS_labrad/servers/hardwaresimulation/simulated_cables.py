class SimulatedOutSignal(object):
    def __init__(self,dev,channel):
        self.dev=dev
        self.channel=channel
        self.outputting=False

    def calculate_voltage_value(self):
        return None

    def calculate_current_value(self):
        return None
        
    
    


class SimulatedPiezoPMTSignal(SimulatedOutSignal):
    def __init__(self,dev,channel):
    	super().__init__(dev,channel)
    
    def calculate_voltage_value(self):
        if self.outputting:
    	    return self.dev.voltages[channel-1]
        else:
            return 0.0


class SimulatedInSignal(object):

    def __init__(self):
    	self.get_signal_voltage=lambda:0.0
    	self.get_signal_current=lambda:0.0

    def plug_in(self,outSignal):
        self.get_signal_voltage=outSignal.calculate_voltage_value
        self.get_signal_current=outSignal.calculate_current_value
        
    def unplug(self):
        self.get_signal_voltage=lambda:0.0
        self.get_signal_current=lambda:0.0

    @property
    def incoming_voltage(self):
        return self.get_signal_voltage()

    @property
    def incoming_current(self):
        return self.get_signal_current()
