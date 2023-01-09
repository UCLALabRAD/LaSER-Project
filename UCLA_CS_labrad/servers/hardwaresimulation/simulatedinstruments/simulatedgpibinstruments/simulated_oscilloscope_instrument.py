from ..simulated_instruments import SimulatedGPIBInstrumentInterface, SimulatedInstrumentError
from UCLA_CS_labrad.servers.hardwaresimulation.cablesimulation.simulated_signals import SimulatedInputSignal


from twisted.internet.threads import deferToThread
from twisted.internet.task import LoopingCall
from twisted.internet.defer import inlineCallbacks, returnValue
from labrad.errors import Error
import time
import numpy as np

__all__=["SimulatedOscilloscopeInstrument","SimulatedOscilloscopeError"]

#Add new error messages specific to oscilloscope instruments here. See SimulatedInstrumentError
class SimulatedOscilloscopeError(SimulatedInstrumentError):
    user_defined_errors={}

#Generic device class for Simulated Oscilloscope Instrument.
#GPIB device with multiple input channels.

# An oscilloscope is used to take in electrical analog signals through its input channels
#and construct digital waveforms from them, as a display graphing the input voltages over time.
# For each channel, it has a constant number of input voltage values it can store and display on its screen at once
# called the record length. The screen has horizontal and vertical “divisions” which are set
# fractions of the total horizontal and vertical lengths of the screen. In order to change the
# amount of time the screen covers, an oscilloscope supports commands to change the scale of the
#horizontal divisions, and it also supports commands to change the scale of the vertical divisions
#for each channel separately, to stretch or compress the waves vertically. It also supports commands to offset
#the display of a channel vertically by adding a constant offset to each recorded electrical input
#signal. Each of these values can also be gotten using GPIB queries.

#There’s a tradeoff here: if the duration of the displayed waveform is too short, important properties of the output signals
#may be missed (for example, a short spike in voltage). But on the other hand, if it is too large, the time difference between
#samples becomes large and the generated waveform becomes less precise, especially if one of the input signals
#has a high frequency.

#In a real oscilloscope, the waveform is drawn using a triggered sweep: a channel and y-value are chosen
#as the “trigger” and whenever the voltage coming in through this channel crosses the y-value going up,
#the oscilloscope starts storing samples and the waveform starts to be drawn from left to right
#across the screen, until the right side of the screen is reached (then, a waveform has been “acquired”).
#However, for our simulated generic device we instead use what is called roll mode, which is only used
#by real oscilloscopes when the window horizontal scale is quite large. In a real oscilloscope, this mode constantly samples the input voltage and stores the
#input voltages received from x seconds ago to now, where x is the horizontal width of the screen,
#throwing away outdated values and constantly updating statistics about the waveform made up by the stored samples.



#We choose to mimic roll mode because it’s easier to implement than trigger sweep and because the
#point of trigger sweep is to stabilize the display, which is not an issue for us since as of yet we
#don’t have an actual display. Also, this mode allows us to take measurements on the "displayed" waveform
#without having to wait for the next sweep to complete.

#To avoid having to constantly take samples, we sample retroactively and construct the waveform when the user requests a
#measurement, using the SignalLog possessed by each input channel that has a cable connected.
#The input channel will be prepared to construct a waveform of even the longest possible duration since this is the duration
#the SignalLog covers (see InputSignal), but the duration used to construct consists of the last d seconds, where d is the width of the screen
#The instrument supports GPIB commands to make a calculation on the next acquired waveform and get the
#result, such as its average voltage or its frequency, and the value will then be displayed on the screen
#(in a new “measurement display slot”) and updated with each new acquired waveform.
#Also, it supports an autoscale command, which adjusts the settings based on the input signals to make the displayed waveforms as easy to see and interpret as possible.

#Any class variable set to None needs to be defined when subclassing with values specific to the model,
#unless otherwise specified. See simulated Agilent33210A specific device class for an example.
class SimulatedOscilloscopeInstrument(SimulatedGPIBInstrumentInterface):
    name=None
    version=None
    description=None
    id_string=None
    
    #greatest amount of time (in seconds) that a horizontal division can span (float)
    max_window_horizontal_scale=None
    
    #greatest number of volts that a vertical division can span for an input signal (float)
    max_vertical_channel_scale=None
    
    #number of vertical divisions on screen (const int)
    vertical_divisions=None
    
    #number of horizontal divisions on screen (const int)
    horizontal_divisions=None
    
    #see SimulatedInstrumentInterface
    channel_count=None
    
    #see SimulatedInstrumentInterface
    #We have to pass values into InputSignal upon initialization which we don't have to do with output signals, so this was a weird case...
    #here's trick I came up with to make channels list fill up with InputSignals that are properly initialized... TODO: make cleaner somehow?
    signal_type=(lambda self: SimulatedInputSignal(self.max_window_horizontal_scale*self.horizontal_divisions))
    
    #default horizonal scale for each horizontal division (float, in seconds)
    def_window_horizontal_scale=None
    
    #default vertical scale for each vertical division for each channel (float, in volts)
    def_channel_vertical_scale=None
    
    #There is a tradeoff between the sample rate and the horizontal scale due to the finite record length:
    #the greater the horizontal scale, the slower the sample rate has to be.
    record_length=None
    
    #see SimulatedInstrumentInterface.
    #channel_positions: nth element of list represents vertical offset we apply to input signal of nth channel
    #channel_scales: nth element of list represents scale of each vertical division for input signal of nth channel
    def set_default_settings(self):
        self.window_horizontal_scale=self.def_window_horizontal_scale
        self.channel_positions=[0.0]*self.channel_count
        self.channel_scales=[self.def_channel_vertical_scale]*self.channel_count
        
    #The handler for the set command for the window horizontal scale is a standard setter that takes one argument and
    #sets the device’s window_horizontal_scale to that value after checking the value is the right type and in the valid range,
    #and the handler for the window horizontal scale query is a typical getter, returning the device’s window_horizontal_scale value.
    def horizontal_scale(self,val=None):
        if val: #setter
            val=self.enforce_type_and_range(val,(float,(0,self.max_window_horizontal_scale)),"horizontal scale")
            self.window_horizontal_scale=val

        else: #query
            return str(self.window_horizontal_scale)
        
    #The channel vertical scale query/set command handlers are also typical getters and setters,
    #except they each also take in a channel value and check its type and range, and they get/set the value just
    #for the specified channel in the device’s channel_vertical_scales list
    def channel_scale(self,chan, val=None):
        chan=self.enforce_type_and_range(chan,(int,(1,4)),"channel")
        if val:
            val=self.enforce_type_and_range(val,(float,(0,self.max_vertical_channel_scale)),"channel scale")
            
            self.channel_scales[chan-1]=val

        else:
            return str(self.channel_scales[chan-1])
        
    #The channel vertical offset query/set command handlers are also typical getters and setters, except they each also take in a
    #channel value and check its type and range, and they get/set the value just for the specified channel in the device’s
    #channel_vertical_positions list. The range of the offset is simply between the bottom and top of the window; which is half the
    #total number of vertical divisions times the scale of each divisions
    def channel_offset(self,chan, val=None):
        chan=self.enforce_type_and_range(chan,(int,(1,4)),"channel")
        if val:
            val=self.enforce_type_and_range(val,(float,(-.5*self.vertical_divisions*self.channel_scales[chan-1],.5*self.vertical_divisions*self.channel_scales[chan-1])))
            self.channel_positions[chan-1]=-1*val
        else:
            return str(-1*self.channel_positions[chan-1])
    
    #The handler for the command to set a channel’s status checks the type and range of its two arguments, channel and status
    #(0 for off, 1 for on), and sets the is_on property of the desired channel accordingly. The corresponding query handler checks
    #its lone channel argument’s type and value and returns the value of is_on property of the desired channel.
    def toggle_channel(self,chan, val=None):
        chan=self.enforce_type_and_range(chan,(int,(1,4)),"channel")
        if val:
            val=self.enforce_type_and_range(val,(int,(0,1)),"channel display status")
            self.channels[chan-1].is_on=bool(val)
        else:
            return str(int(self.channels[chan-1].is_on))
    
    def display_measurement(display_section,channel,measurement):
        pass
        
    #The handlers for GPIB commands for making measurements on constructed waveforms each take in one argument,
    #the channel whose electrical input signal’s constructed waveform should have the measurement taken on it.
    # After checking the channel argument’s type and checking it’s in range, each handler turns on that channel
    #and generates a waveform from the channel’s received input signal by calling the InputSignal’s construct_waveform
    #method. For the waveform duration argument we provide the device’s current window_horizontal_scale multiplied by
    #the number of horizontal_divisions it has (as this will be the time duration the waveform needs to cover). Also, we
    #provide the device’s constant record_length, to determine how many sample points the constructed waveform needs to
    #consist of. For the channel offset argument we provide the channel’s position in the device’s vertical_channel_positions
    #list. Finally, we provide the voltage range in which to sample the electrical signal before clipping, by subtracting
    #(adding) the vertical scale for the channel (from vertical_channel_scales) multiplied by half the number of
    #vertical_divisions to get the range’s min (max).
    
    def measure_average(self,chan):
        chan=chan[-1]
        chan=self.enforce_type_and_range(chan,(int,(1,4)),"channel")
        self.channels[chan-1].is_on=True
        waveform=self.channels[chan-1].construct_waveform(self.window_horizontal_scale*self.horizontal_divisions,self.channel_positions[chan-1],-.5*self.vertical_divisions*self.channel_scales[chan-1],.5*self.vertical_divisions*self.channel_scales[chan-1],self.record_length)# see construct_waveform in InputSignal.
        #This construct_waveform call returns the acquired waveform as a numpy array of floats (voltages).
        #If construct_waveform returns None, this means no cable was connected to the channel.
        
        return str(self.calc_av_from_waveform(waveform))
        
    def calc_av_from_waveform(self,waveform):
        if not waveform:
            return 0.0
        else:
            return np.average(waveform)
            #For the handler for measuring average, we return 0 if the waveform was None.
            #Otherwise, we simply return the mean value of the numpy array.
        
    def measure_peak_to_peak(self,chan):
        chan=chan[-1]
        chan=self.enforce_type_and_range(chan,(int,(1,4)),"channel")
        self.channels[chan-1].is_on=True
        waveform=self.channels[chan-1].construct_waveform(self.window_horizontal_scale*self.horizontal_divisions,self.channel_positions[chan-1],-.5*self.vertical_divisions*self.channel_scales[chan-1],.5*self.vertical_divisions*self.channel_scales[chan-1],self.record_length)
        return str(self.calc_p2p_from_waveform(waveform))
        
    def calc_p2p_from_waveform(self,waveform):
        if not waveform:
            return 0.0
        else:
            max=np.amax(waveform)
            min=np.amin(waveform)
            return max-min
        #For the handler for measuring peak-to-peak voltage, we return 0 if the waveform was None.
        #Otherwise, we simply return the difference between the max and min values of the numpy array.
        
    def measure_frequency(self,chan):
        chan=chan[-1]
        chan=self.enforce_type_and_range(chan,(int,(1,4)),"channel")
        self.channels[chan-1].is_on=True
        waveform=self.channels[chan-1].construct_waveform(self.window_horizontal_scale*self.horizontal_divisions,self.channel_positions[chan-1],-.5*self.vertical_divisions*self.channel_scales[chan-1],.5*self.vertical_divisions*self.channel_scales[chan-1],self.record_length)
        return str(self.calc_freq_from_waveform(waveform))
        
    def calc_freq_from_waveform(self,waveform):
        if not waveform:
            return 1000000
        #For the handler for measuring frequency, if the waveform was None we return a very large number
        #(to mimic a real oscilloscope, which gets thrown off by noise into thinking there’s a very large frequency).
        else:
        
            #Otherwise, we determine at which time-values the voltage crosses the value halfway between its min and max,
            #going from below this halfway point to above.
            wavelength_starts=self.find_where_crossing(waveform)
            
            if len(wavelength_starts)<=1:
                return 100000 #If this never occurs or only occurs once, we return a very large number.
            
            #Otherwise, we calculate the time difference between the first time this occurs and the last time.
            #Then, we take the number of times this happens overall (not including the first time) and divide by that time difference,
            #to get the number of observed full wavelengths in the waveform over the total time these wavelengths collectively took.
            #Then we return this value as the frequency.
            first_cross=wavelength_starts[0]
            last_cross=wavelength_starts[-1]
            crosses=len(wavelength_starts)-1
            fraction_used=(last_cross-first_cross)/(len(waveform))
            window_horiz_time_length=self.window_horizontal_scale*self.horizontal_divisions
            return crosses/(window_horiz_time_length*fraction_used)
            

        
    def find_where_crossing(self,waveform):
        max=np.amax(waveform)
        min=np.amin(waveform)
        halfway=(max+min)/2.0
        signs=np.sign(waveform-halfway) #array of length of waveform. each value mapped to -1 if value lower than average, 0 if average, 1 if above average
        where_pos=(np.clip(signs,0,1)) #change -1s to 0s, so each value is now 0 if original value lower than average or average, 1 if above average
        pos_changes=np.nonzero(np.diff(where_pos)==1)
        return pos_changes[0]  #marks where where_pos went from 0 to 1 (so where voltage rose from below to above average)
    
    
        
        

    #Finally, we have the autoscale command handler.
    #For each channel, it turns on the channel and constructs a waveform from its input signal using the maximum vertical range (using the maximum allowed vertical channel scale),
    #and using a relatively small duration that is model-specific. It then gathers the peak-to-peak voltage, the halfway point between the min and max voltages,
    #and the frequency of this waveform for the channel. If the frequency or peak-to-peak voltage is too low, we turn off the channel.
    # Otherwise, we use the “halfway” voltage to reposition the channel (by changing the value for the channel’s vertical position in channel_vertical_positions)
    #so it is vertically centered in the "display", and then use the peak-to-peak reading to change the vertical scale for the channel
    #in channel_vertical_scales to to attempt to make it fit vertically. Based on the lowest frequency we
    #measured out of the four channels (that wasn’t so low that we turned off the channel) we change the window_horizontal_scale
    #to attempt to include three wavelengths of the lowest-frequency input signal across the screen (across all the horizontal divisions).
    def autoscale(self):
        low_elig_freq=None
        for chan in range(len(self.channels)):
            self.channels[chan-1].is_on=True
            waveform=self.channels[chan-1].construct_waveform(self.max_window_horizontal_scale*self.horizontal_divisions,self.channel_positions[chan-1],-.5*self.vertical_divisions*self.max_vertical_channel_scale,.5*self.vertical_divisions*self.max_vertical_channel_scale,self.record_length)
            freq=self.calc_freq_from_waveform(waveform)
            avg=self.calc_av_from_waveform(waveform)
            p2p=self.calc_p2p_from_waveform(waveform)
            
            if ((freq<.5) or (p2p<.01)):
                self.channels[chan-1].is_on=False
            else:
                if (not low_elig_freq) or freq<low_elig_freq:
                    low_elig_freq=freq
                self.channel_positions[chan-1]=self.channel_positions[chan-1]-avg
                self.channel_scales[chan-1]=min(p2p/self.vertical_divisions,self.max_vertical_channel_scale) #will be centered. try to make it take up all divisions
        if low_elig_freq:
            self.window_horizontal_scale=min((1/self.horizontal_divisions)*3.0*(1/low_elig_freq),self.max_window_horizontal_scale) #try to show 3 wavelengths over the duration
        else:
            self.window_horizontal_scale=self.def_window_horizontal_scale

    
