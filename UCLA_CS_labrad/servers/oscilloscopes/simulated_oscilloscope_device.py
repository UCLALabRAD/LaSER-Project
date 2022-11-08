from UCLA_CS_labrad.servers.hardwaresimulation.sim_instr_models import GPIBDeviceModel

from UCLA_CS_labrad.servers.hardwaresimulation.simulated_cables import SimulatedInSignal

from twisted.internet.threads import deferToThread
from twisted.internet.task import LoopingCall
from twisted.internet.defer import inlineCallbacks, returnValue
from labrad.errors import Error
import time
import numpy as np

#penny CS GPIB Bus - USB0::0x0957::0x1796::MY58104761::INSTR
class SimulatedOscilloscope(GPIBDeviceModel):
    name=None
    version=None
    description=None
    id_string=None
    max_window_horizontal_scale=None
    max_window_vertical_scale=None
    points_in_record_count=None
    
    
    def __init__(self):
        super().__init__()
        self.channels=[]
        for i in range(4):
            self.channels.append(SimulatedInSignal(self.max_window_horizontal_scale*10,self.points_in_record_count))
        self.set_default_settings()
            
    def set_default_settings(self):
        self.window_horizontal_scale=1.0
        self.window_vertical_scale=1.0
        self.window_horizontal_position=0.0
        self.channel_positions=[0.0]*4
        
    def toggle_channel(self,channel,val=None):
        if val:
            self.channels[int(channel)-1].is_on=bool(int(val))
        else:
            return str(int(self.channels[int(channel)-1].is_on))
        
    def display_measurement(display_section,channel,measurement):
        pass
        
    def measure_average(self,chan):
        chan=int(chan[-1:])
        self.channels[chan-1].is_on=True
        waveform=self.channels[chan-1].generate_waveform(self.window_horizontal_scale,self.window_vertical_scale,self.window_horizontal_position,self.channel_positions[chan-1])
        return str(self.calc_av_from_waveform(waveform))
        
    def calc_av_from_waveform(self,waveform):
        if not waveform:
            return 0.0
        else:
            return np.average(waveform)
        
    def measure_peak_to_peak(self,chan):
        chan=int(chan[-1:])
        self.channels[chan-1].is_on=True
        waveform=self.channels[chan-1].generate_waveform(self.window_horizontal_scale,self.window_vertical_scale,self.window_horizontal_position,self.channel_positions[chan-1])
        return str(self.calc_p2p_from_waveform(waveform))
        
    def calc_p2p_from_waveform(self,waveform):
        if not waveform:
            return 0.0
        else:
            max=np.amax(waveform)
            min=np.amin(waveform)
            return max-min
        
    def measure_frequency(self,chan):
        chan=int(chan[-1:])
        self.channels[chan-1].is_on=True
        waveform=self.channels[chan-1].generate_waveform(self.window_horizontal_scale,self.window_vertical_scale,self.window_horizontal_position,self.channel_positions[chan-1])
        return str(self.calc_freq_from_waveform(waveform))
        
    def calc_freq_from_waveform(self,waveform):
        if not waveform:
            return 1000000
        else:
            wavelength_starts=self.find_where_crossing(waveform)
            if len(wavelength_starts)==0:
                return 1000000
            elif len(wavelength_starts)==1:
                return 0
            first_cross=wavelength_starts[0]
            last_cross=wavelength_starts[-1]
            crosses=len(wavelength_starts)-1
            fraction_used=(last_cross-first_cross)/(len(waveform))
            window_horiz_time_length=self.window_horizontal_scale*10
            return crosses/(window_horiz_time_length*fraction_used)
        
    def find_where_crossing(self,waveform):
        max=np.amax(waveform)
        min=np.amin(waveform)
        halfway=(max+min)/2.0
        signs=np.sign(waveform-halfway)
        where_pos=(np.clip(signs,0,1))
        pos_changes=np.nonzero(np.diff(where_pos)==1)
        return pos_changes[0]
    
    
        
        

    
    def autoscale(self): #TODO: put all active channels in window utilizing ver_positions. Currently will turn on/off each channel based on eligibility, but scales to first eligible channel, disregarding others.
        self.window_horizontal_position=self.max_window_horizontal_scale*5
        self.window_horizontal_scale=.5
        self.window_vertical_scale=self.max_window_vertical_scale
        new_window_horizontal_scale=None
        new_window_vertical_scale=None
        new_channel_vertical_position=None
        scaled=False
        for chan in range(len(self.channels)):
            if not scaled:
                self.channel_positions[chan-1]=0.0
            self.channels[chan-1].is_on=True
            waveform=self.channels[chan-1].generate_waveform(self.window_horizontal_scale,self.window_vertical_scale,self.window_horizontal_position,self.channel_positions[chan-1])
            freq=self.calc_freq_from_waveform(waveform)
            if not scaled:
                avg=self.calc_av_from_waveform(waveform)
            p2p=self.calc_p2p_from_waveform(waveform)
            
            if ((freq<.5) or (p2p<.01)):
                self.channels[chan-1].is_on=False
            else:
               if not scaled:
                   scaled=True
                   self.channel_positions[chan-1]=self.channel_positions[chan-1]-avg
                   self.window_vertical_scale=p2p/4.0 #will be centered and take up 4 divisions / 8 vertical divisions
                   self.window_horizontal_scale=.1*2.0*(1/freq) #try to show 2 wavelengths over 10 horizontal divisions


class SimulatedKeysightDSOX2024A(SimulatedOscilloscope):
    name= 'KeysightDSOX2024A'
    version = '1.0'
    description='Oscilloscope'
    id_string='AGILENT TECHNOLOGIES,DSO-X 2024A,MY58104761,02.43.2018020635'
    max_window_horizontal_scale=2.5
    max_window_vertical_scale=5
    points_in_record_count=100000
    command_dict={
        (b':MEASure:VAV?',1) : SimulatedOscilloscope.measure_average,
        (b':MEASure:FREQ?',1) : SimulatedOscilloscope.measure_frequency,
        (b':AUT',0) : SimulatedOscilloscope.autoscale,
        (b':CHANnel1:DISPlay',1): (lambda self, val: SimulatedOscilloscope.toggle_channel(self,'1',val)),
        (b':CHANnel2:DISPlay',1): (lambda self, val: SimulatedOscilloscope.toggle_channel(self,'2',val)),
        (b':CHANnel3:DISPlay',1): (lambda self, val: SimulatedOscilloscope.toggle_channel(self,'3',val)),
        (b':CHANnel4:DISPlay',1): (lambda self, val: SimulatedOscilloscope.toggle_channel(self,'4',val)),
        (b':CHANnel1:DISPlay?',0): (lambda self : SimulatedOscilloscope.toggle_channel(self,'1')),
        (b':CHANnel2:DISPlay?',0): (lambda self : SimulatedOscilloscope.toggle_channel(self,'2')),
        (b':CHANnel3:DISPlay?',0): (lambda self : SimulatedOscilloscope.toggle_channel(self,'3')),
        (b':CHANnel4:DISPlay?',0): (lambda self : SimulatedOscilloscope.toggle_channel(self,'4')),
        (b':TEST:HI:THERE'):None,
        (b':TEST:HI:HERE'):None,
        (b':TEST:HEY:THERE'):None,
        (b':TEST:HEY:HERE'):None
        
        }
        
 
        
        
    
    
