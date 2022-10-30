from UCLA_CS_labrad.servers.hardwaresimulation.sim_instr_models import GPIBDeviceModel

from UCLA_CS_labrad.servers.hardwaresimulation.simulated_cables import SimulatedInSignal

from twisted.internet.threads import deferToThread
from twisted.internet.task import LoopingCall
from twisted.internet.defer import inlineCallbacks, returnValue
from labrad.errors import Error
import time
import numpy as np

#penny CS GPIB Bus - USB0::0x0957::0x1796::MY58104761::INSTR
class SimulatedOscilloscope(GPIBDeviceModel)
    name=None
    version=None
    description=None
    id_string=None
    max_window_horizontal_scale=None
    max_window_vertical_scale=None
    
    def __init__(self):
        super().__init__()
        self.channels=[]
        for i in range(4):
            self.channels.append(SimulatedInSignal(self.max_window_horizontal_scale*10))
        self.set_default_settings()
            
    def set_default_settings(self):
        self.window_horizontal_scale=1
        self.window_vertical_scale=1
        self.window_horizontal_position=1
        #self.window_vertical_position=1
        
    def toggle_channel(self,channel,val=None):
        if val:
            self.channels[int(channel)-1].is_on=bool(int(val))
        return str(int(self.channels[int(channel)-1].is_on))
        
    def display_measurement(display_section,channel,measurement):
        pass
        
    def measure_average(self,chan):
        chan=int(chan[-1])
        waveform=self.channels[chan-1].generate_waveform(self.window_horizontal_scale,self.window_horizontal_position)
        return bytes(np.average(waveform)))
        
    def measure_peak_to_peak(self,chan):
        chan=int(chan[-1])
        waveform=self.channels[chan-1].generate_waveform()
        max=np.amax(waveform)
        min=np.amin(waveform)
        return max-min
        
        
    def measure_frequency(self,chan):
        chan=int(chan[-1])
        waveform=self.channels[chan-1].generate_waveform()
        wavelength_starts=self.find_where_crossing(waveform)
        first_cross=wavelength_starts[0]
        last_cross=wavelength_starts[-1]
        crosses=len(wavelength_starts)-1
        
        return bytes(crosses/((last_cross-first_cross)/(len(waveform))*self.window_horizontal_scale*10))
        #total_time*(last_cross-first_cross)/1000.0)))
        
    def find_where_crossing(self,waveform):
        
        max=np.amax(waveform)
        min=np.amin(waveform)
        halfway=(max+min)/2.0
        
        cross_array=np.diff(np.sign(waveform-halfway)==1)
        nonzero=np.nonzero(cross_array)
        return nonzero
    
        
        
    def measure_peak_to_peak(self,chan):
        chan=int(chan[-1])
        waveform=self.channels[chan-1].generate_waveform(self.window)
        max=np.amax(waveform)
        min=np.amin(waveform)
        return (max-min)
        
        
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
    max_window_horizontal_scale=5
    max_window_vertical_scale=5
    points_in_record_count=1000
    self.command_dict={
        (b':MEAS:VAV?',1) : self.measure_average,
        (b':MEAS:FREQ?',1) : self.measure_frequency,
        (b':MEAS:VAV',1) : self.measure_average,
        (b':MEAS:FREQ',1) : None,
        (b':MEAS:VAV',1) : None,
        (b':AUT',0) : self.autoscale,
        (b':CHAN1:DISP',1): (lambda val: self.toggle_channel('1',val))
        (b':CHAN2:DISP',1): (lambda val: self.toggle_channel('2',val))
        (b':CHAN3:DISP',1): (lambda val: self.toggle_channel('3',val))
        (b':CHAN4:DISP',1): (lambda val: self.toggle_channel('4',val))
        (b':CHAN1:DISP?',0): (lambda val: self.toggle_channel('1'))
        (b':CHAN2:DISP?',0): (lambda val: self.toggle_channel('2'))
        (b':CHAN3:DISP?',0): (lambda val: self.toggle_channel('3'))
        (b':CHAN4:DISP?',0): (lambda val: self.toggle_channel('4'))
        }
        
 
        
        
    
    
