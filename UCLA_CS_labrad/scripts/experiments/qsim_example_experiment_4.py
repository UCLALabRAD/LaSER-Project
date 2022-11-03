#!scriptscanner

import time
import labrad
import numpy as np
from labrad.units import WithUnit as U
from UCLA_CS_labrad.scripts.experiments.qsimexperiment import QsimExperiment


class LaserExperiment4(QsimExperiment):

    # gives a name to display on scriptscanner
    name = 'LaSER Experiment 4'

    """
    This sample experiment inherits from the QsimExperiment Class, which in
        turn inherits from the experiment class. This provides functionality for
        saving data, plotting and connecting to script scanner in order to register
        experiments and update progress.
    """

    # The following defines which parameters you would like to use from
    # parameter vault All parameters must be defined in the registry under
    # the Parameter Vault folder before they are available in the experiment.
    # All parameters will be available in the main experiment function via a
    # variable named self.p.parameter_folder.parameter

    # The format is (parameter folder, parameter)
    exp_parameters = [
        # piezo parameters
        ('example_parameters', 'Piezo_Connection_Bus'),
        ('example_parameters', 'Piezo_Connection_Port'),
        ('example_parameters', 'Piezo_Channel'),

        # oscilloscope parameters
        ('example_parameters', 'Oscilloscope_Name'),
        ('example_parameters', 'Oscilloscope_Channel'),

        # output parameters
        ('example_parameters', 'PWM_Length'),
        ('example_parameters', 'PWM_Frequency'),
        ('example_parameters', 'PWM_Voltage'),
        
        # readout parameters
        ('example_parameters', 'Poll_Interval')
    ]

    def initialize(self, cxn, context, ident):
        """
        This function does any initialization needed, such as connecting
            to equipment servers or setting up Data Vault or the grapher.

        Objects available in this function are:
            cxn (a connection to LabRAD),
            context (the LabRAD connection id)
            ident (the scriptscanner connection id)
            self.p.example_parameters.
        """
        # required for script scanner to manage different instancesself.ident = ident

        # set up datavault
        self.setup_datavault(('Time',), ('Mean Voltage', 'Frequency'))   # gives the x and y names to Data Vault
        #self.setup_grapher('experiment_example')    # tells the grapher which tab to plot the data on

        # set up piezo
        self.piezo_server = cxn.amo3server
        self.piezo_server.device_select(self.p.example_parameters.Piezo_Connection_Bus,self.p.example_parameters.Piezo_Connection_Port)
        self.piezo_server.toggle(self.p.example_parameters.Piezo_Channel, 1)
        
        # set up oscilloscope
        self.os_server = cxn.oscilloscope_server
        self.os_server.select_device(self.p.example_parameters.Oscilloscope_Name)
        self.os_server.channel_toggle(self.p.example_parameters.Oscilloscope_Channel, True)

        # set up channel display
        self.os_server.autoscale()

        # set up measurement
        self.os_server.measure_setup(1, self.p.example_parameters.Oscilloscope_Channel, "MEAN")
        self.os_server.measure_setup(2, self.p.example_parameters.Oscilloscope_Channel, "FREQ")


    def run(self, cxn, context):
        """
        Here is where you write your experiment using the parameters imported
            to affect equipment that you connected to in initialize.

        For this example, we will draw a waveform corresponding to the one being generated by
            the function generator.
        """
        params = self.p.example_parameters
        
        # generate points in time for piezo to do PWM
        x_max = params.PWM_Length
        x_points = int(params.PWM_Length * params.PWM_Frequency * 2)
        x_values = np.linspace(0, x_max, x_points + 1)
        
        # get oscilloscope poll period
        poll_value = int(params.Poll_Interval * params.PWM_Frequency * 2)
        # set up variables for PWM
        output_high = False
        self.piezo_server.voltage(1, 0)

        # main loop
        for i, x_point in enumerate(x_values):

            # The following updates the Script Scanner progress with a number between 0 and 1
            # with 0 being 0% and 1 being 100% completed. If the user has pressed stop on script scanner the for loop
            # is broken. This functionality is optional but extremely helpful.
            should_break = self.update_progress(i/float(len(x_values)))
            if should_break:
                break

            # toggle piezo voltage
            if output_high:
                self.piezo_server.voltage(1,0)
            else:
                self.piezo_server.voltage(1,params.PWM_Voltage)
            output_high = not output_high
            # read & record oscilloscope value
            if (i % poll_value) == 0:
                # get oscilloscope reading
                voltage_mean = self.os_server.measure(1)
                print(voltage_mean)
                voltage_frequency = self.os_server.measure(2)
                print(voltage_frequency)
                # adds the data to Data Vault
                self.dv.add(x_point, voltage_mean, voltage_frequency)
            time.sleep(1.0/(2.0*params.PWM_Frequency))
    def finalize(self, cxn, context):
        """
        In the finalize function we can close any connections or stop any
            processes that are no longer necessary.
        """
        # switch off piezo
        self.piezo_server.toggle(self.p.example_parameters.Piezo_Channel, False)


if __name__ == '__main__':
    # Launches script if code is run from terminal instead of script scanner
    cxn = labrad.connect()                                  # creates LabRAD connection
    scanner = cxn.cs_script_scanner                             # connects to script scanner server
    exprt = LaserExperiment4(cxn=cxn)                     # instantiates the experiment
    ident = scanner.register_external_launch(exprt.name)    # registers an experiment with Script Scanner
    exprt.execute(ident)                                    # executes the experiment
