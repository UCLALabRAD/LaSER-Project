#!scriptscanner

import time
import labrad
import numpy as np
from labrad.units import WithUnit as U
from UCLA_CS_labrad.scripts.experiments.qsimexperiment import QsimExperiment


class QsimExampleExperiment4(QsimExperiment):

    # gives a name to display on scriptscanner
    name = 'Qsim Example Experiment 4'

    """
    This sample experiment inherits from the QsimExperiment Class, which in
        turn inherits from the experiment class. This provides functionality for
        saving data, plotting and connecting to script scanner in order to register
        experiments and update progress.
        
    QsimExampleExperiment4 uses an AMO3 Piezo Box and can use any Oscilloscope
    supported by the Oscilloscope Server (a full server subclassed from the GPIB Managed Device Server).
    
    To set up the experiment, a Piezo Box must be plugged into a computer running a Serial Bus Server.
    Also, an Oscilloscope must be plugged into a computer running a GPIB Bus Server.
    The GPIB Device Manager, Piezo Server, and Oscilloscope Server must be running.
    One of the Piezo Box’s output channels must be connected to one of the input channels of the Oscilloscope
    via a BNC cable.
    
    If devices are simulated, the "Oscilloscope" is an instance of a subclass of
    SimulatedOscilloscopeInstrument in the Hardware Simulation Server.

    Simulating this experiment shows that we can pass electrical signals through simulated cables,
    and that a simulated oscilloscope can construct these signals’ waveforms via sampling the voltage
    coming in through an input channel, and make measurements from these internal drawings. It shows
    that we can make a simulated serial device’s output signal change automatically based on serial commands sent to it.
    
    
    """

    # The following defines which parameters you would like to use from
    # parameter vault All parameters must be defined in the registry under
    # the Parameter Vault folder before they are available in the experiment.
    # All parameters will be available in the main experiment function via a
    # variable named self.p.parameter_folder.parameter

    # The format is (parameter folder, parameter)
    
    
    #QsimExampleExperiment4 has 9 parameters: Piezo_Connection_Bus, Piezo_Connection_Port, Piezo_Channel,
    #Oscilloscope_Name, Oscilloscope_Channel, PWM_Length,PWM_Frequency,PWM_Voltage, and Poll_Interval.
    #Piezo_Connection_Bus,Piezo_Connection_Port, and Oscilloscope_Name are string parameters.
    #Piezo_Channel and Oscilloscope_Channel are integer parameters. PWM_Length, PWM_Frequency,
    #PWM_Voltage, and Poll_Interval are float parameters. The Piezo_Connection_Bus and Piezo_Connection_Port
    #must match the computer and port the Piezo Box is plugged into.
    #Oscilloscope_Name must match the name of the plugged-in device on the Oscilloscope Server
    #(which is based off of which computer’s bus it’s plugged into and the resource name of the device).
    #Piezo_Channel and Oscilloscope_Channel must match the output channel and input channel the
    #cable is plugged into on these devices respectively.
    
    exp_parameters = [
        # piezo parameters
        ('Qsim Example Experiment 4 Parameters', 'Piezo_Connection_Bus'),
        ('Qsim Example Experiment 4 Parameters', 'Piezo_Connection_Port'),
        ('Qsim Example Experiment 4 Parameters', 'Piezo_Channel'),

        # oscilloscope parameters
        ('Qsim Example Experiment 4 Parameters', 'Oscilloscope_Name'),
        ('Qsim Example Experiment 4 Parameters', 'Oscilloscope_Channel'),

        # output parameters
        ('Qsim Example Experiment 4 Parameters', 'PWM_Length'),
        ('Qsim Example Experiment 4 Parameters', 'PWM_Frequency'),
        ('Qsim Example Experiment 4 Parameters', 'PWM_Voltage'),
        
        # readout parameters
        ('Qsim Example Experiment 4 Parameters', 'Poll_Interval')
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
        #The experiment begins by making a request to the Piezo Server to select the plugged-in Piezo Box.
        self.piezo_server.device_select(self.p.example_parameters.Piezo_Connection_Bus,self.p.example_parameters.Piezo_Connection_Port)
        self.piezo_server.toggle(self.p.example_parameters.Piezo_Channel, 1)
        
        # set up oscilloscope
        self.os_server = cxn.oscilloscope_server
        self.os_server.select_device(self.p.example_parameters.Oscilloscope_Name)
        self.os_server.channel_toggle(self.p.example_parameters.Oscilloscope_Channel, True)

        # set up channel display
        self.os_server.autoscale()

        # a request is made to display the relevant input channel’s
        # displayed waveform’s mean and frequency in the first and second “measurement display slots”.
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
        
        #creates a list of x-values from 0 to the PWM_Length value, split evenly so that the difference
        #between a point and the point two spots after it in the list covers (1 / PWM_Frequency) seconds,
        #representing the period
        x_max = params.PWM_Length
        x_points = int(params.PWM_Length * params.PWM_Frequency * 2)
        x_values = np.linspace(0, x_max, x_points + 1)
        
        # get oscilloscope poll period
        poll_value = int(params.Poll_Interval * params.PWM_Frequency * 2)
        # set up variables for PWM
        output_high = False
        self.piezo_server.voltage(1, 0)

        
        for i, x_point in enumerate(x_values):

            # The following updates the Script Scanner progress with a number between 0 and 1
            # with 0 being 0% and 1 being 100% completed. If the user has pressed stop on script scanner the for loop
            # is broken. This functionality is optional but extremely helpful. This imitates an electrical signal with a square waveform of frequency PWM_frequency and amplitude PWM_Voltage, raised by PWM_Voltage/2 volts throughout.
            should_break = self.update_progress(i/float(len(x_values)))
            if should_break:
                break

            #Every time half the period has passed, the experiment makes a request
            #to the Piezo Server to set the constant output voltage of the channel to
            #whichever value it does not currently have: 0 or the value PWM_Voltage (in volts).
            

            if output_high:
                self.piezo_server.voltage(1,0)
            else:
                self.piezo_server.voltage(1,params.PWM_Voltage)
            output_high = not output_high


            # Simultaneously, every time the Poll_Interval has passed, a request is made to the
            # Oscilloscope Server to get the mean and frequency of the waveform the oscilloscope
            # is currently displaying on its screen, and return these values. Each time, these
            # values at that time are added to the data set. Once PWM_Length in seconds has passed,
            #the experiment has ended.
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
    scanner = cxn.script_scanner                             # connects to script scanner server
    exprt = QsimExampleExperiment4(cxn=cxn)                     # instantiates the experiment
    ident = scanner.register_external_launch(exprt.name)    # registers an experiment with Script Scanner
    exprt.execute(ident)                                    # executes the experiment
