from twisted.internet.task import LoopingCall
from labrad.server import LabradServer, setting


__all__ = ["PollingServer"]


"""
Polling Server
"""
class PollingServer(LabradServer):
    """
    Holds all the functionality needed to run polling loops on the server.
    Also contains functionality for Signals.
    """

    # tells server whether to start polling upon startup
    POLL_ON_STARTUP = False
    POLL_INTERVAL_ON_STARTUP = 5

    # STARTUP
    def initServer(self):
        # call parent initserver to support further subclassing
        super().initServer()
        # signal stuff
        self.listeners = set()
        # create refresher for polling
        self.refresher = LoopingCall(self._poll)
        # set startup polling
        self.refresher.start(self.POLL_INTERVAL_ON_STARTUP, now=False)
        if not self.POLL_ON_STARTUP:
            self.refresher.stop()

    def stopServer(self):
        super().stopServer()
        if hasattr(self, 'refresher'):
            if self.refresher.running:
                self.refresher.stop()


    # CONTEXT
    def initContext(self, c):
        """
        Initialize a new context object.
        """
        self.listeners.add(c.ID)

    def expireContext(self, c):
        """
        Remove a context object and stop polling if there are no more listeners.
        """
        self.listeners.remove(c.ID)
        if len(self.listeners) == 0:
            self.refresher.stop()
            print('Stopped polling due to lack of listeners.')

    def getOtherListeners(self, c):
        """
        Get all listeners except for the context owner.
        """
        notified = self.listeners.copy()
        notified.remove(c.ID)
        return notified

    def notifyOtherListeners(self, context, message, f):
        """
        Notifies all listeners except the one in the given context, executing function f
        """
        notified = self.listeners.copy()
        notified.remove(context.ID)
        f(message, notified)


    # POLLING
    @setting(911, 'Polling', status='b', interval='v', returns='(bv)')
    def Polling(self, c, status=None, interval=None):
        """
        Configure polling of device for values.
        """
        # empty call returns getter
        if (status is None) and (interval is None):
            return (self.refresher.running, self.refresher.interval)

        # ensure interval is valid
        if interval is None:
            interval = 5.0
        elif (interval < 1) or (interval > 60):
            raise Exception('Invalid polling interval.')

        # start polling if we are stopped
        if status and (not self.refresher.running):
            self.startRefresher(interval)
        # change polling interval if already running
        elif status and self.refresher.running:
            self.refresher.interval = interval
        # stop polling if we are running
        elif (not status) and self.refresher.running:
            self.refresher.stop()
        return (self.refresher.running, self.refresher.interval)

    def startRefresher(self, interval=None):
        """
        Starts the polling loop and calls errbacks.
        """
        d = self.refresher.start(interval, now=False)
        d.addErrback(self._poll_fail)

    def _poll(self):
        """
        Polls the device for pressure readout.
        To be subclassed.
        """
        pass

    def _poll_fail(self, failure):
        print('Polling failed. Restarting polling.')
        yield self.ser.flush_input()
        yield self.ser.flush_output()
        self.startRefresher(5)
        #todo: maybe don't have it auto restart polling

