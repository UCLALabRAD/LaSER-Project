import UCLA_CS_labrad.servers.scriptscanner.experiment as experiment
import numpy as np
import time


class QsimExperiment(experiment.experiment):

    @classmethod
    def all_required_parameters(cls):
        return cls.exp_parameters

    def __init__(self, name=None, required_parameters=None, cxn=None,
                 min_progress=0.0, max_progress=100.0,):

        required_parameters = self.all_required_parameters()
        super().__init__(name, required_parameters)

        if name is None:
            self.name = self.__class__.__name__
        else: 
            self.name = name
        self.p = self.parameters
        self.cxn = cxn
        self.pv = None
        self.sc = None

    def _connect(self):
        super()._connect()
        try:
            self.dv = self.cxn.servers['CS Data Vault']
        except KeyError as error:
            error_message = error + '\n' + "DataVault is not running"
            raise KeyError(error_message)
        

    def setup_datavault(self, x_axis, y_axis):

        '''
        Adds parameters to datavault and parameter vault
        '''
        self.dv.cd(['', self.name], True)
        self.dataset = self.dv.new(self.name, [(x_axis, 'num')],
                                   [(y_axis, '', 'num')])

        for parameter in self.p:
            self.dv.add_parameter(parameter, self.p[parameter])

        return self.dataset

    def update_progress(self, progress):
        if progress >= 1.0:
            progress = 1.0
        elif progress <= 0.0:
            progress = 0.0

        should_stop = self.pause_or_stop()
        self.sc.script_set_progress(self.ident, 100*progress)
        return should_stop

    def get_scan_list(self, scan, units):
        if units is None:
            minvalue = scan[0]
            maxvalue = scan[1]
        else:
            minvalue = scan[0][units]
            maxvalue = scan[1][units]

        num_steps = scan[2]
        scan_list = np.linspace(minvalue, maxvalue, num_steps)
        return list(scan_list)



    def _finalize(self, cxn, context):
        #self.pmt.set_mode(self.init_mode)
        self.finalize(cxn, context)
        self.sc.finish_confirmed(self.ident)
