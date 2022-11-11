from labrad.gpib import GPIBDeviceWrapper
from twisted.internet.defer import inlineCallbacks, returnValue
from scipy import signal
import numpy as np
from UCLA_CS_labrad.servers.hardwaresimulation import SimulatedFunctionGeneratorInstrument

class Agilent33210AWrapper(GPIBDeviceWrapper):

    # GENERAL
    @inlineCallbacks
    def reset(self):
        yield self.write('*RST')

    @inlineCallbacks
    def toggle(self, status):
        # setter
        if status is not None:
            yield self.write('OUTP {:d}'.format(status))
        # getter
        resp = yield self.query('OUTP?')
        resp = bool(int(resp))
        returnValue(resp)


    # WAVEFORM
    @inlineCallbacks
    def function(self, shape):
        if shape:
            shape = shape.upper()
            if shape in ("SIN", "SQU", "RAMP", "PULS", "NOIS", "DC"):
                yield self.write('FUNC {:s}'.format(shape))
            else:
                raise Exception('Error: invalid input. Shape must be one of (SIN, SQU, RAMP, PULS, NOIS, DC).')
        resp = yield self.query('FUNC?')
        returnValue(resp)

    @inlineCallbacks
    def frequency(self, freq):
        # setter
        if freq:
            if (freq < 1e7) and (freq > 1e-3):
                yield self.write('FREQ {:f}'.format(freq))
            else:
                raise Exception('Error: invalid input. Frequency must be in range [1mHz, 10MHz].')
        # getter
        resp = yield self.query('FREQ?')
        returnValue(float(resp))

    @inlineCallbacks
    def amplitude(self, ampl):
        # setter
        if ampl:
            if (ampl < 1e1) and (ampl > 1e-2):
                yield self.write('VOLT {:f}'.format(ampl))
            else:
                raise Exception('Error: invalid input. Amplitude must be in range [1e-2 Vpp, 1e1 Vpp].')
        # getter
        resp = yield self.query('VOLT?')
        returnValue(float(resp))

    @inlineCallbacks
    def offset(self, off):
        # setter
        if off:
            if (off < 1e1) and (off > 1e-2):
                yield self.write('VOLT:OFFS {:f}'.format(off))
            else:
                raise Exception('Error: invalid input. Amplitude offset must be in range [-1e1 Vpp, 1e1 Vpp].')
        # getter
        resp = yield self.query('VOLT:OFFS?')
        returnValue(float(resp))


    # MODULATION
    # todo

    # SWEEP
    # todo


#frequency,amplitude,toggle
class SimulatedAgilent33210A(SimulatedFunctionGeneratorInstrument):
    name= 'Agilent33210A'
    version = '1.0'
    description='test function generator'
    function_map={"SIN":np.sin,"SQU":signal.square,"RAMP":signal.sawtooth}#duty supported for square, symmetry supported for ramp
    freq_ranges={"SIN":(.001,10000000),"SQU":(.001,10000000),"RAMP":(.001,100000000)}
    max_voltage=5.0
    def_amp=.1
    def_freq=1000.0
    def_func="SIN"
    
    id_string='Agilent Technologies,33210A,MY48007979,1.04-1.04-22-2'
    command_dict={

        (b'OUTPut',1)           : SimulatedFunctionGeneratorInstrument.toggle,
        (b'FREQuency',1)        : SimulatedFunctionGeneratorInstrument.frequency,
        (b'VOLTage',1)        : SimulatedFunctionGeneratorInstrument.amplitude,
        (b'FUNCtion',1)        : SimulatedFunctionGeneratorInstrument.function,
        (b'VOLTage:OFFSet',1)        : SimulatedFunctionGeneratorInstrument.offset,
        (b'OUTPut?',0)           : SimulatedFunctionGeneratorInstrument.toggle,
        (b'FREQuency?',0)        : SimulatedFunctionGeneratorInstrument.frequency,
        (b'VOLTage?',0)        : SimulatedFunctionGeneratorInstrument.amplitude,
        (b'FUNCtion?',0)        : SimulatedFunctionGeneratorInstrument.function,
        (b'VOLTage:OFFSet?',0)        : SimulatedFunctionGeneratorInstrument.offset
    }
    freq_range=
    
    
            
