import numpy as np
import time
from datetime import datetime
import os
import shutil
import stat


import pytesdaq.config.settings as settings
import pytesdaq.instruments.control as instrument
from pytesdaq.utils import connection_utils
from pytesdaq.utils import arg_utils
from pytesdaq.daq import daq

class Sequencer:
     """
     TBD
     """

     def __init__(self, measurement_name,
                  measurement_list=None,
                  comment='No comment',
                  detector_channels=None,
                  tc_channels=None,
                  sequencer_file=None, setup_file=None,
                  sequencer_pickle_file=None,
                  dummy_mode=False,
                  verbose=True):
          


          # measurement name and list
          self._measurement_name = measurement_name
          self._measurement_list = measurement_list
          if self._measurement_list is None:
               self._measurement_list = [self._measurement_name]
          self._measurement_config = None
               
          # initialize some parameters
          # can be overwritten by config and class property
          self._verbose = verbose
          self._comment = comment
          self._online_analysis = False
          self._enable_redis = False
          self._daq_driver = 'polaris'
          self._dummy_mode = dummy_mode
          self._facility = 1
          self._save_raw_data = True
          self._group_name = 'None'
          self._fridge_run = None
          

          # default data path
          self._base_raw_data_path = './'
          self._raw_data_path = './'
          self._base_automation_data_path = './'
          self._automation_data_path = './'

          # automation data
          self._automation_data = dict()
          self._automation_data['info'] = None
          self._automation_data['data'] = None

          
          # setup files
          self._setup_file = setup_file
          
          self._sequencer_pickle_file = sequencer_pickle_file
          self._sequencer_file = sequencer_file


          # channels (can also be set in sequencer file)
          self._detector_channels = detector_channels
          self._tc_channels = tc_channels
          self._is_tc_channel_number = False
          

          # channel tables
          self._detector_connection_table = None
          self._tc_connection_table = None
          
          
                    
          # Instantiate config
          try:
               self._config = settings.Config(sequencer_file=self._sequencer_file,
                                              setup_file=self._setup_file)
          except Exception as e:
               print('ERROR reading configuration files!')
               print(str(e))
               exit(1)

          # Read measurement(s)  configuration
          self._read_measurement_config()


          
          # redis (can be enable in sequncer.ini file)
          if self._enable_redis:
               self._redis_db = redis.RedisCore()
               self._redis_db.connect()
               
          
          # Initialize daq / instrument
          self._daq = None
          self._instrument = None
               
               


     @property
     def verbose(self):
          return self._verbose
          
     @verbose.setter
     def verbose(self,value):
          self._verbose=value
  
     @property
     def dummy_mode(self):
          return self._dummy_mode
        
     @dummy_mode.setter
     def dummy_mode(self,value):
          self._dummy_mode=value




           
     def _read_measurement_config(self):
          """
          Read sequencer configuration
          """
          
          self._measurement_config = self._config.get_sequencer_setup(self._measurement_name,
                                                                      self._measurement_list)
        
          # save some parameters from user settings
          for key,item in self._measurement_config[self._measurement_name].items():
               if key == 'online':
                    self._online_analysis = item
               elif key == 'daq_driver':
                    self._daq_driver = item
               elif key == 'enable_redis':
                    self._enable_redis = item
               elif key == 'save_raw_data':
                    self._save_raw_data = item
         
          # facility
          self._facility = self._config.get_facility_num()

          # data path
          data_path = self._config.get_data_path()
          
          # append run#
          self._fridge_run = self._config.get_fridge_run()
          fridge_run_name = 'run' + str(self._fridge_run)
          if data_path.find(fridge_run_name)==-1:
               data_path += '/' + fridge_run_name
          self._base_raw_data_path =  data_path + '/raw'
          self._base_automation_data_path  =  data_path + '/automation'
          arg_utils.make_directories([data_path, self._base_raw_data_path,
                                      self._base_automation_data_path])

          
          # channels
          for measurement in  self._measurement_list:
               # detector channels
               if (self._detector_channels is None and
                   'detector_channels' in self._measurement_config[measurement]):
                    channels = self._measurement_config[measurement]['detector_channels']
                    self._detector_channels = channels
                    
               # Tc channels
               if (self._tc_channels is None and
                   'tc_channels' in self._measurement_config[measurement]):
                    channels = self._measurement_config[measurement]['tc_channels']
                    self._tc_channels = channels

               break


          # channel table
          if self._detector_channels is not None:
               self._detector_connection_table = self._config.get_adc_connections()

                       

          # check channels
          self._check_detector_channels()

          # done if no detector channels
          if self._detector_channels is None:
               return

          # ADC parameter for measurement with detector channels
          adc_dict = dict()
          for channel in  self._detector_channels:
               adc_id, adc_chan = connection_utils.get_adc_channel_info(
                    self._detector_connection_table,
                    detector_channel=channel
               )
               if adc_id not in adc_dict:
                    adc_dict[adc_id] = self._config.get_adc_setup(adc_id).copy()
                    adc_dict[adc_id]['channel_list'] = list()

               adc_dict[adc_id]['channel_list'].append(int(adc_chan))
                    

          # check required parameter
          # add or replace parameter from measurement_config
          required_parameters = ['sample_rate','voltage_min','voltage_max']
          required_parameters_didv = ['signal_gen_frequency', 'signal_gen_shape']
          if self._config.get_signal_generator()=='magnicon':
               required_parameters_didv.append('signal_gen_current')
          else:
               required_parameters_didv.append('signal_gen_voltage')
          
        

          # loop measurements
          for measurement in  self._measurement_list:
               
               # measurement config
               config_dict = self._measurement_config[measurement]

               
               # dIdV flag
               is_didv_used = (measurement != 'iv'
                               and  measurement != 'noise')

               # check dIdV parameters
               if is_didv_used:
                    required_parameters.extend(required_parameters_didv)

               if self._detector_channels is not None:
                    for item in required_parameters:
                         if item not in config_dict:
                              raise ValueError(measurement
                                               + ' measurement require '
                                               + str(item)
                                               + '! Please check configuration')
                         
               # ADC parameters
               for adc_id in adc_dict:
                    for item,value in adc_dict[adc_id].items():
                         if item in config_dict:
                              value = config_dict[item]
                              adc_dict[adc_id][item] = value

                    # calculate number of samples (dIdV fit)
                    nb_samples = 0
                    sample_rate = int(config_dict['sample_rate'])
                    if (is_didv_used and 'nb_cycles' in config_dict):
                         signal_gen_freq = float(config_dict['signal_gen_frequency'])
                         nb_samples= round(
                              float(config_dict['nb_cycles'])*sample_rate/signal_gen_freq
                         )
                    elif 'trace_length_ms' in config_dict:
                         nb_samples= round(float(config_dict['trace_length_ms'])*sample_rate/1000)
                    elif 'trace_length_adc' in config_dict:
                         nb_samples = int(config_dict['trace_length_adc'])
                    else:
                         raise ValueError('Nb of cycles or trace length required for "'
                                          + measurement + '" measurement!')
                    

                    # trigger
                    trigger_type = 1
                    if is_didv_used:
                         trigger_type = 2
               
                    # add parameters
                    for adc_id in adc_dict:
                         adc_dict[adc_id]['nb_samples'] = int(nb_samples)
                         adc_dict[adc_id]['trigger_type'] =  trigger_type
                         if trigger_type==2:
                              trigger_channel = '/Dev1/pfi0'
                              if ('device_name' in adc_dict[adc_id] and 
                                  'trigger_channel' in  adc_dict[adc_id]):
                                   trigger_channel = '/' + adc_dict[adc_id]['device_name'] + '/' 
                                   trigger_channel += adc_dict[adc_id]['trigger_channel']
                              adc_dict[adc_id]['trigger_channel'] = trigger_channel

               self._measurement_config[measurement]['adc_setup'] = adc_dict

                         
                         

     def _read_pickle(self):
          print('Reading pickle -> Not implemented...')



     def _instantiate_drivers(self):
          """
          Instantiate drivers
          """
          
          # DAQ (if detector readout)
          if self._detector_channels is not None:
               self._daq = daq.DAQ(driver_name=self._daq_driver,
                                   verbose=self._verbose,
                                   setup_file=self._setup_file)
               
        
          # Instrumment controller
          self._instrument = instrument.Control(setup_file=self._setup_file,
                                                dummy_mode=self._dummy_mode)
               
          if self._tc_channels is not None:
               self._tc_connection_table = self._instrument.get_temperature_controllers_table()
               self._check_tc_channels()
          

          
     def _check_detector_channels(self):
          """
          Check detector (SQUID readout) channels
          """
          
          # check detector channels
          if self._detector_channels is not None:
               # connection info
               items_dict = connection_utils.get_items(self._detector_connection_table)
               
               for channel in self._detector_channels:
                    if channel not in items_dict['detector_channel']:
                         raise ValueError('Channel ' + channel + ' unrecognized. '
                                          + 'Please check input or connections map in setup.ini)')


                    

     def _check_tc_channels(self):
          """
          Check Tc channels
          """
             
          if self._tc_channels is not None:

               # check if global number or name
               self._is_channel_number = all([x.isdigit() for x in self._tc_channels])
               item_name = 'channel_name'
               if self._is_channel_number:
                    self._tc_channels = [int(x) for x in self._tc_channels]
                    item_name = 'global_channel_number'

               # loop channel and check if available
               for chan in self._tc_channels:
                    query_string = item_name + ' == @chan'
                    channel_check = self._tc_connection_table.query(query_string)[item_name].values
                    if len(channel_check)>1:
                         raise ValueError('ERROR: Multiple temperature controller channel found for '
                                          + 'tc channel = ' + str(chan) + '!')
                    elif len(channel_check)<1:
                         raise ValueError('ERROR: No temperature controller channel found for '
                                          + 'tc channel = "' + str(chan) + '"!')

               
       
     def _create_measurement_directories(self, base_name=None):
          """
          Create sequencer directory
          """
                        
          # date/time
          now = datetime.now()
          series_day = now.strftime('%Y') +  now.strftime('%m') + now.strftime('%d') 
          series_time = now.strftime('%H') + now.strftime('%M') +  now.strftime('%S')
          series = 'I' + str(self._facility) + '_D' + series_day + '_T' + series_time
          if base_name is None:
               base_name = 'measurement'
          self._group_name = base_name + '_' + series
                        
          # raw data
          self._raw_data_path = self._base_raw_data_path  + '/' + self._group_name 
          if self._save_raw_data and self._detector_channels is not None:
               arg_utils.make_directories(self._raw_data_path)
                             
          # tc data
          self._automation_data_path = self._base_automation_data_path + '/' + self._group_name 
          if self._tc_channels is not None:
               arg_utils.make_directories(self._automation_data_path + '/' + self._group_name )
            

          # update automation data
          if self._automation_data['info'] is None:
               self._automation_data['info'] = dict()

          self._automation_data['info']['date'] = now
          self._automation_data['info']['series'] = series
          self._automation_data['info']['measurements'] = 'Tc'
          
        
