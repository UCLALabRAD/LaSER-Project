import numpy as np
from twisted.internet.defer import inlineCallbacks, returnValue

from labrad.units import WithUnit
from labrad.types import Value
from labrad.gpib import GPIBDeviceWrapper

from UCLA_CS_labrad.servers.hardwaresimulation import SimulatedOscilloscopeInstrument

class KeysightDSOX2024AWrapper(GPIBDeviceWrapper):
    def __init__(self,guid,name):
        super().__init__(guid,name)
        self.measurement_slots=[None]*4

    # SYSTEM
    @inlineCallbacks
    def reset(self):
        yield self.write('*RST')

    @inlineCallbacks
    def clear_buffers(self):
        yield self.write('*CLS')

    @inlineCallbacks
    def autoscale(self):
        yield self.write(':AUT')


    # CHANNEL
    @inlineCallbacks
    def channel_info(self, channel):
        onoff = yield self.channel_toggle(channel)
        probeAtten = yield self.channel_probe(channel)
        scale = yield self.channel_scale(channel)
        offset = yield self.channel_offset(channel)
        coupling = yield self.channel_coupling(channel)
        invert = yield self.channel_invert(channel)
        returnValue((onoff, probeAtten, scale, offset, coupling, invert))

    @inlineCallbacks
    def channel_coupling(self, channel, coupling=None):
        chString = ':CHAN{:d}:COUP'.format(channel)
        if coupling is not None:
            coupling = coupling.upper()
            if coupling in ('AC', 'DC'):
                yield self.write(chString + ' ' + coupling)
            else:
                raise Exception('Coupling must be one of: ' + str(('AC', 'DC')))
        resp = yield self.query(chString + '?')
        returnValue(resp.strip())

    @inlineCallbacks
    def channel_scale(self, channel, scale=None):
        chString = ':CHAN{:d}:SCAL'.format(channel)
        if scale is not None:
            if (scale > 1e-3) and (scale < 1e1):
                yield self.write(chString + ' ' + str(scale))
            else:
                raise Exception('Scale must be in range: [1e-4, 1e1]')
        resp = yield self.query(chString + '?')
        returnValue(float(resp))

    @inlineCallbacks
    def channel_probe(self, channel, atten=None):
        chString = ':CHAN{:d}:PROB'.format(channel)
        if atten is not None:
            if (atten > 1e-3) and (atten < 1e3):
                yield self.write(chString + ' ' + str(atten))
            else:
                raise Exception('Probe attenuation must be between .001 and 1000')
        resp = yield self.query(chString + '?')
        returnValue(float(resp))

    @inlineCallbacks
    def channel_toggle(self, channel, state=None):
        chString = ':CHAN{:d}:DISP'.format(channel)
        if state is not None:
            yield self.write(chString + ' ' + str(int(state)))
        resp = yield self.query(chString + '? ')
        returnValue(bool(int(resp)))

    @inlineCallbacks
    def channel_invert(self, channel, invert=None):
        chString = ':CHAN{:d}:INV'.format(channel)
        if invert is not None:
            yield self.write(chString + ' ' + str(int(invert)))
        resp = yield self.query(chString + '?')
        returnValue(bool(int(resp)))


    @inlineCallbacks
    def channel_position(self, channel, position=None):
        # value is in divisions
        chString = ':CHAN{:d}:OFFS'.format(channel)
        if position is not None:
            if (position > 1e-4) and (position < 1e1):
                position=position*-1
                yield self.write(chString + ' ' + str(position))
            else:
                raise Exception('Vertical position must be less than 4 divisions.')
        resp = yield self.query(chString + '?')
        returnValue(float(resp)*-1)


    # TRIGGER
    @inlineCallbacks
    def trigger_channel(self, channel=None):
        # note: target channel must be on
        chString = ':TRIG:EDGE:SOUR'
        if channel is not None:
            if channel in (1, 2, 3, 4):
                yield self.write(chString + ' CHAN' + str(channel))
            else:
                raise Exception('Trigger channel must be one of: ' + str((1, 2, 3, 4)))
        resp = yield self.query(chString + '?')
        resp = resp.strip()[4:]
        returnValue(int(resp))

    @inlineCallbacks
    def trigger_slope(self, slope=None):
        chString = 'TRIG:EDGE:SLOP'
        if slope is not None:
            slope = slope.upper()
            if slope in ('POS', 'NEG', 'EITH', 'ALT'):
                yield self.write(chString + ' ' + slope)
            else:
                raise Exception('Slope must be one of: ' + str(('POS', 'NEG', 'EITH', 'ALT')))
        resp = yield self.query(chString + '?')
        returnValue(resp.strip())

    @inlineCallbacks
    def trigger_level(self, channel, level=None):
        chString = ':TRIG:EDGE:LEV'
        if level is not None:
            chan_tmp = yield self.trigger_channel()
            vscale_tmp = yield self.channel_scale(chan_tmp)
            level_max = 5 * vscale_tmp
            if (level == 0) or (abs(level) <= level_max):
                yield self.write(chString + ' ' + str(level))
            else:
                raise Exception('Error: Trigger level must be in range: ' + str((-level_max, level_max)))
        resp = yield self.query(chString + '?')
        returnValue(float(resp))

    @inlineCallbacks
    def trigger_mode(self, mode=None):
        chString = ':TRIG:SWE'
        if mode is not None:
            if mode in ('AUTO', 'NORM'):
                yield self.write(chString + ' ' + mode)
            else:
                raise Exception('Error: Trigger mode must be one of: ' + str(('AUTO', 'NORM')))
        resp = yield self.query(chString + '?')
        returnValue(resp.strip())

    # HORIZONTAL
    @inlineCallbacks
    def horizontal_offset(self, offset=None):
        chString = 'TIM:POS'
        if offset is not None:
            if (offset == 0) or ((abs(offset) > 1e-6) and (abs(offset) < 1e0)):
                yield self.write(chString + ' ' + str(offset))
            else:
                raise Exception('Horizontal offset must be in range: ' + str('(1e-6, 1e0)'))
        resp = yield self.query(chString + '?')
        returnValue(float(resp))

    @inlineCallbacks
    def horizontal_scale(self, scale=None):
        chString = ':TIM:SCAL'
        if scale is not None:
            if (scale > 2e-9) and (scale < 5e1):
                yield self.write(chString + ' ' + str(scale))
            else:
                raise Exception('Horizontal scale must be in range: (2e-9, 100).')
        resp = yield self.query(chString + '?')
        returnValue(float(resp))


    # ACQUISITION
    @inlineCallbacks
    def trace(self, channel, points=1250000):
        """
        Get a trace for a single channel.
        Arguments:
            channel: The channel for which we want to get the trace.
        Returns:
            Tuple of ((ValueArray[s]) Time axis, (ValueArray[V]) Voltages).
        """
        # first need to stop oscilloscope to record
        yield self.write(':STOP')

        # set channel to take trace on
        yield self.write(':WAV:SOUR CHAN{:d}'.format(channel))
        # use raw mode which gives us the entire on-screen waveform with full horizontal resolution
        yield self.write(':WAV:POIN:MODE RAW')
        # return format (default byte), use ASC or WORD for better vertical resolution
        yield self.write(':WAV:FORM BYTE')

        # transfer waveform preamble
        preamble = yield self.query(':WAV:PRE?')
        # get waveform data
        data = yield self.query(':WAV:DATA?')

        # start oscope back up
        yield self.write(':RUN')

        # parse waveform preamble
        points, xincrement, xorigin, xreference, yincrement, yorigin, yreference = yield self._parsePreamble(preamble)
        # parse data
        trace = yield self._parseByteData(data)

        # convert data to volts
        xAxis = (np.arange(points) * xincrement + xorigin)
        yAxis = (trace - yorigin - yreference) * yincrement
        returnValue((xAxis, yAxis))


    # MEASURE
    @inlineCallbacks
    def measure_setup(self, slot, channel, param):
        # convert generalized parameters to device specific parameters
        valid_measurement_parameters = {
            "FREQ":"FREQ", "AMP":"VAMP", "MEAN":"VAV", "MAX":"VMAX", "MIN":"VMIN", "P2P":"VPP"
        }
        if slot not in (1, 2, 3, 4):
            raise Exception("Invalid measurement slot. Must be in [1, 4].")
        if (channel is not None) and (param is not None):
            if param not in valid_measurement_parameters:
                raise Exception("Invalid measurement type. Must be one of {}.".format(valid_measurement_parameters.keys()))
            self.measurement_slots[slot-1]=(channel, valid_measurement_parameters[param])
            yield self.write(':MEAS:CLE')
            for i in range(4):
                if self.measurement_slots[i]:
                    yield self.write(':MEAS:{:s} CHAN{:d}'.format(self.measurement_slots[i][1],self.measurement_slots[i][0]))
        if not (self.measurement_slots[slot-1]):
            raise Exception("")
        measurement_source, measurement_type=self.measurement_slots[slot-1]
        returnValue((slot,measurement_source, measurement_type))

    @inlineCallbacks
    def measure(self, slot):
        valid_measurement_parameters = {
            "FREQ":"FREQ", "AMP":"VAMP", "MEAN":"VAV", "MAX":"VMAX", "MIN":"VMIN", "P2P":"VPP"
        }
        if slot not in (1, 2, 3, 4) or (not self.measurement_slots[slot-1]):
            raise Exception("Invalid measurement slot. Must be in [1, 4].")
        measurement_source, measurement_type=self.measurement_slots[slot-1]
        print(measurement_source)
        print(measurement_type)
        measure_val = yield self.query('MEAS:{:s}? CHAN{:d}'.format(measurement_type,measurement_source))
        returnValue(float(measure_val))


     # HELPER
    def _parsePreamble(preamble):
        """
        <preamble_block> = <format 16-bit NR1>,
                         <type 16-bit NR1>,
                         <points 32-bit NR1>,
                         <count 32-bit NR1>,
                         <xincrement 64-bit floating point NR3>,
                         <xorigin 64-bit floating point NR3>,
                         <xreference 32-bit NR1>,
                         <yincrement 32-bit floating point NR3>,
                         <yorigin 32-bit floating point NR3>,
                         <yreference 32-bit NR1>
        """
        fields = preamble.split(',')
        points = int(fields[2])
        xincrement, xorigin, xreference = float(fields[4: 7])
        yincrement, yorigin, yreference = float(fields[7: 10])
        # print(str((points, xincrement, xorigin, xreference, yincrement, yorigin, yreference)))
        return (points, xincrement, xorigin, xreference, yincrement, yorigin, yreference)

    def _parseByteData(data):
        """
        Parse byte data.
        """
        # get tmc header in #NXXXXXXXXX format
        tmc_N = int(data[1])
        tmc_length = int(data[2: 2 + tmc_N])
        #print("tmc_N: " + str(tmc_N))
        #print("tmc_length: " + str(tmc_length))
        # use this return if return format is in bytes, otherwise need to adjust
        return np.frombuffer(data[2 + tmc_N:], dtype=np.uint8)
        
        
class SimulatedKeysightDSOX2024A(SimulatedOscilloscopeInstrument):
    name= 'KeysightDSOX2024A'
    version = '1.0'
    description='Oscilloscope'
    id_string='AGILENT TECHNOLOGIES,DSO-X 2024A,MY58104761,02.43.2018020635'
    max_window_horizontal_scale=2.5
    max_channel_scale=5
    points_in_record_count=100000
    command_dict={
        (b':MEASure:VAV?',1) : SimulatedOscilloscopeInstrument.measure_average,
        (b':MEASure:FREQ?',1) : SimulatedOscilloscopeInstrument.measure_frequency,
        (b':MEASure:VPP?',1) : SimulatedOscilloscopeInstrument.measure_peak_to_peak,
        (b':AUT',0) : SimulatedOscilloscopeInstrument.autoscale,
        (b':CHANnel1:DISPlay',1): (lambda self, val: SimulatedOscilloscopeInstrument.toggle_channel(self,'1',val)),
        (b':CHANnel2:DISPlay',1): (lambda self, val: SimulatedOscilloscopeInstrument.toggle_channel(self,'2',val)),
        (b':CHANnel3:DISPlay',1): (lambda self, val: SimulatedOscilloscopeInstrument.toggle_channel(self,'3',val)),
        (b':CHANnel4:DISPlay',1): (lambda self, val: SimulatedOscilloscopeInstrument.toggle_channel(self,'4',val)),
        (b':CHANnel1:DISPlay?',0): (lambda self : SimulatedOscilloscopeInstrument.toggle_channel(self,'1')),
        (b':CHANnel2:DISPlay?',0): (lambda self : SimulatedOscilloscopeInstrument.toggle_channel(self,'2')),
        (b':CHANnel3:DISPlay?',0): (lambda self : SimulatedOscilloscopeInstrument.toggle_channel(self,'3')),
        (b':CHANnel4:DISPlay?',0): (lambda self : SimulatedOscilloscopeInstrument.toggle_channel(self,'4')),
        (b':MEASure:CLEar',0): None,
        
        (b':CHANnel1:OFFSet',1): (lambda self,val : SimulatedOscilloscopeInstrument.channel_offset(self,'1',val)),
        (b':CHANnel2:OFFSet',1): (lambda self,val : SimulatedOscilloscopeInstrument.channel_offset(self,'2',val)),
        (b':CHANnel3:OFFSet',1): (lambda self,val : SimulatedOscilloscopeInstrument.channel_offset(self,'3',val)),
        (b':CHANnel4:OFFSet',1): (lambda self,val : SimulatedOscilloscopeInstrument.channel_offset(self,'4',val)),
        (b':CHANnel1:OFFSet?',0): (lambda self : SimulatedOscilloscopeInstrument.channel_offset(self,'1')),
        (b':CHANnel2:OFFSet?',0): (lambda self : SimulatedOscilloscopeInstrument.channel_offset(self,'2')),
        (b':CHANnel3:OFFSet?',0): (lambda self : SimulatedOscilloscopeInstrument.channel_offset(self,'3')),
        (b':CHANnel4:OFFSet?',0): (lambda self : SimulatedOscilloscopeInstrument.channel_offset(self,'4')),
        
        (b':CHANnel1:SCALe',1): (lambda self,val : SimulatedOscilloscopeInstrument.channel_scale(self,'1',val)),
        (b':CHANnel2:SCALe',1): (lambda self,val : SimulatedOscilloscopeInstrument.channel_scale(self,'2',val)),
        (b':CHANnel3:SCALe',1): (lambda self,val : SimulatedOscilloscopeInstrument.channel_scale(self,'3',val)),
        (b':CHANnel4:SCALe',1): (lambda self,val : SimulatedOscilloscopeInstrument.channel_scale(self,'4',val)),
        (b':CHANnel1:SCALe?',0): (lambda self : SimulatedOscilloscopeInstrument.channel_scale(self,'1')),
        (b':CHANnel2:SCALe?',0): (lambda self : SimulatedOscilloscopeInstrument.channel_scale(self,'2')),
        (b':CHANnel3:SCALe?',0): (lambda self : SimulatedOscilloscopeInstrument.channel_scale(self,'3')),
        (b':CHANnel4:SCALe?',0): (lambda self : SimulatedOscilloscopeInstrument.channel_scale(self,'4')),
        (b':TIMe:SCALe',1): SimulatedOscilloscopeInstrument.horizontal_scale,
        (b':TIMe:SCALe?',0): SimulatedOscilloscopeInstrument.horizontal_scale,
        (b':TIMe:POSition',1): SimulatedOscilloscopeInstrument.horizontal_position,
        (b':TIMe:POSition?',0): SimulatedOscilloscopeInstrument.horizontal_position

        
        }
        
