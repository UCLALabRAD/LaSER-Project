import numpy as np
from labrad.gpib import GPIBDeviceWrapper
from twisted.internet.defer import inlineCallbacks, returnValue

_TEKTRONIXTDS2000_PROBE_ATTENUATIONS = ( 1, 10, 100, 1000)


class TektronixTDS2000Wrapper(GPIBDeviceWrapper):

    # SYSTEM
    @inlineCallbacks
    def reset(self):
        """
        Reset the oscilloscopes to factory settings.
        """
        yield self.write('*RST')

    @inlineCallbacks
    def clear_buffers(self):
        """
        Clear device status buffers.
        """
        yield self.write('*CLS')


    # CHANNEL
    @inlineCallbacks
    def channel_info(self, channel):
        """
        Get channel information.
        Arguments:
            channel (int): channel to query
        Returns:
            Tuple of (on/off, attenuation, scale, offset, coupling, invert)
        """
        onoff = yield self.channel_toggle(channel)
        probeAtten = yield self.channel_probe(channel)
        scale = yield self.channel_scale(channel)
        offset = yield self.channel_offset(channel)
        coupling = yield self.channel_coupling(channel)
        invert = yield self.channel_invert(channel)
        returnValue((onoff, probeAtten, scale, offset, coupling, invert))

    @inlineCallbacks
    def channel_coupling(self, channel, coupling=None):
        """
        Set or query channel coupling.
        Arguments:
            channel (int): Which channel to set coupling.
            coup (str): Coupling, 'AC' or 'DC'. If None (the default) just query
                the coupling without setting it.
        Returns:
            string indicating the channel's coupling.
        """
        chString = 'CH{:d}:COUP'.format(channel)
        if coupling is not None:
            coupling = coupling.upper()
            if coupling in ('AC', 'DC', 'GND'):
                yield self.write(chString + ' ' + coupling)
            else:
                raise Exception('Error: Coupling must be one of: (AC, DC, GND).')
        resp = yield self.query(chString + '?')
        returnValue(resp.strip())

    @inlineCallbacks #TODO: change range (seems to depend on attenuation)
    def channel_scale(self, channel, scale=None):
        """
        Get or set the vertical scale.
        Arguments:
            channel (int): The channel to get or set.
            scale   (float): The vertical scale (in volts/div).
        Returns:
            (float): The vertical scale (in volts/div).
        """
        chString = 'CH{:d}:SCA'.format(channel)
        if scale is not None:
            if (scale > 1e-3) and (scale < 1e1):
                yield self.write(chString + ' ' + str(scale))
            else:
                raise Exception('Error: Scale must be in range: [1e-3, 1e1]')
        resp = yield self.query(chString + '?')
        returnValue(float(resp))

    @inlineCallbacks
    def channel_probe(self, channel, atten=None):
        """
        todo
        Get/set the probe attenuation factor.
        Arguments:
            channel (int): the channel to get/set
            factor (float): the probe attenuation factor
        Returns:
            (float): the probe attenuation factor
        """
        chString = 'CH{:d}:PRO'.format(channel)
        if atten is not None:
            if atten in _TEKTRONIXTDS2000_PROBE_ATTENUATIONS:
                yield self.write(chString + ' ' + str(atten))
            else:
                raise Exception('Error: Probe attenuation must be one of: ' + str(_TEKTRONIXTDS2000_PROBE_ATTENUATIONS))
        resp = yield self.query(chString + '?')
        returnValue(float(resp))

    @inlineCallbacks
    def channel_toggle(self, channel, state=None):
        """
        Set or query channel on/off state.
        Arguments:
            channel (int): the channel to get/set
            state (bool): True->On, False->Off.
        Returns:
            (bool): The channel state.
        """
        chString = 'SEL:CH{:d}'.format(channel)
        if state is not None:
            yield self.write(chString + ' ' + str(int(state)))
        resp = yield self.query(chString + '?')
        returnValue(bool(int(resp)))

    @inlineCallbacks
    def channel_invert(self, channel, invert=None):
        """
        Get or set channel inversion.
        Arguments:
            channel (int): the channel to get/set
            invert (bool): True->invert, False->do not invert channel.
        Returns:
            (int): 0: not inverted, 1: inverted.
        """
        chString = ":CH{:d}:INV".format(channel)
        if invert is not None:
            if invert:
                invert='ON'
            else:
                invert='OFF'
            yield self.write(chString + ' ' + invert)
        resp = yield self.query(chString + '?')
        print(resp)
        returnValue((resp=='ON'))

    @inlineCallbacks  #TODO: change range (seems to depend on scale)
    def channel_offset(self, channel, offset=None):
        """
        Get or set the vertical offset.
        Arguments:
            channel (int): the channel to get/set
            offset (float): Vertical offset in units of divisions. If None,
                (the default), then we only query.
        Returns:
            (float): Vertical offset in units of divisions.
        """
        # value is in volts
        chString = ":CH{:d}:POS".format(channel)
        if offset is not None:
            if (offset > 1e-4) and (offset < 1e1):
                yield self.write(chString + ' ' + str(offset))
            else:
                raise Exception('Error: Scale must be in range: [1e-3, 1e1]')
        resp = yield self.query(chString + '?')
        returnValue(float(resp))


    # TRIGGER
    @inlineCallbacks
    def trigger_channel(self, channel=None):
        """
        Set or query trigger channel.
        Arguments:
            source (str): channel name
        Returns:
            (str): Trigger source.
        """
        # note: target channel must be on
        chString = 'TRIG:MAI:EDGE:SOU'
        if channel is not None:
            if channel in (1, 2, 3, 4):
                yield self.write(chString + ' CH' + str(channel))
            else:
                raise Exception('Error: Trigger channel must be one of: ' + str((1, 2, 3, 4)))
        resp = yield self.query(chString + '?')
        returnValue(resp.strip())

    @inlineCallbacks
    def trigger_slope(self, slope=None):
        """
        Set or query trigger slope.
        Arguments:
            slope (str): the slope to trigger on (e.g. rising edge)
        Returns:
            (str): the slope being triggered off
        """
        chString = 'TRIG:MAI:EDGE:SLO'
        if slope is not None:
            slope = slope.upper()
            if slope in ('FALL', 'RIS'):
                yield self.write(chString + ' ' + slope)
            else:
                raise Exception('Error: Slope must be one of: ' + str(('FALL', 'RIS')))
        resp = yield self.query(chString + '?')
        returnValue(resp.strip())

    @inlineCallbacks #fix range logic?
    def trigger_level(self, channel, level=None):
        """
        Set or query the trigger level.
        Arguments:
            channel (int)   :  the channel to set the trigger for
            level   (float) : the trigger level (in V)
        Returns:
            (float): the trigger level (in V).
        """
        chString = 'TRIG:MAI:LEV'
        if level is not None:
            chan_tmp = yield self.trigger_channel()
            vscale_tmp = yield self.channel_scale(int(chan_tmp[-1]))
            level_max = 5 * vscale_tmp
            if (level == 0) or (abs(level) <= level_max):
                yield self.write(chString + ' ' + str(level))
            else:
                raise Exception('Error: Trigger level must be in range: ' + str((-level_max, level_max)))
        resp = yield self.query(chString + '?')
        returnValue(float(resp))

    @inlineCallbacks
    def trigger_mode(self, mode=None):
        """
        Set or query the trigger mode.
        Arguments:
            mode (str): The trigger mode.
        Returns:
            (str): The trigger mode.
        """
        chString = 'TRIG:MAI:MOD'
        if mode is not None:
            if mode in ('AUTO', 'NORM'):
                yield self.write(chString + ' ' + mode)
            else:
                raise Exception('Error: Trigger mode must be one of: ' + str(('AUTO', 'NORM')))
        resp = yield self.query(chString + '?')
        returnValue(resp.strip())


    # HORIZONTAL
    @inlineCallbacks #TODO:Range change? horizontal position knob ( depends on scale)
    def horizontal_offset(self, offset=None):
        """
        Set or query the horizontal offset.
        Arguments:
            offset (float): the horizontal offset (in seconds).
        Returns:
            (float): the horizontal offset in (in seconds).
        """
        chString = 'HOR:MAI:POS'
        if offset is not None:
            if (offset == 0) or ((abs(offset) > 1e-6) and (abs(offset) < 1e0)):
                yield self.write(chString + ' ' + str(offset))
            else:
                raise Exception('Error: Horizontal offset must be in range: ' + str('(1e-6, 1e0)'))
        resp = yield self.query(chString + '?')
        returnValue(float(resp))

    @inlineCallbacks
    def horizontal_scale(self, scale=None):
        """
        Set or query the horizontal scale.
        Arguments:
            scale (float): the horizontal scale (in s/div).
        Returns:
            (float): the horizontal scale (in s/div).
        """
        chString = 'HOR:MAI:SCA'
        if scale is not None:
            if (scale > 1e-6) and (scale < 50):
                yield self.write(chString + ' ' + str(scale))
            else:
                raise Exception('Error: Horizontal scale must be in range: ' + str('(1e-6, 50)'))
        resp = yield self.query(chString + '?')
        returnValue(float(resp))


    # ACQUISITION
    @inlineCallbacks
    def get_trace(self, channel, points=None):
        """
        Get a trace for a single channel.
        Arguments:
            channel: The channel for which we want to get the trace.
        Returns:
            Tuple of ((ValueArray[s]) Time axis, (ValueArray[V]) Voltages).
        """

        # configure trace
        yield self.write('DAT:SOU CH{:d}'.format(channel))
        yield self.write('DAT:STAR 1')
        yield self.write('DAT:ENC ASCI')
        yield self.write('DAT:STOP {:d}'.format(points))

        # get preamble
        preamble = yield self.query('WFMP?')
        # get waveform
        data = yield self.query('CURV?')
        data=data[6:]
        # parse waveform preamble
        points, xincrement, xorigin, yorigin, ymult, yoff = self._parsePreamble(preamble)
        # parse data
        trace = self._parseByteData(data)
        # format data
        xAxis = np.arange(points) * xincrement + xorigin
        yAxis = (trace - yoff) * ymult + yorigin
        returnValue((xAxis, yAxis))

    # HELPER
    def _parsePreamble(self, preamble):
        fields = preamble.split(';')
        points = int(fields[5])
        xincrement = float(fields[8])
        xorigin= float(fields[10])
        yorigin=float(fields[13])
        ymult=float(fields[12])
        yoff=float(fields[14])
        # print(str((points, xincrement, xorigin, xreference, yincrement, yorigin, yreference)))
        return (points, xincrement, xorigin, yorigin, ymult, yoff)

    def _parseByteData(self, data):
        """
        Parse byte data
        """
        trace = np.array(data.split(','), dtype=float)
        return trace