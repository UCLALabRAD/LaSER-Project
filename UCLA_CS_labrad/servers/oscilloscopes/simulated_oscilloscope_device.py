from UCLA_CS_labrad.servers.hardwaresimulation.sim_instr_models import GPIBDeviceModel

from UCLA_CS_labrad.servers.hardwaresimulation.simulated_cables import SimulatedInSignal

from twisted.internet.threads import deferToThread
from twisted.internet.task import LoopingCall
from twisted.internet.defer import inlineCallbacks, returnValue
from labrad.errors import Error
import time
import numpy as np

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
        (":MEAS:VAV?",1) : self.measure_average,
        (":MEAS:FREQ?",1) : self.measure_frequency,
        (":AUT",0) : self.autoscale }
        self.current_horizontal_scale=5
        self.total_time=10*self.current_horizontal_scale
        self.channels=[]
        self.sample_storage=[np.zeros(100)]*4
        self.sampling_rate=self.total_time/(len(self.sample_storage[0]))
        self.samplers=[]
        
        for i in range(4):
            self.channels.append(SimulatedInSignal())
            self.samplers.append(self.ThreadSampler(self.channels[i],self.sample_storage[i]))
            

    def display_measurement(display_section,channel,measurement):
        pass
        
    @inlineCallbacks   
    def measure_average(self,chan):
        chan=int(chan[-1])
        yield self.samplers[chan-1].capture(self.sampling_rate)
        returnValue(str(np.average(self.sample_storage[chan-1])))
    
    @inlineCallbacks
    def measure_frequency(self,chan):
        
        chan=int(chan[-1])
        yield self.samplers[chan-1].capture(self.sampling_rate)
        max=np.amax(self.sample_storage[chan-1])
        min=np.amin(self.sample_storage[chan-1])
        halfway=(max+min)/2.0
        print(halfway)
        crosses=0
        above=False
        first_cross=None
        last_cross=None
        if self.sample_storage[chan-1][0]>=halfway:
            above=True
        for i in range(100):
            if (above!=(self.sample_storage[chan-1][i]>=halfway)):
                above=(not above)
                if above:
                    if (not first_cross):
                       first_cross=i
                    else:
                       crosses=crosses+1
                    last_cross=i
                
        
        
        returnValue(str(crosses/(self.total_time*(last_cross-first_cross)/100.0)))
        
    
        
    
    def autoscale(self):
    #change scales,trigger, positions
        pass
    
    
    class ReactorSampler(object):
        def __init__(self,channel,sample_storage):
            self.current_sample=0
            self.looping_call=LoopingCall(self.sample_voltage)
            self.sample_storage=sample_storage
            self.channel=channel
        def sample_voltage(self):
            self.sample_storage[self.current_sample]=self.channel.incoming_voltage
            self.current_sample=self.current_sample+1
            if self.current_sample>=len(self.sample_storage):
                self.current_sample=0
                self.looping_call.stop()
                
        @inlineCallbacks
        def capture(self,sampling_rate):
            yield self.looping_call.start(sampling_rate)
            
    class ThreadSampler(object):
        def __init__(self,channel,sample_storage):
            self.sample_storage=sample_storage
            self.channel=channel
        def collect_voltage_data(self,sample_rate):
            for i in range(len(self.sample_storage)):
                self.sample_storage[i]=self.channel.incoming_voltage
                time.sleep(sample_rate)
        @inlineCallbacks
        def capture(self,sample_rate):
            yield deferToThread(self.collect_voltage_data,sample_rate)
            
    
    
    
        

    
    
            
            
            
            
                    
