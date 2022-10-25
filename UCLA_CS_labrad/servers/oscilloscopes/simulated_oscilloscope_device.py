from UCLA_CS_labrad.servers.hardwaresimulation.sim_instr_models import GPIBDeviceModel

from UCLA_CS_labrad.servers.hardwaresimulation.simulated_cables import SimulatedInSignal

from twisted.internet.threads import deferToThread
from twisted.internet.task import LoopingCall
from twisted.internet.defer import inlineCallbacks, returnValue
from labrad.errors import Error
import time
import numpy as np
#penny CS GPIB Bus - USB0::0x0957::0x1796::MY58104761::INSTR
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
        (":AUT",0) : self.autoscale,
        (":TOGG",2) : self.toggle_channel,
        (":TOGG?",1) : self.toggle_channel
        }
        self.current_horizontal_scale=.01
        self.total_time=10*self.current_horizontal_scale
        self.channels=[]
        self.sample_storage=[np.zeros(1000)]*4
        self.sampling_period=self.total_time/(len(self.sample_storage[0]))
        self.samplers=[]
        self.channel_toggled_on=[False]*4
        for i in range(4):
            self.channels.append(SimulatedInSignal())
            self.samplers.append(self.ThreadSampler(self.channels[i],self.sample_storage[i]))
            
    def toggle_channel(self,channel,val=None):
        if val:
            self.channel_toggled_on[int(channel)-1]=bool(int(val))
        return str(int(self.channel_toggled_on[int(channel)-1]))
    def display_measurement(display_section,channel,measurement):
        pass
        
    @inlineCallbacks   
    def measure_average(self,chan):
        chan=int(chan[-1])
        yield self.samplers[chan-1].capture(self.sampling_period)
        returnValue(str(np.average(self.sample_storage[chan-1])))
    
    @inlineCallbacks
    def measure_frequency(self,chan):
        chan=int(chan[-1])
        yield self.samplers[chan-1].capture(self.sampling_period)
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
        for i in range(1000):
            if (above!=(self.sample_storage[chan-1][i]>=halfway)):
                above=(not above)
                if above:
                    if (not first_cross):
                       first_cross=i
                    else:
                       crosses=crosses+1
                    last_cross=i
                
        
        
        returnValue(str(crosses/(self.total_time*(last_cross-first_cross)/1000.0)))
        
    
        
    
    def autoscale(self):
    #change scales,trigger, positions
        return "nice"
    
    
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
        def capture(self,sampling_period):
            yield self.looping_call.start(sampling_period)
            
    class ThreadSampler(object):
        def __init__(self,channel,sample_storage):
            self.sample_storage=sample_storage
            self.channel=channel
        def collect_voltage_data(self,sample_period):
            for i in range(len(self.sample_storage)):
                self.sample_storage[i]=self.channel.incoming_voltage
                time.sleep(sample_period)
        @inlineCallbacks
        def capture(self,sample_period):
            yield deferToThread(self.collect_voltage_data,sample_period)
            
    
    
    
        

    
    
            
            
            
            
                    
