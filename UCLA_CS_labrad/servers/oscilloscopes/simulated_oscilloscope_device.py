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
        self.window_horizontal_scale=1
        self.window_vertical_scale=1
        self.window_horizontal_position=0
        #self.window_vertical_position=1
        
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
        waveform=self.channels[chan-1].generate_waveform(self.window_horizontal_scale,self.window_horizontal_position,1)
        if not waveform:
            return str(0.0)
        else:
            return str(np.average(waveform))
        
    def measure_peak_to_peak(self,chan):
        chan=int(chan[-1:])
        self.channels[chan-1].is_on=True
        waveform=self.channels[chan-1].generate_waveform()
        if not waveform:
            return str(0.0)
        else:
            max=np.amax(waveform)
            min=np.amin(waveform)
            return str(max-min)
        
        
    def measure_frequency(self,chan):
        chan=int(chan[-1:])
        self.channels[chan-1].is_on=True
        waveform=self.channels[chan-1].generate_waveform(self.window_horizontal_scale,self.window_horizontal_position,1)
        if not waveform:
            return str(1000000)
        else:
            wavelength_starts=self.find_where_crossing(waveform)
            if len(wavelength_starts)==0:
                return str(1000000)
            elif len(wavelength_starts)==1:
                return str(0)
            first_cross=wavelength_starts[0]
            last_cross=wavelength_starts[-1]
            crosses=len(wavelength_starts)-1
            fraction_used=(last_cross-first_cross)/(len(waveform))
            window_horiz_time_length=self.window_horizontal_scale*10
            return str(crosses/(window_horiz_time_length*fraction_used))
        
    def find_where_crossing(self,waveform):
        
        max=np.amax(waveform)
        min=np.amin(waveform)
        halfway=(max+min)/2.0
        signs=np.sign(waveform-halfway)
        where_pos=(np.clip(signs,0,1))
        pos_changes=np.nonzero(np.diff(where_pos)==1)
        return pos_changes[0]
    
        
        

    '''
    def autoscale(self):
        self.window_horizontal_position=self.max_window_horizontal_scale*5
        horiz_scale_new_window=0
        vert_position_new_window=0
        vert_scale_new_window=5
        
        for channel in self.channels:
            waveform=self.channels[chan-1].generate_waveform()
            
            max=np.amax(waveform)
            min=np.amin(waveform)
            halfway=(max+min)/2.0
            
            cross_array=np.diff(np.sign(waveform-halfway)==1)
            wavelength_starts=np.nonzero(cross_array)
            crosses=len(wavelength_starts)-1
            freq=crosses/((last_cross-first_cross)/(len(waveform))*self.window_horizontal_scale*10)
            if ((freq<1) or (max-min)<.2):
                channel.is_on=False
            else:
            if measure_frequency()<10 or measure)peak_to_peak
            if channel.input_signal_log:
            else:
                channel.is_on=False
        
        
        
            
        
        wavelength_starts=self.find_where_crossing(waveform)
        if len(wavelength_starts)>3:
            
        elif len(wavelength_starts<3:
        
        else:
         break
        
        
        #get waveforms for all channels, get max,min, where waves clipped if clipped, horizontally?
        return
        '''

class SimulatedKeysightDSOX2024A(SimulatedOscilloscope):
    name= 'KeysightDSOX2024A'
    version = '1.0'
    description='Oscilloscope'
    id_string='AGILENT TECHNOLOGIES,DSO-X 2024A,MY58104761,02.43.2018020635'
    max_window_horizontal_scale=2.5
    max_window_vertical_scale=5
    points_in_record_count=1000
    command_dict={
        (b':MEASure:VAV?',1) : SimulatedOscilloscope.measure_average,
        (b':MEASure:FREQ?',1) : SimulatedOscilloscope.measure_frequency,
        (b':MEASure:VAV',1) : SimulatedOscilloscope.measure_average,
        (b':MEASure:FREQ',1) : None,
        #(b':AUT',0) : SimulatedOscilloscope.autoscale,
        (b':CHANnel1:DISPlay',1): (lambda self, val: SimulatedOscilloscope.toggle_channel(self,'1',val)),
        (b':CHANnel2:DISPlay',1): (lambda self, val: SimulatedOscilloscope.toggle_channel(self,'2',val)),
        (b':CHANnel3:DISPlay',1): (lambda self, val: SimulatedOscilloscope.toggle_channel(self,'3',val)),
        (b':CHANnel4:DISPlay',1): (lambda self, val: SimulatedOscilloscope.toggle_channel(self,'4',val)),
        (b':CHANnel1:DISPlay?',0): (lambda self : SimulatedOscilloscope.toggle_channel(self,'1')),
        (b':CHANnel2:DISPlay?',0): (lambda self : SimulatedOscilloscope.toggle_channel(self,'2')),
        (b':CHANnel3:DISPlay?',0): (lambda self : SimulatedOscilloscope.toggle_channel(self,'3')),
        (b':CHANnel4:DISPlay?',0): (lambda self : SimulatedOscilloscope.toggle_channel(self,'4'))
        }
        
 
        
        
    
    
