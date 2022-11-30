from ..simulated_instruments import SimulatedGPIBInstrumentInterface, SimulatedInstrumentError
from UCLA_CS_labrad.servers.hardwaresimulation.cablesimulation.simulated_signals import SimulatedInputSignal


from twisted.internet.threads import deferToThread
from twisted.internet.task import LoopingCall
from twisted.internet.defer import inlineCallbacks, returnValue
from labrad.errors import Error
import time
import numpy as np

__all__=["SimulatedOscilloscopeInstrument","SimulatedOscilloscopeError"]

class SimulatedOscilloscopeError(SimulatedInstrumentError):
    user_defined_errors={}
#penny CS GPIB Bus - USB0::0x0957::0x1796::MY58104761::INSTR
class SimulatedOscilloscopeInstrument(SimulatedGPIBInstrumentInterface):
    name=None
    version=None
    description=None
    id_string=None
    max_window_horizontal_scale=None
    max_vertical_channel_scale=None
    vertical_divisions=None
    horizontal_divisions=None
    channel_count=None
    signal_type=(lambda self: SimulatedInputSignal(self.max_window_horizontal_scale*self.horizontal_divisions))
    def_window_horizontal_scale=None
    def_channel_vertical_scale=None
    record_length=None
    
    def set_default_settings(self):
        self.window_horizontal_scale=self.def_window_horizontal_scale
        self.channel_positions=[0.0]*self.channel_count
        self.channel_scales=[self.def_channel_vertical_scale]*self.channel_count
        
    def horizontal_scale(self,val=None):
        if val:
            val=self.enforce_type_and_range(val,(float,(0,self.max_window_horizontal_scale)),"horizontal scale")
            self.window_horizontal_scale=val

        else:
            return str(self.window_horizontal_scale)
        

    def channel_scale(self,chan, val=None):
        chan=self.enforce_type_and_range(chan,(int,(1,4)),"channel")
        if val:
            val=self.enforce_type_and_range(val,(float,(0,self.max_vertical_channel_scale)),"channel scale")
            
            self.channel_scales[chan-1]=val

        else:
            return str(self.channel_scales[chan-1])
        
        
    def channel_offset(self,chan, val=None):
        chan=self.enforce_type_and_range(chan,(int,(1,4)),"channel")
        if val:
            val=self.enforce_type_and_range(val,(float,(-.5*self.vertical_divisions*self.channel_scales[chan-1],.5*self.vertical_divisions*self.channel_scales[chan-1])))
            self.channel_positions[chan-1]=-1*val
        else:
            return str(-1*self.channel_positions[chan-1])
    
    def toggle_channel(self,chan, val=None):
        chan=self.enforce_type_and_range(chan,(int,(1,4)),"channel")
        if val:
            val=self.enforce_type_and_range(val,(int,(0,1)),"channel display status")
            self.channels[chan-1].is_on=bool(val)
        else:
            return str(int(self.channels[chan-1].is_on))
        
    def display_measurement(display_section,channel,measurement):
        pass
        
    def measure_average(self,chan):
        chan=chan[-1]
        chan=self.enforce_type_and_range(chan,(int,(1,4)),"channel")
        self.channels[chan-1].is_on=True
        waveform=self.channels[chan-1].construct_waveform(self.window_horizontal_scale*self.horizontal_divisions,self.channel_positions[chan-1],-.5*self.vertical_divisions*self.channel_scales[chan-1],.5*self.vertical_divisions*self.channel_scales[chan-1],self.record_length)
        return str(self.calc_av_from_waveform(waveform))
        
    def calc_av_from_waveform(self,waveform):
        if not waveform:
            return 0.0
        else:
            return np.average(waveform)
        
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
        
    def measure_frequency(self,chan):
        chan=chan[-1]
        chan=self.enforce_type_and_range(chan,(int,(1,4)),"channel")
        self.channels[chan-1].is_on=True
        waveform=self.channels[chan-1].construct_waveform(self.window_horizontal_scale*self.horizontal_divisions,self.channel_positions[chan-1],-.5*self.vertical_divisions*self.channel_scales[chan-1],.5*self.vertical_divisions*self.channel_scales[chan-1],self.record_length)
        return str(self.calc_freq_from_waveform(waveform))
        
    def calc_freq_from_waveform(self,waveform):
        if not waveform:
            return 0
        else:
            wavelength_starts=self.find_where_crossing(waveform)
            if len(wavelength_starts)<=1:
                return 0
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
        signs=np.sign(waveform-halfway)
        where_pos=(np.clip(signs,0,1))
        pos_changes=np.nonzero(np.diff(where_pos)==1)
        return pos_changes[0]
    
    
        
        

    
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
                self.channel_scales[chan-1]=min(p2p/self.vertical_divisions,self.max_vertical_channel_scale) #will be centered and take up 4 divisions / 8 vertical divisions
        if low_elig_freq:
            self.window_horizontal_scale=min((1/self.horizontal_divisions)*3.0*(1/low_elig_freq),self.max_window_horizontal_scale) #try to show 3 wavelengths over 10 horizontal divisions
        else:
            self.window_horizontal_scale=self.def_window_horizontal_scale

    
