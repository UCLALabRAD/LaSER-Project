"""
### BEGIN NODE INFO
[info]
name = AMO3Server
version = 1.0.0
description = Communicates with the AMO3 box for control of piezo voltages.
instancename = AMO3Server

[startup]
cmdline = %PYTHON% %FILE%
timeout = 20

[shutdown]
message = 987654321
timeout = 20
### END NODE INFO
"""

from labrad.units import WithUnit
from labrad.server import setting, Signal, inlineCallbacks

from twisted.internet.defer import returnValue
from UCLA_CS_labrad.servers import SerialDeviceServer
from UCLA_CS_labrad.servers.hardwaresimulation import SimulatedPiezoInstrument

TERMINATOR = '\r\n'


class AMO3Server(SerialDeviceServer):
    """
    Communicates with the AMO3 box for control of piezo voltages.
    """

    name = 'AMO3Server'
    regKey = 'AMO3Server'
    default_node = None
    default_port = None
    
    timeout = WithUnit(10.0, 's')
    baudrate = 38400


    # SIGNALS
    voltage_update = Signal(999999, 'signal: voltage update', '(iv)')
    toggle_update = Signal(999998, 'signal: toggle update', '(ib)')

    # CONTEXTS
    def initContext(self, c):
        super().initContext(c)
        self.listeners.add(c.ID)

    def expireContext(self, c):
        self.listeners.remove(c.ID)

    def getOtherListeners(self, c):
        notified = self.listeners.copy()
        notified.remove(c.ID)
        return notified

    def notifyOtherListeners(self, context, message, f):
        """
        Notifies all listeners except the one in the given context, executing function f.
        """
        notified = self.listeners.copy()
        notified.remove(context.ID)
        f(message, notified)


    # STARTUP
    def initServer(self):
        super().initServer()
        self.listeners = set()


    # GENERAL
    @setting(12, 'Remote', remote_status='b')
    def remote(self, c, remote_status=None):
        """
        Set remote mode of device.
        Arguments:
            remote_status   (bool)  : whether the device accepts serial commands
        Returns:
                            (bool)  : whether the device accepts serial commands
        """
        if remote_status is not None:
            yield c['Serial Connection'].acquire()
            yield c['Serial Connection'].write('remote.w {:d}\r\n'.format(remote_status))
            yield c['Serial Connection'].read_line()
            c['Serial Connection'].release()
        # getter
        yield c['Serial Connection'].acquire()
        yield c['Serial Connection'].write('remote.r\r\n')
        resp = yield c['Serial Connection'].read_line()
        c['Serial Connection'].release()
        # parse
        resp = bool(int(resp.strip()))
        returnValue(resp)


    # ON/OFF
    @setting(111, 'Toggle', channel='i', power='i', returns='b')
    def toggle(self, c, channel, power=None):
        """
        Set a channel to be on or off.
        Args:
            channel (int)   : the channel to read/write.
            power   (bool)  : whether channel is to be on or off
        Returns:
                    (bool)  : result
        """
        if channel not in (1, 2, 3, 4):
            raise Exception("Error: channel must be one of (1, 2, 3, 4).")
        # setter
        if power is not None:
            yield c['Serial Connection'].acquire()
            print('out.w {:d} {:d}\r\n'.format(channel, power))
            yield c['Serial Connection'].write('out.w {:d} {:d}\r\n'.format(channel, power))
            yield c['Serial Connection'].read_line()
            c['Serial Connection'].release()
        # getter
        yield c['Serial Connection'].acquire()
        yield c['Serial Connection'].write('out.r {:d}\r\n'.format(channel))
        resp = yield c['Serial Connection'].read_line()
        c['Serial Connection'].release()
        
        # parse


        resp = resp.strip()
        resp = bool(int(resp))
        self.notifyOtherListeners(c, (channel, resp), self.toggle_update)
        returnValue(resp)


    # VOLTAGE
    @setting(211, 'Voltage', channel='i', voltage='v', returns='v')
    def voltage(self, c, channel, voltage=None):
        """
        Sets/get the channel voltage.
        Arguments:
            channel (int)   : the channel to read/write
            voltage (float) : the channel voltage to set
        Returns:
                    (float) : the channel voltage
        """
        # setter
        if channel not in (1, 2, 3, 4):
            raise Exception("Error: channel must be one of (1, 2, 3, 4).")
        if voltage is not None:
            if (voltage < 0) or (voltage > 150):
                raise Exception("Error: voltage must be in [0, 150].")
            yield c['Serial Connection'].acquire()
            yield c['Serial Connection'].write('vout.w {:d} {:3f}\r\n'.format(channel, voltage))
            yield c['Serial Connection'].read_line()
            c['Serial Connection'].release()
        # getter
        yield c['Serial Connection'].acquire()
        yield c['Serial Connection'].write('vout.r {:d}\r\n'.format(channel))
        resp = yield c['Serial Connection'].read_line()
        c['Serial Connection'].release()
        resp = float(resp)
        self.notifyOtherListeners(c, (channel, resp), self.voltage_update)
        returnValue(float(resp))


if __name__ == '__main__':
    from labrad import util
    util.runServer(AMO3Server())
    

#Specific device class for simulated AMO3 Piezo Box (Serial Device).
class SimulatedAMO3(SimulatedPiezoInstrument):
    name= 'AMO3'
    version = '1.0'
    description='test piezo'
    
    #Here, we define class properties that were set to None in the generic device (parent) class,
    #SimulatedPiezoInstrument, giving them values specific to the AMO3 model.
    
    

    #See SimulatedInstrumentInterface
    channel_count=4

    
    #See SimulatedSerialInstrumentInterface
    required_baudrate=38400
    
    #See SimulatedPiezoInstrument
    voltage_range=(0,150.0)
    set_voltage_string="vout.w : set output {} to {:.3f}"
    set_toggle_on_string="out.w : output {} enabled"
    set_toggle_off_string="out.w : output {} disabled"
    
    
    #See SimulatedInstrumentInterface to learn about the command_dict, and SimulatedPiezoInstrument
    #to see definitions of this one's handler functions
    command_dict={
        (b'remote.r',1)           : None,
        (b'remote.w',2)        : None,
        (b'out.r',1)    : SimulatedPiezoInstrument.get_channel_status,
        (b'out.w',2)    : SimulatedPiezoInstrument.set_channel_status,
        (b'vout.r',1)   : SimulatedPiezoInstrument.get_channel_voltage,
        (b'vout.w',2)  : SimulatedPiezoInstrument.set_channel_voltage }
        
    
    
    
