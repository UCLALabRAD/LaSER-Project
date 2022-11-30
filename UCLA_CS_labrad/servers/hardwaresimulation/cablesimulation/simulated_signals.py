import time
import numpy as np
from scipy import signal
import threading

__all__=["SimulatedOutputSignal","SimulatedInputSignal"]

class CableError(Exception):
    def __init__(self):
        super().__init__()
        
class SimulatedOutputSignal(object):
    
    def __init__(self):
        self.output_signal_log=SignalLog()
        self.initialize_signal_properties()
        
    def initialize_signal_properties(self):
        self.current_output_function=None
        self.outputting_val=False
        

    
    def update_signal(self):
        self.current_output_function=self.calculate_signal()
        if self.outputting_val:
            self.output_signal_log.update(self.current_output_function)
    
    @property
    def outputting(self):
        return self.outputting_val
        
    @outputting.setter
    def outputting(self,val):
        was_outputting=self.outputting_val
        self.outputting_val=val
        if self.outputting_val!=was_outputting:
            if self.outputting_val:
                self.output_signal_log.update(self.current_output_function)
            else:
                self.output_signal_log.update(None)
            
    def calculate_signal(self):
        pass





class SimulatedInputSignal(object):

    def __init__(self,max_dev_waveform_duration):
        self.input_signal_log=None
        self.is_on=False
        self.max_dev_waveform_duration=max_dev_waveform_duration


    def plug_in(self,outSignal):
        if self.input_signal_log or outSignal.output_signal_log.log_duration:
            raise CableError()
        self.input_signal_log=outSignal.output_signal_log
        self.input_signal_log.log_duration=self.max_dev_waveform_duration
        outSignal.update_signal()
        
        
        
        
        
    def unplug(self):
        if not self.input_signal_log:
            raise CableError()
        self.input_signal_log.log_duration=None
        self.input_signal_log.erase_log()
        self.input_signal_log=None
        
            
           
    def construct_waveform(self, duration, vert_pos, min_voltage, max_voltage,points_in_waveform):
        if not self.is_on or (not self.input_signal_log):
            return None
        window_horiz_start=self.input_signal_log.log_duration-duration
        window_horiz_end=self.input_signal_log.log_duration
        window_vert_start=min_voltage
        window_vert_end=max_voltage
        current_time=time.time()
        record_start_time=current_time-self.input_signal_log.log_duration
        self.input_signal_log.lock.acquire()
        self.input_signal_log.clip_record()
        record=[((self.input_signal_log.log[i][0]-record_start_time),self.input_signal_log.log[i][1]) for i in range(len(self.input_signal_log.log))]
        self.input_signal_log.lock.release()
        if (not record) or (record[0][0]>0.0):
            record.insert(0,(0.0,None))
        x_vals=np.linspace(window_horiz_start,window_horiz_end,points_in_waveform)
        split_points=[rec[0] for rec in record]
        split_indices=np.searchsorted(x_vals,split_points,'left')
        func_app_list=np.array_split(x_vals,split_indices)[1:]
        waveform=[]
        for seg,arr in zip(record,func_app_list):
            if not seg[1]:
                waveform.extend(np.zeros(len(arr)))
            else:
                waveform.extend((seg[1](arr-seg[0])+vert_pos).clip(window_vert_start,window_vert_end))
        return waveform

class SignalLog(object):
    def __init__(self):
        self.lock=threading.Lock()
        self.log=[]
        self.log_duration=None

    def update(self, new_func):
        if not self.log_duration:
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
            if self.log[i][0]>(current_time-self.log_duration):
                first_record_starting_in_window=i
                break
        
        last_record_starting_before_window=first_record_starting_in_window-1
        if last_record_starting_before_window<0:
            pass
        else:
            self.log=self.log[last_record_starting_before_window:]
            
    
    def erase_log(self):
        self.log=[]

