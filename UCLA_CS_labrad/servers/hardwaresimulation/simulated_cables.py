import time
import numpy as np
from scipy import signal
import threading
class SimulatedOutSignal(object):
    
    def __init__(self):
        self.currently_outputting=False
        self.output_signal_log=SignalLog()
        self.current_signal_function=None

    def update_signal_function(self):
        self.current_signal_function=self.calculate_signal_function()
        if self.currently_outputting:
            self.output_signal_log.update(self.current_signal_function)
    
    @property
    def outputting(self):
        return self.currently_outputting
        
    @outputting.setter
    def outputting(self,val):
        was_outputting=self.currently_outputting
        self.currently_outputting=val
        if self.currently_outputting!=was_outputting:
            if self.currently_outputting:
                self.output_signal_log.update(self.current_signal_function)
            else:
                self.output_signal_log.update(None)
            

class SimulatedPiezoPMTSignal(SimulatedOutSignal):

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
    
class SimulatedFunctionGeneratorSignal(SimulatedOutSignal):
    def __init__(self):
        super().__init__()
        self.current_function="SIN"
        self.current_frequency=1.0
        self.current_amplitude=1.0
        self.current_offset=0.0
        
        
    def generate_periodic_signal_func(self,function,frequency,amplitude,offset):
        scipy_func=None
        if function=="SIN":
            scipy_func=np.sin
        elif function=="SQU":
            scipy_func=signal.square #duty supported
        elif function=="RAMP":
            scipy_func=signal.sawtooth #symmetry supported
        elif function=="PULS":
            pass
        elif function=="NOIS":
            pass
        elif function=="DC":
            pass
        else:
            pass
        return (lambda arr: (scipy_func((2*np.pi*frequency*arr)-offset))*amplitude)
        
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
    
    
class SignalLog(object):
    def __init__(self):
        self.lock=threading.Lock()
        self.log=[]
        self.record_time_length=None

    def update(self, new_func):
        if not self.record_time_length:
            return
        self.lock.acquire()
        current_time=time.time()
        self.log.append((current_time,new_func))
        self.clip_record()
        self.lock.release()
        
        
        
    def clip_record(self):
        first_record_starting_in_window=len(self.log)
        current_time=time.time()
        for i in range(len(self.log)):
            if self.log[i][0]>(current_time-self.record_time_length):
                first_record_starting_in_window=i
                break
        
        last_record_starting_before_window=first_record_starting_in_window-1
        if last_record_starting_before_window<0:
            pass
        else:
            self.log=self.log[last_record_starting_before_window:]
            
    
    def erase_log(self):
        self.log=[]





class SimulatedInSignal(object):

    def __init__(self,record_time_length,points_in_memory):
        self.input_signal_log=None
        self.is_on=False
        self.record_time_length=record_time_length
        self.points_in_memory=points_in_memory

    def plug_in(self,outSignal):
        self.input_signal_log=outSignal.output_signal_log
        self.input_signal_log.record_time_length=self.record_time_length
        outSignal.update_signal_function()
        
        
        
        
        
    def unplug(self):
        self.input_signal_log.record_time_length=None
        self.input_signal_log.erase_log()
        self.input_signal_log=None
        
            
           
    def generate_waveform(self,horiz_scale,horiz_pos, vert_scale):#,vert_pos):
        if not self.is_on or (not self.input_signal_log):
            return None
            
        window_horiz_start=horiz_pos+(self.record_time_length/2.0)-(horiz_scale*5)
        window_horiz_end=horiz_pos+(self.record_time_length/2.0)+(horiz_scale*5)
        window_vert_start=vert_scale*(-5)
        window_vert_end=5*vert_scale
        current_time=time.time()
        record_start_time=current_time-self.record_time_length
        self.input_signal_log.lock.acquire()
        self.input_signal_log.clip_record()
        record=[((self.input_signal_log.log[i][0]-record_start_time),self.input_signal_log.log[i][1]) for i in range(len(self.input_signal_log.log))]
        self.input_signal_log.lock.release()
        if (record[0][0]>0.0):
            record.insert(0,(0.0,None))
        x_vals=np.linspace(window_horiz_start,window_horiz_end,self.points_in_memory)
        split_points=[rec[0] for rec in record]
        split_indices=np.searchsorted(x_vals,split_points,'left')
        func_app_list=np.array_split(x_vals,split_indices)[1:]
        waveform=[]
        for seg,arr in zip(record,func_app_list):
            if not seg[1]:
                waveform.extend(np.zeros(len(arr)))
            else:
                waveform.extend(seg[1](arr-seg[0]).clip(window_vert_start,window_vert_end))
        return waveform
