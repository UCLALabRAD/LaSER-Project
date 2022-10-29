class SimulatedOutSignal(object):
    
    def __init__(self,dev,channel):
        self.dev=dev
        self.channel=channel
        self.currently_outputting=False
        self.signal_log=SignalLog()
        self.current_signal_function=None

    def calculate_signal_function(self):
        return None

    def update_signal_function(self):
        self.current_signal_function=self.calculate_signal_function()
        if self.currently_outputting:
            self.signal_log.update((self.current_signal_function))

    @property
    def outputting(self,val):
        was_outputting=self.currently_outputting
        self.currently_outputting=val
        if self.currently_outputting!=was_outputting:
            if self.currently_outputting:
                self.signal_log.update(self.current_signal_function)
            else:
                self.signal_log.update(None,time.time())
            

class SimulatedPiezoPMTSignal(SimulatedOutSignal):
    def generate_constant_signal_func(self,voltage):
        return (lambda times: np.full(len(times),voltage))
        
    def calculate_signal_function(self):
        return self.generate_constant_signal_func(self.dev.channels[self.channel-1])
    
    
        
    
    
class SignalLog(object):
    def __init__(self):
        self.log=[]
        self.record_time_length=None
        #self.lock needed???
        
    def update(self, new_func):
        if not self.record_time_length:
            return
        current_time=time.time()
        self.log.append((new_func,current_time))
        self.clip_record()
        
    def clip_record(self):
        first_record_starting_in_window=len(self.log)-1
        
        for i in len(self.log):
            if self.log[i].time>(current_time-self.record_time_length):
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

    def plug_in(self,outSignal):
        self.input_signal_log=outSignal.output_signal_log
        self.input_signal_log.record_time_length=self.record_time_length
        outSignal.update_signal_function()
        
        
        
        
    def unplug(self):
        self.input_signal_log.record_time_length=None
        self.input_signal_log.erase_log()
        self.input_signal_log=None
        
            
           
    def generate_waveform(self,horiz_scale,horiz_pos, vert_scale,vert_pos):
        if not self.is_on:
            return None
        window_horiz_start=horiz_pos-(horiz_scale*5)
        window_horiz_end=horiz_pos+(horiz_scale*5)
        window_vert_start=
        window_vert_end=
        current_time=time.time()
        record_start_time=current_time-self.record_time_length
        if self.input_signal_log[0].start_time > record_start_time:
            #hasnt been running long enough
        record=[((self.input_signal_log[i].start_time-record_start_time),self.input_signal_log[i].func) for i in range(len(self.input_signal_log))]
        
        x_vals=np.linspace(window_start,window_end,memory_length)
        split_points=[rec.start_time for rec in log]
        split_indices=np.searchsorted(x_vals,split_points,'left')
        func_app_list=np.array_split(x_vals,split_indices)
        waveform=[]
        for record,arr in zip(rec,func_app_list):
            waveform.extend(record.func(arr-record_start_time).clip(window_vert_start,window_vert_end))
    
        return waveform
