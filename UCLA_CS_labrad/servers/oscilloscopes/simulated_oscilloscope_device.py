from UCLA_CS_labrad.servers.hardwaresimulation.sim_instr_models import GPIBDeviceModel

from UCLA_CS_labrad.servers.hardwaresimulation.simulated_cables import SimulatedInSignal
from labrad.errors import Error

#frequency,amplitude,toggle
class SimulatedKeysightDSOXADevice(GPIBDeviceModel):
    name= 'KeysightDSOX2024A'
    version = '1.0'
    description='Oscilloscope'
  
    def __init__(self):
        super().__init__()
        self.supports_command_chaining=True
        self.id_string='AGILENT TECHNOLOGIES,DSO-X 2024A,MY58104761,02.43.2018020635'
        self.command_dict={
        (":MEAS:VAV",1,False) : self.measure_average,
		(":MEAS:FREQ",1,False) : self.measure_frequency,
		(":AUT",0,False) : self.autoscale)
		self.measured_points=np.zeros(1000) #record length is a constant
		self.current_horizontal_scale=1
		self.total_time=10*self.current_horizontal_scale
        self.channels=[]
		self.sampling_rate=self.total_time/len(self.measured_points)
		self.sampler=LoopingCall.with_count(sample_voltage)
        for i in range(4):
            self.channels.append(SimulatedInSignal())

    def display_measurement(display_section,channel,measurement):
        pass
        
    def measure_average(self,chan):
	    chan=int(chan[:-1])
	    for i in range(len(measured_points))
		    #wait some amount of time
            self.measured_points[i]=self.channels[chan-1].incoming_voltage
		return np.average(measured_points)
		
	def measure_frequency(self,chan=None):
	    
		chan=int(chan[:-1])
        self.sampler.start(chan)
		max=np.amax(self.measured_points)
		min=np.amin(self.measured_points)
		halfway=(max+min)/2.0
		crosses=0
		above=False
		first_cross=None
		last_cross=None
		if self.measured_points[0]>=halfway:
		    above=True
		for i in range(1000):
		    if (above!=(self.measured_points[i]>=halfway)):
		        above=(not above)
				if above:
				    if (not first_cross):
					   first_cross=i
					else:
				       crosses=crosses+1
					last_cross=i
				
		
		
		return crosses/self.total_time*(last_cross-first_cross)/1000
		
	def sample_voltage(self,i,chan):
	    self.measured_points[i]=self.channels[chan-1].incoming_voltage
	    
	
	def autoscale(self):
	#change scales,trigger, positions
    
    
    
        

    
    
            
            
            
            
                    
