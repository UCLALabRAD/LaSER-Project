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
            






class SimulatedInputSignal(object):

    def __init__(self,record_time_length,points_in_memory):
        self.input_signal_log=None
        self.is_on=False
        self.record_time_length=record_time_length
        self.points_in_memory=points_in_memory

    def plug_in(self,outSignal):
        if self.input_signal_log or outSignal.output_signal_log.record_time_length:
            raise CableError()
        self.input_signal_log=outSignal.output_signal_log
        self.input_signal_log.record_time_length=self.record_time_length
        outSignal.update_signal_function()
        
        
        
        
        
    def unplug(self):
        if not self.input_signal_log:
            raise CableError()
        self.input_signal_log.record_time_length=None
        self.input_signal_log.erase_log()
        self.input_signal_log=None
        
            
           
    def generate_waveform(self,horiz_scale,horiz_pos, vert_scale,vert_pos):
        if not self.is_on or (not self.input_signal_log):
            return None
        window_horiz_start=horiz_pos+(self.record_time_length/2.0)-(horiz_scale*5)
        window_horiz_end=horiz_pos+(self.record_time_length/2.0)+(horiz_scale*5)
        window_vert_start=vert_scale*(-4)
        window_vert_end=4*vert_scale
        current_time=time.time()
        record_start_time=current_time-self.record_time_length
        self.input_signal_log.lock.acquire()
        self.input_signal_log.clip_record()
        record=[((self.input_signal_log.log[i][0]-record_start_time),self.input_signal_log.log[i][1]) for i in range(len(self.input_signal_log.log))]
        self.input_signal_log.lock.release()
        
        if (not record) or (record[0][0]>0.0):
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
                waveform.extend((seg[1](arr-seg[0])+vert_pos).clip(window_vert_start,window_vert_end))
        return waveform

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

