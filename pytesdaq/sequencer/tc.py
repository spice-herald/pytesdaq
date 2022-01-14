import numpy as np
import time
from math import nan

from pytesdaq.daq import daq
import pytesdaq.config.settings as settings
import pytesdaq.instruments.control as instrument
from pytesdaq.sequencer.sequencer import Sequencer
from pytesdaq.utils import connection_utils


class Tc(Sequencer):
    
    def __init__(self, tc_channels=None, detector_channels=None,
                 sequencer_file=None, setup_file=None,
                 dummy_mode=False, verbose=True):
        
        super().__init__('tc',
                         detector_channels=detector_channels,
                         tc_channels=tc_channels,
                         sequencer_file=sequencer_file,
                         setup_file=setup_file,
                         dummy_mode=dummy_mode,
                         verbose=verbose)
        
        # configuration measurement
        self._configure()
        
        



    def run(self):

        """ 
        Run Tc automation
        """

        # instantiate driver
        self._instantiate_drivers()


        # configuration data
        config_dict = self._measurement_config[self._measurement_name]
        
        # thermometers, heater and control channel (PID)
        control_thermometer_name = config_dict['control_thermometer_name']
        heater_name = config_dict['heater_name']
        thermometer_names = config_dict['thermometer_names']

        
        # initialize data
        self._automation_data['data'] = dict()
        self._automation_data['data']['temperature'] = dict()
        self._automation_data['data']['resistance_tempcontroller'] = dict()
        self._automation_data['data']['resistance_squid'] = dict()
                     
        if self._tc_channels:
            for chan in self._tc_channels:
                self._automation_data['data']['resistance_tempcontroller'][chan] = list()
     
        if self._detector_channels:
            for chan in self._detector_channels:
                self._automation_data['data']['resistance_squid'][chan] = list()

        for thermometer in thermometer_names:
            self._automation_data['data']['temperature'][thermometer] = list()


            
        # loop temperature and measure resistance
        if self._verbose:
            print('INFO: Starting ' + self._measurement_name + ' measurement!')
        
        for temperature in config_dict['temperature_vect']:

            # set temperature
            if self._verbose:
                print('INFO: Setting temperature to ' + str(temperature) + '!')

            self._instrument.set_temperature(temperature,
                                             channel_name=control_thermometer_name,
                                             heater_name=heater_name,
                                             wait_temperature_reached=True)


            # get temperature
            for thermometer in thermometer_names:
                temperature = self._instrument.get_temperature(
                    channel_name=thermometer
                )

                # append data
                self._automation_data['data']['temperature'][thermometer].append(
                    float(temperature)
                )
                
                
            

            # measure resistance  (SQUID readout)
            if self._detector_channels:
                pass

            # measure resistance  (Temperature controller)
            if self._tc_channels:
                for chan in self._tc_channels:
                    resistance = nan
                    if self._is_tc_channel_number:
                        resistance = self._instrument.get_resistance(
                            global_channel_number=chan
                        )
                    else:
                        resistance = self._instrument.get_resistance(
                            channel_name=chan
                        )

                    # append data
                    self._automation_data['data']['resistance_tempcontroller'].append(
                        float(resistance)
                    )
        



        # Measurement done save data 
        

    def _configure(self):
        """
        Automation configuration
        """

        config_dict = self._measurement_config[self._measurement_name]
             
        # Build temperature vector
        if config_dict['use_temperature_vect']:
            temperature_vect = [float(temp) for temp in config_dict['temperature_vect']]
        else:

            # build using min/max/step

            # check required parameter
            required_parameter = ['temperature_min','temperature_max',
                                  'temperature_step']

            for key in required_parameter:
                if key not in config_dict:
                    raise ValueError('Tc automation require ' + str(key)
                                     + ' if "use_temperature_vect" = false! '
                                     + 'Please check configuration')
                
            # build
            temperature_vect = np.arange(float(config_dict['temperature_min']),
                                         float(config_dict['temperature_max']),
                                         float(config_dict['temperature_step']))

            temperature_vect = np.append(temperature_vect,
                                         float(config_dict['temperature_max']))
        
            
        # check unique values
        temperature_vect = np.unique(np.asarray(temperature_vect))


        # add to configuration
        self._measurement_config[self._measurement_name]['temperature_vect'] = temperature_vect
       
        # create automation directory
        self._create_measurement_directories('tc')
        
    
        
