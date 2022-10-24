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
        (":MEAS:VAV?",1) : self.measure_average
        (":MEAS:FREQ?",1) : self.measure_frequency,
        (":AUT",0) : self.autoscale)
        self.current_horizontal_scale=5
        self.total_time=10*self.current_horizontal_scale
        self.channels=[]
        self.sample_storage=[np.zeros(100)]*4
        self.sampling_rate=self.total_time/len(self.sample_storage[0])
        self.samplers=[]
        
        for i in range(4):
            self.channels.append(SimulatedInSignal())
            self.samplers.append(self.Sampler(self.channels[i],self.sample_storage[i]))
            

    def display_measurement(display_section,channel,measurement):
        pass
        
    @inlineCallbacks   
    def measure_average(self,chan):
        chan=int(chan[:-1])
        yield self.samplers[chan].capture()
        returnValue(np.average(self.sample_storage))
    
    @inlineCallbacks
    def measure_frequency(self,chan):
        
        chan=int(chan[:-1])
        yield self.samplers[chan].capture()
        max=np.amax(self.sample_storage)
        min=np.amin(self.sample_storage)
        halfway=(max+min)/2.0
        crosses=0
        above=False
        first_cross=None
        last_cross=None
        if self.sample_storage[0]>=halfway:
            above=True
        for i in range(1000):
            if (above!=(self.sample_storage[i]>=halfway)):
                above=(not above)
                if above:
                    if (not first_cross):
                       first_cross=i
                    else:
                       crosses=crosses+1
                    last_cross=i
                
        
        
        returnValue(crosses/(self.total_time*(last_cross-first_cross)/1000.0))
        
    
        
    
    def autoscale(self):
    #change scales,trigger, positions
        pass
    
    
    class SamplingLoopingCall(self):
        def __init__(self,channel,sample_storage):
            self.current_sample=0
            self.looping_call=LoopingCall(self.sample_voltage)
            self.sample_storage=sample_storage
        def sample_voltage(self):
            self.sample_storage[self.current_sample]=channel.incoming_voltage
            self.current_sample=self.current_sample+1
            if self.current_sample>=len(self.sample_storage):
                self.current_sample=0
                self.looping_call.stop()
        @inlineCallbacks
        def capture(self,sampling_rate):
            yield self.looping_call.start(sampling_rate)
            
    
    
    
        

    
    
            
            
            
            
                    
