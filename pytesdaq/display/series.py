import time
import os
import numpy as np
from glob import glob
from pprint import pprint
from pathlib import Path
import json

import pytesdaq.io.hdf5 as h5io
from pytesdaq.utils import  arg_utils

class SeriesGroup:
    def __init__(self, group_name, group_path):

        self._group_name = group_name
        self._group_path = group_path


        # initialize group info
        self._is_data_filled = False
        self._nb_series = 0
        self._nb_events = 0
        self._group_comment = None
        self._devices = list()
        self._facility = None
        self._duration = 0
        self._data_types = list()
        self._data_purposes = list()
        self._fridge_run = None
        self._timestamp = None
        self._series_info = dict()

        
    @property
    def group_name(self):
        return self._group_name
   
    @property
    def nb_events(self):
        return self._nb_events

    @property
    def nb_series(self):
        return self._nb_series

    @property
    def facility(self):
        return self._facility

    @property
    def fridge_run(self):
        return self._fridge_run

    @property
    def duration(self):
        return self._duration

    @property
    def group_comment(self):
        return self._group_comment

    @property
    def devices(self):
        return self._devices

    


    def get_series_list(self):
        """
        Get list of series
        
        Return:
        -------
        series_list: list of str
        """

        if not self._series_info:
            self.fill_info_from_disk()

            
        return list(self._series_info.keys())
    
    def get_group_info(self, include_series_info=False):
        """
        Get group infog
        
        Return:
        -------
        
        info: dictionary

        """

        # check if information extracted from file
        if not self._is_data_filled:
            self.fill_info_from_disk()

        
        group_info_dict = dict()
        group_info_dict['group_name'] = self._group_name
        group_info_dict['facility'] = self._facility
        group_info_dict['fridge_run'] = self._fridge_run
        group_info_dict['nb_series'] = self._nb_series
        group_info_dict['nb events'] = self._nb_events
        group_info_dict['duration'] = self._duration

        devices = ', '.join(self._devices)
        group_info_dict['devices'] =  devices
        data_types = ', '.join(str(item) for item in self._data_types)
        group_info_dict['data_types'] =  data_types
        data_purposes = ', '.join(self._data_purposes)
        group_info_dict['data_purposes'] =  data_purposes
        comment = 'None'
        if self._group_comment is not None:
            comment = self._group_comment
            group_info_dict['group_comment'] = comment

        group_info_dict['timestamp'] = self._timestamp
            
        series_info_dict = dict()
        if include_series_info:
            for series in self._series_info.values():
                 series_info_dict[series.series_name] = series.get_general_info()
                 series_info_dict[series.series_name]['ADC_config'] = series.get_adc_info()
                 series_info_dict[series.series_name]['detector_config'] = series.get_detector_info()
                 series_info_dict[series.series_name]['connection_table'] = series.connection_table
            
        return group_info_dict, series_info_dict
    

    def print_info(self, include_series_info=False):
        """
        Display group info
        """

        
        # get dictionaries
        group_info, series_info = self.get_group_info(
            include_series_info=include_series_info)

        # display
        print(' ')
        for param, val in group_info.items():
            print(param + ': ' + str(val))
            
        if include_series_info and series_info:
            for series_name, series_param in series_info.items():
                for param_name, param_val in series_param.items():
                    if not isinstance(param_val, dict):
                        series_info[series_name][param_name] = str(
                            series_info[series_name][param_name]
                        )
            series_json = json.dumps(series_info, indent=5)
            print(series_json)
            
        print(' ')


        
    def fill_info_from_disk(self):
        """
        Get series info from files

        Arguments:
        ---------
        """

        # get list of file
        full_path = os.path.join(self._group_path, self._group_name)
        file_list = glob(full_path + '/*.hdf5')
        file_list.sort()

        
        if not file_list:
            print('WARNING: No raw data found in ' + full_path + '!')
            return

        
        # h5 reader 
        hdf5 = h5io.H5Reader()
        
        # loop files
        for file_path in file_list:
            
            # read metadata
            info =  hdf5.get_metadata(file_name=file_path,
                                      include_dataset_metadata=True)

           
            # series name
            series_num = info['series_num']
            series_name = h5io.extract_series_name(series_num)
            series_obj = None

            # series object
            if series_name not in self._series_info:
                series_obj = Series(series_name=series_name, series_num=series_num)
                self._series_info[series_name] = series_obj
            
            self._series_info[series_name].add_dump_from_metadata(info)     
        
        #  group info
        self._nb_series = len(self._series_info)
        for series in self._series_info.values():
            self._nb_events += series.nb_events
            self._duration += series.duration
            for device in series.devices:
                if device not in self._devices:
                    self._devices.append(device)
            if self._facility is None and series.facility is not None:
                self._facility = series.facility
            if self._fridge_run is None and series.fridge_run is not None:
                self._fridge_run = series.fridge_run
            if self._group_comment is None and series.group_comment is not None:
                self._group_comment = series.group_comment
            if series.data_type is not None and series.data_type not in self._data_types:
                self._data_types.append(series.data_type)
            if series.data_purpose is not None and series.data_purpose not in self._data_purposes:
                self._data_purposes.append(series.data_purpose)
            if self._timestamp is None or series.first_event_timestamp<self._timestamp:
                self._timestamp = series.first_event_timestamp
           

                
        self._duration = round(self._duration*100)/100
        self._is_data_filled = True


class Series:
    
    def __init__(self,
                 series_name=None,
                 series_num=None):
        
        self._series_name = series_name
        self._series_num = series_num
        if series_num is None and series_name is not None:
            self._series_num = h5io.extract_series_num(series_name)
        if series_name is None and series_num is not None:
            self._series_name = h5io.extract_series_name(series_num)
      
        
        # initialize overall series info
        self._group_name = None
        self._group_comment = None
        self._nb_dumps = 0
        self._nb_events = 0
        self._nb_dumps = 0
        self._facility = None
        self._daq_version = None
        self._format_version = None
        self._data_type = None
        self._data_purpose = None
        self._comment = None
        self._prefix = None
        self._devices = list()
        self._fridge_run = None
        self._first_event_timestamp = None
        self._last_event_timestamp = None
        self._duration  = 0
        
        # Initialize dump information
        self._dump_num_list = list()
        self._dump_info = dict()

        # Initialize adc and detector information
        self._adc_info = None
        self._detector_info = None
                
        # pandas chanel map
        self._connection_table = None
    
    @property
    def series_name(self):
        return self._series_name

    @property
    def series_num(self):
        return self._series_num

    @property
    def group_name(self):
        return self._group_name
    
    @property
    def group_comment(self):
        return self._group_comment
    
    @property
    def nb_dumps(self):
        return self._nb_dumps
    
        
    @property
    def nb_events(self):
        return self._nb_events

    @property
    def nb_dumps(self):
        return self._nb_dumps
    
    @property
    def facility(self):
        return self._facility


    @property
    def fridge_run(self):
        return self._fridge_run
        
    @property
    def data_type(self):
        return self._data_type
    
    @property
    def data_purpose(self):
        return self._data_purpose
    
    @property
    def prefix(self):
        return self._prefix
    
    @property
    def devices(self):
        return self._devices
    
    @property
    def comment(self):
        return self._comment

    @property
    def duration(self):
        return self._duration

    @property
    def first_event_timestamp(self):
        return self._first_event_timestamp
    @property
    def last_event_timestamp(self):
        return self._last_event_timestamp

    @property
    def connection_table(self):
        return self._connection_table

    def get_general_info(self):
        """
        Get Series info
        """
        info_dict = dict()
        info_dict['group_name'] = str(self._group_name)
        info_dict['group_comment'] = str(self._group_comment)
        info_dict['facility'] = self._facility
        info_dict['fridge_run'] = self._fridge_run
        info_dict['devices'] = ', '.join(self._devices)
        info_dict['comment'] = str(self._comment)
        info_dict['nb_dumps'] = self._nb_dumps
        info_dict['nb_events'] = self._nb_events
        info_dict['data_type'] = self._data_type
        info_dict['data_purpose'] = self._data_purpose
        info_dict['duration'] = self._duration
        info_dict['timestamp'] = self._first_event_timestamp
        return info_dict

        
    def get_adc_info(self, json_format=False):
        """
        Get ADC info
        """

        if self._adc_info is not None:
            output = self._adc_info
            if json_format:
                output = json.dumps(self._adc_info, indent=4)
            return output
        else:
            return None


    def get_detector_info(self, json_format=False):
        """
        Get Detector info
        """

        if self._detector_info is not None:
            output = self._detector_info
            if json_format:
                output = json.dumps(self._detector_info, indent=4)
            return output
        else:
            return None

        
        
    def add_dump_from_metadata(self, metadata):
        """
        Add dump information
        """

        # check dump number exist
        if 'dump_num' not in metadata:
            raise ValueError('ERROR:  metadata format not recognized!')

        # add dump
        dump_num = int(metadata['dump_num'])
        if dump_num in self._dump_num_list:
            print('INFO: dump already exist!')
            return
        self._dump_num_list.append(dump_num)
        self._dump_info[dump_num] = dict()
        self._dump_info[dump_num]['timestamp'] = metadata['timestamp']
    
               
        # data reader
        hdf5 = h5io.H5Reader()

           
        # add series information
        if self._series_num is None:
            self._series_num = metadata['series_num']
            self._series_name = h5io.extract_series_name(series_num)
        
        if self._facility is None and 'facility' in metadata:
            self._facility = metadata['facility']

        if self._fridge_run is None and 'fridge_run' in metadata:
            self._fridge_run = metadata['fridge_run']

        if self._group_name is None and 'group_name' in metadata:
            self._group_name = metadata['group_name']
           
        if self._group_comment is None and 'group_comment' in metadata:
            self._group_comment = metadata['group_comment']
            if self._group_comment[0]=='"':
                self._group_comment = self._group_comment[1:-1]
                       
        if self._daq_version is None and 'daq_version' in metadata:
            self._daq_version = metadata['daq_version']

        if self._format_version is None and 'format_version' in metadata:
            self._format_version = metadata['format_version']    

        if self._data_type is None and 'run_type' in metadata:
            self._data_type = metadata['run_type']

        if self._data_purpose is None and 'run_purpose' in metadata:
            self._data_purpose = str(metadata['run_purpose'])
        
            
        if self._prefix is None and 'prefix' in metadata:
            prefix = Path(metadata['prefix']).parts[-1]

        if self._comment is None and 'comment' in metadata:
            self._comment = metadata['comment']


        if self._connection_table is None:
            self._connection_table = hdf5.get_connection_table(metadata=metadata)
            
            
        # ADC/Detector info 
        for adc_id in metadata['adc_list']:

            adc_info = metadata['groups'][adc_id]
                                         
            # nb events in dump
            self._dump_info[dump_num]['nb_events'] = adc_info['nb_events']
                       
            # check if already filled (same all dumps)
            if self._adc_info is not None and self._detector_info is not None:
                break
            
            # connection dictionary and table
            connections = hdf5.get_connection_dict(adc_name=adc_id,
                                                   metadata=metadata)


            
            adc_map = dict()
            for ichan, chan in enumerate(connections['adc_chans']):
                adc_map[chan] = connections['detector_chans'][ichan]
                
            # save detector list
            for detector in connections['detector_chans']:
                if detector not in self._devices:
                    self._devices.append(detector)
                    
            # adc info
            if self._adc_info is None:
                self._adc_info = dict()
                for ichan, chan in enumerate(connections['adc_chans']):
                    self._adc_info[connections['detector_chans'][ichan]] = {
                        'ADC name':adc_id,
                        'ADC channel': str(chan),
                        'Wiring channel':  connections['tes_chans'][ichan],
                        'Controller channel': connections['controller_chans'][ichan],
                        'Nb samples': str(adc_info['nb_samples']),
                        'Sample rate':  str(adc_info['sample_rate']),
                        'Voltage min':  str(adc_info['voltage_range'][ichan][0]),
                        'Voltage max':  str(adc_info['voltage_range'][ichan][1])
                    }

            # detector info
            parameter_list = {'tes_bias':('TES bias [uA]',1e6), 'squid_bias':('SQUID bias [uA]', 1e6),
                              'lock_point_voltage': ('Lock point [mV]', 1e3),
                              'output_gain': ('Driver gain', None),
                              'close_loop_norm': ('Normalization', None),
                              'feedback_mode': ('Feedback mode', None),
                              'signal_gen_onoff': ('SG on/off', None),
                              'signal_gen_source': ('SG source', None),
                              'signal_gen_current': ('SG amplitude [uA]', 1e6),
                              'signal_gen_frequency': ('SG frequency [Hz]', None)
                              }
                    
            detconfig_group = 'detconfig' + adc_id[3:]
            if self._detector_info is None and detconfig_group in metadata['groups']:
                self._detector_info = dict()
                
                # convert to list if needed
                detconfig = metadata['groups'][detconfig_group]
                for key, val in detconfig.items():
                    if not isinstance(val, list):
                        detconfig[key] = [val]
                        
                # loop channels
                for ichan, chan in enumerate(detconfig['channel_list']):
                    channel_info = dict()
                    for key,param_info in parameter_list.items():
                        if key not in detconfig:
                            channel_info[param_info[0]] = 'N/A'
                        else:
                            val = detconfig[key][ichan]
                            if param_info[1] is not None:
                                val = float(val) * param_info[1]
                                val = round(val*100)/100
                            channel_info[param_info[0]] = str(val)
                            
                    self._detector_info[adc_map[chan]] = channel_info
                              

        # update overall nb events and dumps
        self._nb_events += self._dump_info[dump_num]['nb_events']
        self._nb_dumps = len(self._dump_num_list)

      
        # time stamp
        first_event_time = 0
        last_event_time  = 0
        for adc_id in metadata['adc_list']:
            if 'datasets' in metadata['groups'][adc_id]:
                if 'event_1' in metadata['groups'][adc_id]['datasets']:
                    first_event_time = metadata['groups'][adc_id]['datasets']['event_1']['event_time']
                last_event = 'event_' + str(self._dump_info[dump_num]['nb_events'])
                if last_event in metadata['groups'][adc_id]['datasets']:
                    last_event_time = metadata['groups'][adc_id]['datasets'][last_event]['event_time']
                    
        
        if (first_event_time>0 and
            (self._first_event_timestamp is None
             or first_event_time<self._first_event_timestamp)):
            self._first_event_timestamp = first_event_time

        if (last_event_time>0 and
            (self._last_event_timestamp is None
             or last_event_time>self._last_event_timestamp)):
            self._last_event_timestamp = last_event_time
            
                        
        # update duration
        self._duration = (self._last_event_timestamp-self._first_event_timestamp)/60
        self._duration = round(self._duration *100)/100
        
        

class Register:
    
    def __init__(self, raw_path, group_name=None, display_only=False):
        """
        TBD
        """

        self._raw_path = raw_path

        # group list
        self._group_list = None
        if group_name is not None:
            self._group_list = [group_name]
        else:
            self._group_list = self._get_group_list()
            
        # display only
        self._display_only = display_only
            


    def run(self):
        """
        TBD
        """

        if self._group_list is None:
            print('INFO: No group to register!')
            return
        
        # loop groups
        for group_name in self._group_list:

            # instantiate group and fill info
            group = SeriesGroup(group_name, self._raw_path)
            group.fill_info_from_disk()

            if self._display_only:
                group.print_info(True)
                continue
            else:
                group_info, series_info = group.get_group_info(True)
                print(group_info)
                print(series_info)
                # .... register/ update



        
        
    def _get_group_list(self):
        """
        Get list of group
        """
        
        group_list = glob(self._raw_path + '/*/')
        group_list.sort(key=lambda x: os.path.getmtime(x))

        return group_list

        
