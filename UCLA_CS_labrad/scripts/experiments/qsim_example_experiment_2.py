#!scriptscanner

import time
import labrad
from labrad.units import WithUnit as U
from UCLA_CS_labrad.scripts.experiments.qsimexperiment import QsimExperiment


class QsimExampleExperiment2(QsimExperiment):

    name = 'Qsim Example Experiment 2'  # gives a name to display on scripscanner

    '''
    This expirement_example inherits from the QsimExperiment Class which in
    turn inherits from the experiment class. This provides functionality for
    saving data, plotting and connecting to script scanner in order to register
    experiments and update progress

    This has been modified from the original example experiment in that it attempts 
    to connect to a serial device, and uses both read and write functionality on the serial bus
    
    QsimExampleExperiment2 uses a device called “AMO3” which is a “Piezo Box”.
    This instrument is a serial device made in-house at UCLA. 
    
    To set up the experiment, a Piezo Box must be plugged into a computer running a Serial Bus Server,
    and the AMO3Server (a full server subclassed from the SDS) must have selected the node and port
    this box is connected to. Channel 1 of the device must be toggled on and set to output some voltage v.
    
    If device is simulated, the "AMO3" is an instance of SimulatedAMO3Instrument in the Hardware
    Simulation Server. Simulating this experiment shows we can change the value of a property of a
    simulated serial device via a serial command.
    '''

    # The following defines which parameters you would like to use from
    # parameter vault All parameters must be defined in the registry under
    # the Parameter Vault folder before they are available in the experiment.
    # All parameters will be available in the main experiment function via a
    # variable named self.p.parameter_folder.parameter
    
    #QsimExampleExperiment2 has 2 parameters, Range and Amplitude. Range is a scan parameter and Amplitude is a float parameter.

    exp_parameters = []
    exp_parameters.append(('Qsim Example Experiment 2 Parameters', 'Range'))  # The format is (parameter folder, parameter)
    exp_parameters.append(('Qsim Example Experiment 2 Parameters', 'Amplitude'))
    


    def initialize(self, cxn, context, ident):

        '''
        This function does any initialization needed, Such as connecting to
        equipment servers or setting up Data Vault or the grapher.
        Objects available in this function are cxn (a connection to LabRAD),
        context (the LabRAD connection id) and ident (the scriptscanner connection id)
        '''

        self.ident = ident  # this is required so that script scanner can sort and access different instances
        self.pzt_server = cxn.piezo_server
        self.pzt_channel = 1

    def run(self, cxn, context):

        '''
        This is where the magic happens. Here is where you write your experiment using
        the parameters imported to affect equipment that you connected to in initialize. For this
        example we will draw a parabola for a given range with a given amplitude
        '''
        self.setup_datavault('Range', 'Amplitude')  # gives the x and y names to Data Vault
        #self.setup_grapher('experiment_example')  # Tells the grapher which tab to plot the data on
        
        self.amplitude = self.p.example_parameters.Amplitude  # shortens the amplitude name
        
        # the following generates a list of the points used in the scan. If the points
        # have LabRAD unit types they can be specified in the second argument
        self.x_values = self.get_scan_list(self.p.example_parameters.Range, units=None)

        # The experiment first makes an AMO3 Server request to get the voltage v the instrument is outputting from channel 1.
        self.pzt_voltage = self.pzt_server.voltage(self.pzt_channel)

        for i, x_point in enumerate(self.x_values):  # Main Loop. Every iteration will have an index i and an associated x point 

            # The following updates the Script Scanner progress with a number between 0 and 1
            # with 0 being 0% and 1 being 100% completed. If the user has pressed stop on script scanner the for loop
            # is broken. This functionality is optional but extremely helpful.

            should_break = self.update_progress(i/float(len(self.x_values)))
            if should_break:
                break

            y_point = self.amplitude * 0.5*(x_point**3) # calculates the parabola
            
            self.pzt_server.voltage(self.pzt_channel, self.pzt_voltage + y_point)
            #For each x-value encoded in the range parameter, it sets channel 1 of the box to (v+.5*a*x^3),
            #where a is the amplitude parameter.
			
            assert self.pzt_server.voltage(self.pzt_channel) != self.pzt_voltage
            #uses an assert statement each time to assure the constant voltage the box is
            #outputting has changed from the voltage it was outputting at the experiment’s start

            self.dv.add(x_point, y_point)  # adds the data to Data Vault which will be automatically plotted

            time.sleep(0.2)

    def finalize(self, cxn, context):
        '''
        In the finalize function we can close any connections or stop any
        processes that are no longer necessary.
        '''
        pass  # no processes to stop

if __name__ == '__main__':
    # Launches script if code is run from terminal instead of script scanner
    cxn = labrad.connect()  # creates LabRAD connection
    scanner = cxn.scriptscanner  # connects to script scanner server
    exprt = QsimExampleExperiment2(cxn=cxn)  # instantiates the experiment
    ident = scanner.register_external_launch(exprt.name)  # registers an experiment with Script Scanner
    exprt.execute(ident)  # executes the experiment
