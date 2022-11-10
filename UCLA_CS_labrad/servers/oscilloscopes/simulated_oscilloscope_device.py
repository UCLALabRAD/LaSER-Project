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
    max_channel_scale=None
    points_in_record_count=None
    
    
    def __init__(self):
        super().__init__()
        self.channels=[]
        for i in range(4):
            self.channels.append(SimulatedInSignal(self.max_window_horizontal_scale*10,self.points_in_record_count))
        self.set_default_settings()
            
    def set_default_settings(self):
        self.window_horizontal_scale=1.0
        self.window_horizontal_position=0.0
        self.channel_positions=[0.0]*4
        self.channel_scales=[1.0]*4
        
    def horizontal_scale(self,val=None):
        if val:
            self.window_horizontal_scale=float(val.decode())
        else:
            return str(self.window_horizontal_scale)
        

    def horizontal_position(self,val=None):
        if val:
            self.window_horizontal_position=float(val.decode())
        else:
            return str(self.window_horizontal_position)
        
    def channel_scale(self,chan, val=None):
        chan=int(chan.decode())
        if val:
            self.channel_scales[chan-1]=float(val.decode())
        else:
            return str(self.channel_scales[chan-1])
        
    def channel_offset(self,chan, val=None):
        chan=int(chan.decode())
        if val:
            self.channel_positions[chan-1]=-1*float(val.decode())
        else:
            return str(-1*self.channel_positions[chan-1])
    
    def toggle_channel(self,chan, val=None):
        chan=int(chan.decode())
        if val:
            self.channels[chan-1].is_on=int(val.decode())
        else:
            return str(int(self.channels[chan-1].is_on))
        
    def display_measurement(display_section,channel,measurement):
        pass
        
    def measure_average(self,chan):
        chan=int(chan[-1:])
        self.channels[chan-1].is_on=True
        waveform=self.channels[chan-1].generate_waveform(self.window_horizontal_scale,self.window_horizontal_position,self.channel_scales[chan-1],self.channel_positions[chan-1])
        return str(self.calc_av_from_waveform(waveform))
        
    def calc_av_from_waveform(self,waveform):
        if not waveform:
            return 0.0
        else:
            return np.average(waveform)
        
    def measure_peak_to_peak(self,chan):
        chan=int(chan[-1:])
        self.channels[chan-1].is_on=True
        waveform=self.channels[chan-1].generate_waveform(self.window_horizontal_scale,self.window_horizontal_position,self.channel_scales[chan-1],self.channel_positions[chan-1])
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
        waveform=self.channels[chan-1].generate_waveform(self.window_horizontal_scale,self.window_horizontal_position,self.channel_scales[chan-1],self.channel_positions[chan-1])
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
    
    
        
        

    
    def autoscale(self):
        low_elig_freq=None
        for chan in range(len(self.channels)):
            self.channels[chan-1].is_on=True
            waveform=self.channels[chan-1].generate_waveform(1.0,0.0,self.max_channel_scale,0.0)
            freq=self.calc_freq_from_waveform(waveform)
            avg=self.calc_av_from_waveform(waveform)
            p2p=self.calc_p2p_from_waveform(waveform)
            
            if ((freq<.5) or (p2p<.01)):
                self.channels[chan-1].is_on=False
            else:
                if (not low_elig_freq) or freq<low_elig_freq:
                    low_elig_freq=freq
                self.channel_positions[chan-1]=self.channel_positions[chan-1]-avg
                self.channel_scales[chan-1]=p2p/4.0 #will be centered and take up 4 divisions / 8 vertical divisions
        if low_elig_freq:
            self.window_horizontal_scale=.1*2.0*(1/low_elig_freq) #try to show 2 wavelengths over 10 horizontal divisions
        else:
            self.window_horizontal_scale=1.0



class SimulatedKeysightDSOX2024A(SimulatedOscilloscope):
    name= 'KeysightDSOX2024A'
    version = '1.0'
    description='Oscilloscope'
    id_string='AGILENT TECHNOLOGIES,DSO-X 2024A,MY58104761,02.43.2018020635'
    max_window_horizontal_scale=2.5
    max_channel_scale=5
    points_in_record_count=100000
    command_dict={
        (b':MEASure:VAV?',1) : SimulatedOscilloscope.measure_average,
        (b':MEASure:FREQ?',1) : SimulatedOscilloscope.measure_frequency,
        (b':AUT',0) : SimulatedOscilloscope.autoscale,
        (b':CHANnel1:DISPlay',1): (lambda self, val: SimulatedOscilloscope.toggle_channel(self,b'1',val)),
        (b':CHANnel2:DISPlay',1): (lambda self, val: SimulatedOscilloscope.toggle_channel(self,b'2',val)),
        (b':CHANnel3:DISPlay',1): (lambda self, val: SimulatedOscilloscope.toggle_channel(self,b'3',val)),
        (b':CHANnel4:DISPlay',1): (lambda self, val: SimulatedOscilloscope.toggle_channel(self,b'4',val)),
        (b':CHANnel1:DISPlay?',0): (lambda self : SimulatedOscilloscope.toggle_channel(self,b'1')),
        (b':CHANnel2:DISPlay?',0): (lambda self : SimulatedOscilloscope.toggle_channel(self,b'2')),
        (b':CHANnel3:DISPlay?',0): (lambda self : SimulatedOscilloscope.toggle_channel(self,b'3')),
        (b':CHANnel4:DISPlay?',0): (lambda self : SimulatedOscilloscope.toggle_channel(self,b'4')),
		(b':MEASure:CLEar',0): None,
        
        (b':CHANnel1:OFFSet',1): (lambda self,val : SimulatedOscilloscope.channel_offset(self,b'1',val)),
        (b':CHANnel2:OFFSet',1): (lambda self,val : SimulatedOscilloscope.channel_offset(self,b'2',val)),
        (b':CHANnel3:OFFSet',1): (lambda self,val : SimulatedOscilloscope.channel_offset(self,b'3',val)),
        (b':CHANnel4:OFFSet',1): (lambda self,val : SimulatedOscilloscope.channel_offset(self,b'4',val)),
        (b':CHANnel1:OFFSet?',0): (lambda self : SimulatedOscilloscope.channel_offset(self,b'1')),
        (b':CHANnel2:OFFSet?',0): (lambda self : SimulatedOscilloscope.channel_offset(self,b'2')),
        (b':CHANnel3:OFFSet?',0): (lambda self : SimulatedOscilloscope.channel_offset(self,b'3')),
        (b':CHANnel4:OFFSet?',0): (lambda self : SimulatedOscilloscope.channel_offset(self,b'4')),
        
        (b':CHANnel1:SCALe',1): (lambda self,val : SimulatedOscilloscope.channel_scale(self,b'1',val)),
        (b':CHANnel2:SCALe',1): (lambda self,val : SimulatedOscilloscope.channel_scale(self,b'2',val)),
        (b':CHANnel3:SCALe',1): (lambda self,val : SimulatedOscilloscope.channel_scale(self,b'3',val)),
        (b':CHANnel4:SCALe',1): (lambda self,val : SimulatedOscilloscope.channel_scale(self,b'4',val)),
        (b':CHANnel1:SCALe?',0): (lambda self : SimulatedOscilloscope.channel_scale(self,b'1')),
        (b':CHANnel2:SCALe?',0): (lambda self : SimulatedOscilloscope.channel_scale(self,b'2')),
        (b':CHANnel3:SCALe?',0): (lambda self : SimulatedOscilloscope.channel_scale(self,b'3')),
        (b':CHANnel4:SCALe?',0): (lambda self : SimulatedOscilloscope.channel_scale(self,b'4')),
        (b':TIMe:SCALe',1): SimulatedOscilloscope.horizontal_scale,
        (b':TIMe:SCALe?',0): SimulatedOscilloscope.horizontal_scale,
        (b':TIMe:POSition',1): SimulatedOscilloscope.horizontal_position,
        (b':TIMe:POSition?',0): SimulatedOscilloscope.horizontal_position

        
        }
        
 
        
        
    
    
