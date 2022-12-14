"""
### BEGIN NODE INFO
[info]
name = Parameter Vault
version = 2.0
description =
instancename = Parameter Vault

[startup]
cmdline = %PYTHON% %FILE%
timeout = 20

[shutdown]
message = 987654321
timeout = 20
### END NODE INFO
"""
from labrad.server import LabradServer, setting, Signal
from twisted.internet.defer import inlineCallbacks


class ParameterVault(LabradServer):
    """
    Data Server for storing ongoing experimental parameters
    """
    name = "Parameter Vault"
    registryDirectory = ['', 'Servers', 'Parameter Vault']
    onParameterChange = Signal(612512, 'signal: parameter change', '(ss)')

    @inlineCallbacks
    def initServer(self):
        self.listeners = set()
        self.parameters = {}
        yield self.load_parameters()

    def initContext(self, c):
        """Initialize a new context object."""
        self.listeners.add(c.ID)

    def expireContext(self, c):
        self.listeners.remove(c.ID)

    def getOtherListeners(self, c):
        notified = self.listeners.copy()
        notified.remove(c.ID)
        return notified

    @inlineCallbacks
    def load_parameters(self):
        # recursively add all parameters to the dictionary
        yield self._addParametersInDirectory(self.registryDirectory, [])

    @inlineCallbacks
    def _addParametersInDirectory(self, topPath, subPath):
        yield self.client.registry.cd(topPath + subPath)
        directories, parameters = yield self.client.registry.dir()
        if subPath:  # ignore parameters in the top level
            for parameter in parameters:
                value = yield self.client.registry.get(parameter)
                key = tuple(subPath + [parameter])
                self.parameters[key] = value
        for directory in directories:
            newpath = subPath + [directory]
            yield self._addParametersInDirectory(topPath, newpath)

    def _get_parameter_names(self, collection):
        names = []
        for key in self.parameters.keys():
            if list(key[:len(collection)]) == collection: #should this only require prefix or whole path? Another possibility: include all parameters below with . notation (relative to collection)- definitely necessary to deal with duplicates
                names.append('.'.join(key[len(collection):]))
        return names

    def _get_collections(self): #should this only require prefix or whole path? probably prefix (
        names = set()
        for key in self.parameters.keys():
            for i in range(len(key)-1):
                names.add(tuple(key[:i+1]))
        return [list(name) for name in names]

    @inlineCallbacks
    def save_parameters(self):
        '''save the latest parameters into registry'''
        regDir = self.registryDirectory
        for key, value in self.parameters.items():
            key = list(key)
            parameter_name = key.pop()
            fullDir = regDir + key
            yield self.client.registry.cd(fullDir)
            yield self.client.registry.set(parameter_name, value)

    def _save_full(self, key, value):
        t, item = self.parameters[key]
        if t == 'parameter':
            parameter_bound = "Parameter {} Out of Bound"
            assert item[0] <= value <= item[1], parameter_bound.format(key[1])
            item[2] = value
            return (t, item)
        else:
            raise Exception("Can't save, not one of checkable types")

    def _check_parameter(self, key, value):
        """
        Parameters
        ----------
        key: str, parameter name
        value:

        Returns
        -------
        parameter "item" if parameter's value passes checks.
        """
        param_type, item = value

        # Error strings
        parameter_bound = "Parameter {} Out of Bound"
        bad_selection = "Inorrect selection made in {}"

        if param_type == 'parameter' or param_type == 'duration_bandwidth':
            assert item[0] <= item[2] <= item[1], parameter_bound.format(key)
            return item[2]

        elif param_type == 'string':
            return item

        elif param_type == 'bool':
            return item

        elif param_type == 'sideband_selection':
            return item

        elif param_type == 'spectrum_sensitivity':
            return item

        elif param_type == 'scan':
            minim, maxim = item[0]
            start, stop, steps = item[1]
            assert minim <= start <= maxim, parameter_bound.format(key)
            assert minim <= stop <= maxim, parameter_bound.format(key)
            return (start, stop, steps)

        elif param_type == 'selection_simple':
            assert item[0] in item[1], bad_selection.format(key)
            return item[0]

        elif param_type == 'line_selection':
            assert item[0] in dict(item[1]).keys(), bad_selection.format(key)
            return item[0]

        else:  # parameter type not known
            return value

    @setting(0, "Set Parameter", collection=['s','*s'], parameter_name='s', value='?',
             full_info='b', returns='')
    def setParameter(self, c, collection, parameter_name, value,
                     full_info=False):
        """Set Parameter"""
        if isinstance(collection,str):
            collection=[collection]
        key = (*collection, *parameter_name.split('.'))
        if key not in self.parameters.keys():
            raise Exception(str(key) + " Parameter Not Found")
        if full_info:
            self.parameters[key] = value
        else:
            self.parameters[key] = self._save_full(key, value)
        notified = self.getOtherListeners(c)
        self.onParameterChange((key[0], key[1]), notified)

    @setting(1, "Get Parameter", collection=['s','*s'], parameter_name='s',
             checked='b', returns=['?'])
    def getParameter(self, c, collection, parameter_name, checked=True):
        """Get Parameter Value"""
        if isinstance(collection,str):
            collection=[collection]
        key = (*collection, *parameter_name.split('.'))
        if key not in self.parameters.keys():
            raise Exception(str(key) + "  Parameter Not Found")
        value = self.parameters[key]
        if checked:
            value = self._check_parameter(key, value)
        return value

    @setting(2, "Get Parameter Names", collection=['s','*s'], returns='*s')
    def getParameterNames(self, c, collection):
        """Get Parameter Names"""
        if isinstance(collection,str):
            collection=[collection]
        parameter_names = self._get_parameter_names(collection)
        return parameter_names

    @setting(3, "Save Parameters To Registry", returns='')
    def saveParametersToRegistry(self, c):
        """Get Experiment Parameter Names"""
        yield self.save_parameters()

    @setting(4, "Get Collections", returns='**s')
    def get_collection_names(self, c):
        collections = self._get_collections()
        return collections

    @setting(5, "Refresh Parameters", returns='')
    def refresh_parameters(self, c):
        """Saves Parameters To Registry, then realods them"""
        yield self.save_parameters()
        yield self.load_parameters()

    @setting(6, "Reload Parameters", returns='')
    def reload_parameters(self, c):
        """Discards current parameters and reloads them from registry"""
        yield self.load_parameters()

    @inlineCallbacks
    def stopServer(self):
        try:
            yield self.save_parameters()
        except AttributeError:
            # if values don't exist yet, i.e stopServer was called due to an
            # Identification Error
            pass

if __name__ == "__main__":
    from labrad import util
    util.runServer(ParameterVault())
