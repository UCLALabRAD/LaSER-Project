import time
import numpy as np
from scipy import signal
import threading

__all__=["SimulatedOutputSignal","SimulatedInputSignal"]

#Type of HSS error, but couldn't raise HSS error here due to circular import TODO: fix structure of package so can make this one of the HSS errors?
class CableError(Exception):
    def __init__(self):
        super().__init__()
    
#Stores basic output channel properties, properties of the current output signal,
#and a log containing a history of changes to the output signal.
class SimulatedOutputSignal(object):
    
    def __init__(self):
        self.output_signal_log=SignalLog() #log describing the history of channel's output signal
        self.initialize_signal_properties() #TODO: this shouldn't need to be here anymore, will look into it further
        
    #Meant to be extended to allow generic-device-writers to declare object variables of their OutputSignal
    #subclass when writing the code for the generic device's channels. These object variables
    #represent the properties each channel of the generic instrument has (usually output signal properties), which can be set to new values in Serial/GPIB
    #command-handling functions in the generic simulated device class (representing the handling of a command causing
    #some sort of change in one of the device's output channels).
    #When extending, these new object variables can either be defined in order to initialize the property to a hardcoded default value universal
    #to all instrument models for that instrument type, or set to None if the default value is specific to instrument models.
    #This is automatically called for all channels on a device when the device's set_default_settings is called, after
    # which set_default_settings defines the properties specific to instrument models that were set to None here.
    def initialize_signal_properties(self):
        self.current_output_function=None #starts by outputting nothing
        self.outputting_val=False #channel initially off
        

    # This is to be called any time an object property declared in initialize_signal_properties is changed when handling a command written to the
    # simulated device. It updates the current signal output function of the channel based on the calculate_signal function written by the
    # generic-device-writer in their OutputSignal subclass. If the channel is currently outputting, it also updates the channel's SignalLog
    # accordingly to reflect the change in the output signal. Currently this requires the generic-device-writer that is subclassing OutputSignal to
    # use a format where for each signal property, say ‘exampleproperty’, the OutputSignal subclass would need to have an object variable called
    # exampleproperty_val and two property-decorated functions, an “exampleproperty getter” and an “exampleproperty setter”.
    # The getter would return the value of exampleproperty_val, and the setter would set exampleproperty_val but also call update_signal right
    #after. Then, when a generic device method sets a signal property of a channel to a new value, its SignalLog would automatically be updated
    #with the new signal- simulating the signal going across the simulated cable changing!
    # TODO: There should be a way to make these property-decorated functions be added to the OutputSignal
    # subclass automatically for each signal property defined in initialize_signal_properties
    def update_signal(self):
        self.current_output_function=self.calculate_signal()
        if self.outputting_val:
            self.output_signal_log.update(self.current_output_function)
    
    
    #we use Python’s property decorator to write an “outputting property getter” and “outputting property setter” for the OutputSignal
    @property
    def outputting(self):
        return self.outputting_val #get whether channel is outputting
        
    # When the channel is turned on or off, we need to directly update the SignalLog accordingly (bypassing update_signal in just this one case).
    # This is because one can change output signal properties for a channel (and thus the current_output_function) even when then channel is not outputting,
    # to specify what the output signal should be once the channel is turned on.
    @outputting.setter
    def outputting(self,val):
        was_outputting=self.outputting_val
        self.outputting_val=val #update whether channel is outputting
        if self.outputting_val!=was_outputting:
            if self.outputting_val:
                self.output_signal_log.update(self.current_output_function)
                #if it was turned on, we should pass the stored current_output_function to the SignalLog’s update function
            else:
                self.output_signal_log.update(None)
                #if it was turned off, we should pass None to the SignalLog’s update function
                #(to represent no signal)
            
            
    ##written by the generic-device-writer in their OutputSignal subclass when writing the code for the generic
    #device's channels. calculates the current output signal function based on the current values of the object variables
    #that were declared in initialize_signal_properties
    def calculate_signal(self):
        pass





#Represents the properties of an input channel and allows the signal-receiving device to construct the input signal’s waveforms
# by sampling the received voltage over time.
class SimulatedInputSignal(object):

    def __init__(self,max_dev_waveform_duration):
        self.input_signal_log=None #will store a SignalLog received from an output channel when a cable connected to this channel.
        self.is_on=False #channel starts as off upon device initialization
        self.max_dev_waveform_duration=max_dev_waveform_duration #longest possible duration waveform the device will want to construct from this channel

    # plug_in grabs a reference to the OutputSignal’s SignalLog, and assigns it to the InputSignal’s input_signal_log variable.
    # It also changes a property of the SignalLog specifying how much history the log should cover called log_duration, based on the
    # longest-lasting waveform the input device may want to construct, which is stored in the InputSignal’s dev_max_waveform_duration object
    # property. Changing this property in the  SignalLog (which is None when the output channel is not connected to any input channel) to ‘x’
    # indicates to the OutputSignal that it needed to start constantly maintaining a log somehow specifying any signals
    # it was sending from x seconds ago, to the current time.
    def plug_in(self,outSignal):
        if self.input_signal_log or outSignal.output_signal_log.log_duration:
            raise CableError() #a different cable is already plugged in to either this input channel or the output channel outSignal
        self.input_signal_log=outSignal.output_signal_log
        self.input_signal_log.log_duration=self.max_dev_waveform_duration
        outSignal.update_signal()
        #output channel's signal log first entry needs to be added to reflect its current output function (assuming the output channel is on)
        # since log empty prior to cable connection
        #TODO: maybe this is being nitpicky, but this essentially forces t=0 for the output function upon connection to be the time of connection
        #when in reality, I think t=0 is whenever the new output function is set. maybe this should be fixed?
        
        
        
        
        
    
    def unplug(self):
        if not self.input_signal_log:
            raise CableError() #no cable was plugged in
        self.input_signal_log.log_duration=None
        self.input_signal_log.erase_log()
        self.input_signal_log=None
        
            
    #constructs waveform from input signal log.
    #construct_waveform takes in four values that represent a portion of the SignalLog to capture in the waveform:
    # a duration d, a signal vertical offset, a minimum voltage, and a maximum voltage.
    # If the log is maintained to always cover a history of x seconds, x seconds ago will be treated as t=0, the current time will be treated as t=x,
    # and the time window to sample from will be from t=(x-d) to t=x (the last d seconds).
    # The record length property represents the number of samples that should be taken to construct the waveform, based on how much memory the instrument
    # has, and for a constant record length there’s a tradeoff: if the duration of the waveform is too short, important
    # properties of the output signals in the SignalLog may be missed (for example, a short spike in voltage). But on the other hand,
    # if it is too large, the time difference between samples becomes large and the generated waveform becomes less precise,
    # especially if one of the electrical signals in the log has a high frequency.
    def construct_waveform(self, duration, vert_pos, min_voltage, max_voltage,points_in_waveform):
        if not self.is_on or (not self.input_signal_log):
            return None #no cable plugged in or channel is off, so waveform is flat at v=0 for the entire duration, which we represent w/ None
            
        window_horiz_start=self.input_signal_log.log_duration-duration
        window_horiz_end=self.input_signal_log.log_duration
        window_vert_start=min_voltage
        window_vert_end=max_voltage
        
        #The first step in construct_waveform is to make a record out of the SignalLog.
        #This is exactly the same format as the log (a list of 2-tuples) except that the timestamps are changed
        #to be relative to x seconds before the current time.
        current_time=time.time()
        record_start_time=current_time-self.input_signal_log.log_duration
        self.input_signal_log.lock.acquire()
        self.input_signal_log.clip_record()
        record=[((self.input_signal_log.log[i][0]-record_start_time),self.input_signal_log.log[i][1]) for i in range(len(self.input_signal_log.log))]
        self.input_signal_log.lock.release()
        
        #Because of how the log is clipped, this means that the new time values in the tuples will be between 0 and x,
        # except for the very first one, which can be negative. If the first time is not negative, this means the
        # cable hasn’t been connected for x seconds yet, so we prepend a new entry to the log starting at t=0 with None as the function (no signal).
        #If the first entry’s time is negative, we don’t change that time to 0, because as we recall at the time an entry of function
        # f is logged, the voltage being received is f(0), so changing the start time would incorrectly horizontally shift that
        # input signal function to the right.
        if (not record) or (record[0][0]>0.0):
            record.insert(0,(0.0,None))
       
        #create a numpy array of length record_length of equally spaced time values between the start time x-d and the end time x
        x_vals=np.linspace(window_horiz_start,window_horiz_end,points_in_waveform)
        
        #split these time values into sub-arrays corresponding to which signal function in the SignalLog
        #was being used to generate the input voltage at that time
        split_points=[rec[0] for rec in record]
        split_indices=np.searchsorted(x_vals,split_points,'left')
        func_app_list=np.array_split(x_vals,split_indices)[1:]
        
        #Consider a sub-array of time values where the input voltage was being generated by signal function f.
        #We subtract each time value within the sub-array by the time the function f’s log entry was made, since the time
        #the entry was made represents f(0) (the start of the signal). We then apply the function f to the sub-array
        #(remembering that it takes in an array of times and outputs an array of voltages of equal length, so we can take
        #advantage of some of the vectorized numpy and scipy functions), mapping each time value to get the input voltage
        #value at that time. We add the value of the vertical offset argument to each output and then clip any values not
        #between the min and max voltages provided in the arguments, so any value less than (greater than) the min (max)
        #will be set to the min (max). Then, we glue all the mapped sub-arrays back together in order to get a full numpy array waveform, and return it.
        waveform=[]
        for seg,arr in zip(record,func_app_list):
            if not seg[1]:
                waveform.extend(np.zeros(len(arr)))# Note that if f is None, we just apply a function that always outputs an array of all zeroes
            else:
                waveform.extend((seg[1](arr-seg[0])+vert_pos).clip(window_vert_start,window_vert_end))
        return waveform

#Log representing the signals the channel has output covering a historical time span, which discards outdated information about the output signal.
#Each output channel of a simulated instrument has one of these.
#When a simulated cable is used to connect an output channel of one device to an input channel of another, the SignalLog is shared with the simulated
# input channel- the output channel can read and write to it, while the input channel can only read from it (except for during the
# process of connecting or disconnecting, then it can write).
# automatically updated when any properties of the output signal change.
class SignalLog(object):
    def __init__(self):
        self.lock=threading.Lock()
        #once we allowed for electrical signals to be sent between simulated devices we had the issue of shared SignalLogs
        #between two devices being accessed by two threads at the same time.
        #We cannot use Deferred or callback logic in any simulated-device related code, which includes the InputSignals, OutputSignals, and SignalLogs,
        #because this code is being run in non-reactor threads. So we give each SignalLog object its own normal mutex lock
        #used for typical multithreading. This lock must be acquired and released whenever the SignalLog is edited.
        #Where things get a bit tricky is that one must be quite careful using mutex locks in these threads because Twisted maintains a thread pool
        #that is only so large, and a deadlock or anything of that sort can cause multiple threads to be lost until the server is restarted,
        #in addition to leaving any client who tries to use the device blocked forever.

        self.log=[]
        # list of tuples representing changes to the function used to calculate the voltage being output (and thus changes to the output signal).
        # Each tuple consists of two values: first, a timestamp as to when the entry was made in the log, and second,
        # a function taking in a numpy array of time inputs and generating a numpy array of corresponding voltage outputs,
        # representing the new function that at that timestamp started to be used to calculate the output voltage
        # (with the starting time being 0 on the function’s x-axis, or the start of the signal).
        # Log starts off empty, will stay empty until connected to an input channel.
        
        
        self.log_duration=None #no duration until connected to an input channel

    def update(self, new_func):
        if not self.log_duration:
            return
            #first checks if the channel has a simulated cable plugged into it, because if not nothing needs to be done and it can just return.
            #It checks this by seeing if the log_duration variable indicating how long the record should be (in terms of historical time covered) is set to None;
            
        self.lock.acquire()
        current_time=time.time()
        
        #if so, no cable is plugged into this output channel. Otherwise, we have to update the SignalLog’s list of 2-tuples.
        # We do so, creating a timestamp and adding a new tuple with this time and the new output signal function.
        self.log.append((current_time,new_func))
        
        #get rid of outdated output signal info
        self.clip_record()

        self.lock.release()
        
        
    #if the log should be of historical time length ‘x’ (represented by log_duration received from input channel),
    #we remove all entries in the log except for all the ones with timestamps indicating they were added less than x seconds ago.
    #However, we also need to include the most recent entry that was added more than x seconds ago if such an entry exists,
    #because otherwise we have lost the output signal function between x seconds ago and the time of the oldest entry that
    #was added less than x seconds ago.
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
            
    #called when simulated cable disconnected from this channel
    def erase_log(self):
        self.log=[]

