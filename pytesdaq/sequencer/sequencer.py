import numpy as np
import time
import pytesdaq.config.settings as settings
import pytesdaq.instruments.control as instrument
from pytesdaq.utils import connection_utils


class Sequencer:
     """
     TBD
     """

     def __init__(self,channel_list= list(),sequencer_file='',setup_file='',
                  pickle_file=''):
          


          # initialize some parameters
          # can be overwritten by config and class property
          self._verbose = True
          self._is_online = False
          self._enable_redis = False
          self._daq_driver = 'polaris'
          self._dummy_mode = False
          self._facility = 1
          self._data_path = '/data/raw'
          

          # read configuration data
          self._config= []
          self._sequencer_config = dict()
          self._connection_table = dict()
          self._read_config(sequencer_file,setup_file)
          

          # read pickle file
          #self._read_pickle

          
          # check channels -> use "tes_channel" only
          channel_list = self._check_channels(channel_list)
          self._selected_channel_list = channel_list

          # redis (can be enable in sequncer.ini file)
          if self._enable_redis:
               self._redis_db = redis.RedisCore()
               self._redis_db.connect()
               
          
          # daq / instrument
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



           
     def _read_config(self,sequencer_file,setup_file):
          
          # configuration dictionary 
          try:
               self._config = settings.Config(sequencer_file=sequencer_file,
                                              setup_file=setup_file)
          except Exception as e:
               print('ERROR reading configuration files!')
               print(str(e))
               exit(1)
               

          config_dict = self._config.get_sequencer_setup()

          for key in config_dict:

               if key == 'verbose':
                    self._verbose = config_dict[key]
               elif key == 'online':
                    self._is_online = config_dict[key]
               elif key == 'dummy_mode':
                    self._dummy_mode = config_dict[key]
               elif key == 'daq_driver':
                    self._daq_driver = config_dict[key]
               elif key == 'data_path':
                    self._data_path = str(config_dict[key])
               elif key == 'enable_redis':
                    self._enable_redis = config_dict[key]
               else:
                    self._sequencer_config[key] = config_dict[key]
          
        
          # connection table
          self._connection_table= self._config.get_adc_connections()
               
          # facility
          self._facility = self._config.get_facility_num()
       


     def _read_pickle(self):
          print('Reading pickle -> Not implemented...')
          
     def _check_channels(self,channel_list):

          if not channel_list: 
               raise ValueError('No channel has been selected!')

          selected_channels = list()
          items_dict = connection_utils.get_items(self._connection_table)
          
          
          # loop channels
          for channel in channel_list:
               if channel in items_dict['tes_channel']:
                    selected_channels.append(channel)
               elif channel in items_dict['detector_channel']:
                    ind = items_dict['detector_channel'].index(channel)
                    selected_channels.append(items_dict['tes_channel'][ind])
               else:
                    raise ValueError('Channel ' + channel + 
                                     ' unrecognized. Please check input or connections map in setup.ini)')
                         
               
          return selected_channels
          
          

     def _get_adc_setup(self, config_dict, measurement_name):
          
          
          adc_dict = dict()

          # didv, rp, and rn have same adc setup
          is_didv = (measurement_name == 'rp' or measurement_name == 'rn' or measurement_name == 'didv')
          
          # fill channel list
          for channel in  self._selected_channel_list:
               adc_id, adc_chan = connection_utils.get_adc_channel_info(self._connection_table,
                                                                        tes_channel=channel)
               if adc_id not in adc_dict:
                    adc_dict[adc_id] = self._config.get_adc_setup(adc_id).copy()
                    adc_dict[adc_id]['channel_list'] = list()
               adc_dict[adc_id]['channel_list'].append(int(adc_chan))
                    
          
                
          # check required parameter
          required_parameter_adc = ['sample_rate','voltage_min','voltage_max']
          for item in required_parameter_adc:
               if item not in config_dict:
                    raise ValueError(measurement_name + ' measurement require ' + str(item) +
                                     ' ! Please check configuration')
        
          # calculate nb_samples
          nb_samples = 0
          sample_rate = int(config_dict['sample_rate'])
          if (is_didv and 'nb_cycles' in config_dict):
               signal_gen_freq = float(config_dict['signal_gen_frequency'])
               nb_samples= round(float(config_dict['nb_cycles'])*sample_rate/signal_gen_freq)
          elif 'trace_length_ms' in config_dict:
               nb_samples= round(float(config_dict['trace_length_ms'])*sample_rate/1000)
          elif 'trace_length_adc' in config_dict:
               nb_samples = int(config_dict['trace_length_adc'])
          else:
               raise ValueError('Nb of cycles or trace length required for TES measurement!')
                    

          # trigger
          trigger_type = 1
          if is_didv:
               trigger_type = 2
               
          
         
          # overwrite dictionary with setup from sequencer.ini
          for adc_id in adc_dict:
               adc_dict[adc_id]['nb_samples'] = int(nb_samples)
               adc_dict[adc_id]['sample_rate'] = int(config_dict['sample_rate'])
               adc_dict[adc_id]['voltage_min'] = float(config_dict['voltage_min'])
               adc_dict[adc_id]['voltage_max'] = float(config_dict['voltage_max'])
               adc_dict[adc_id]['trigger_type'] =  trigger_type
               if trigger_type==2:
                    trigger_channel = '/Dev1/pfi0'
                    if ('device_name' in adc_dict[adc_id] and 
                        'trigger_channel' in  adc_dict[adc_id]):
                         trigger_channel = '/' + adc_dict[adc_id]['device_name'] + '/' 
                         trigger_channel += adc_dict[adc_id]['trigger_channel']
                    adc_dict[adc_id]['trigger_channel'] = trigger_channel
         
          return adc_dict
