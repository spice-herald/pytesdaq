import numpy as np
import time
import pytesdaq.config.settings as settings
import pytesdaq.instruments.control as instrument
from pytesdaq.utils import connections


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
          self._data_base_path = '/data/sequencer'
          self._dummy_mode = False
          self._facility = 1
          

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
               elif key == 'data_base_path':
                    self._data_base_path = config_dict[key]
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
          items_dict = connections.get_items(self._connection_table)
          
          
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
          
          
