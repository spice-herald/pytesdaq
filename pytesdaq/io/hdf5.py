import h5py
import re
import os
import numpy as np
import pandas as pd
from glob import glob
import stat
import matplotlib.pyplot as plt
import warnings
import copy

from pytesdaq.utils import connection_utils

__all__ = ['H5Reader', 'H5Writer',
           'extract_series_num', 'extract_series_name',
           'extract_dump_num']

def extract_series_num(series_name):
    """
    Extract series number from file name or series name
    Assume series name has the following. This function
    should only be used if "series_num" is not stored in raw 
    data.

    Naming convention:  Ix_Dyyyymmdd_Thhmmss
        
    Parameters
    ----------
    series_name : str
      name of the series with format (format Ix_Dyyyymmdd_Thhmmss)

    Return
    ------
    serie_num : np.uint64
      series number (format xyyyymmddhhmmss)
    """

    if not isinstance(series_name, str):
        raise ValueError('ERROR in extract_series_num: series name should be a string')

    # check if full path
    if series_name.find('/')!=-1:
        series_name = series_name.split('/')[-1]
 
    # split series name 
    series_split = series_name.split('_')

    # index facility (different if file or series name)
    index_facility = 0
    if series_split[1][0] == 'I':
        index_facility = 1

    # check format
    if (len(series_split)< 3  or
        series_split[index_facility][0]!= 'I' or
        series_split[index_facility+1][0]!= 'D' or
        series_split[index_facility+2][0]!= 'T'):
        raise ValueError('ERROR in extract_series_num: unknown series name format!')
    
    # extract series num
    series_num = series_split[index_facility][1:] + series_split[index_facility+1][1:]
    series_num += series_split[index_facility+2][1:]
    series_num = np.uint64(float(series_num))

    return series_num


def extract_series_name(series_num):
    """
    Extract series name from series number

    Format:
    Series name:  Ix_Dyyyymmdd_Thhmmss
    Series num: xyyyymmddhhmmss 
  
    Parameters:
    ----------
    series_num: int
     series number

    Return
    ------
    series_name : str

    """

    series_num_str = str(series_num)
    series_time = 'T' + series_num_str[-6:]
    series_day = 'D' + series_num_str[-14:-6]
    series_inst = 'I' + series_num_str[:-14]
    series_name = series_inst + '_' +  series_day + '_' + series_time

    return series_name
    
    
def extract_dump_num(file_name):
    """
    Extract dump number for file name. This function
    should only be used if "dump_num" is not stored in raw 
    data.

    File name format: series_name_Fxxxx.hdf5
        
    Return:

    dump_num: int 
    (return None if not dump number found)
    """

    # remove path
    if file_name.find('/')!=-1:
        file_name = file_name.split('/')[-1]


    # find  dump string
    dump_num = None
    pos = file_name.find('_F')
    if pos>0:
        dump_num = int(file_name[pos+2:pos+6])
          
    return dump_num




class H5Reader:
    """
    Class to read raw data hdf5 files taken by pytesdaq
    """
    
    
    def __init__(self, raise_errors=True, verbose=True):
        """
        Initialize H5Reader

        Parameters
        ----------
        raise_errors : boolean, optional
          if True raise ValueError (default)
          if False, display error and return empty containers

        verbose : boolean, optional
          if True, display messages (default)
        
        
        Return
        ------
        None

        """

        self._raise_errors = raise_errors
        self._verbose = verbose
        
        # file dictionary {file: list of event dict}
        self._file_dict = dict()
       
        # current file data
        self._current_file = None
        self._current_file_name = None
        self._current_file_metadata = None
        self._current_file_nb_events = 0
        self._current_file_event_counter = 0
        self._current_file_event_list = None
             
        # global trigger counter (same as "event"
        # when entire trace used)
        self._global_events_counter = 0
         
        # global file counter
        self._file_counter = 0

        
    def set_files(self, filepaths, series=None, event_list=None):
        """

        """
        # clear
        self.clear()
        self._file_dict = dict()
      
        # find files
        self._file_dict = self._get_file_dict(
            filepaths, series=series,
            event_list=event_list
        )
             
  
    def close(self):
        """
        Close current file and initialize 
        file name paramters

        Parameters
        ----------
        None

        Return
        ------
        None
        """
        
        self._close_file()


        
    def clear(self):
        """
        Close current file and initialize 
        file name parameters and counters

        Parameters
        ----------
        None

        Return
        ------
        None

        """

        # close current file
        self._close_file()

        # initialize 
        self._current_file = None
        self._current_file_name = None
        self._current_file_metadata = None
        self._current_file_nb_events = 0
        self._current_file_event_counter = 0
        self._current_file_event_list = None
        self._file_counter = 0
        self._global_events_counter = 0



    def rewind(self):
        """
        Rewind to beginning of file(s)
        reopen....

        Parameters
        ----------
        None

        Return
        ------
        None
        """
                
        # if multiple files -> close current file then reopen first file
        if len(self._file_dict)>1:
            self._close_file()
            file_list = list(self._file_dict.keys())
            self._open_file(file_list[0])
    
        # initialize counters
        self._file_counter = 0
        self._current_file_event_counter = 0
        self._global_events_counter = 0
     



    def read_next_event(self,
                        trace_length_msec=None,
                        trace_length_samples=None,
                        pretrigger_length_msec=None,
                        pretrigger_length_samples=None,
                        detector_chans=None,
                        adctovolt=False, adctoamp=False,
                        baselinesub=False, baselineinds=None,
                        include_metadata=False,
                        adc_name='adc1'):
        """
        Function to read next event and increment event
        number counter. Require first to set file list
        (see "set_files" function)

        Parameters
        ----------
        
        detector_chans : str or list, optional
          detector/channel name or list of detectors/channels
          if None, get all channels (default)

        adctovolt : bool, optional
          convert from ADC to volts
          default: False

        adctoamp : bool, optional
          convert from ADC to current amps
          default: False
        
              
        baselinesub: bool, optional
          if True, subtract pre-pulse baseline
          default: False

        baselineinds: tuple (int, int) or list [int, int]
          min/max index for  baseline calculation 
          default: (10, 0.8*pretrigger length))
          
        include_metadata : bool, optional
          return file/event/detector metadata
          default: False

        adc_name : str, optional
          name/ID of the adc
          default: "adc1"

        Return
        ------
        
        array : 2D numpy array
           traces for each channel [nb channel, nb samples]

        info : dict
           file/event/detector metadata (if "include_metadata" = True)
        """

        
        info = dict()
        array = np.array([])
        
        # check if files available
        file_list = list(self._file_dict.keys())
        if not file_list or len(file_list)==0:
            info['read_status'] = 1
            info['error_msg'] = 'No file available!'
            return array, info
          
        # open file if no file currently open
        if self._current_file is None:

            # double check we can open file
            if self._file_counter>=len(file_list):
                info['read_status'] = 1
                info['error_msg'] = 'No more files available'
                return array, info

            file_name = file_list[self._file_counter]
            event_list = self._file_dict[file_name]
            self._open_file(file_name, event_list=event_list)

            
        # Check if there are more events
        # if not, open new file
        if self._current_file_event_counter>=self._current_file_nb_events:

            # close 
            self._close_file()
            
            # check if there are more files
            if  self._file_counter>=len(file_list):
                info['read_status'] = 1
                info['error_msg'] = 'No more files available'
                return array, info
            else:
                file_name = file_list[self._file_counter]
                event_list = self._file_dict[file_name]
                self._open_file(file_name, event_list=event_list)
                       
        # check if file not yet open (shouldn't happen)
        if self._current_file is None:
            info['read_status'] = 1
            info['error_msg'] = 'Problem reading next event. File closed!'
            return array, info
         
        
        # get event index and trigger index (event_index start from 1)
        event_index = self._current_file_event_counter+1
        trigger_index = None
        if self._current_file_event_list is not None:
            event_dict = (
                self._current_file_event_list[self._current_file_event_counter]
            )
            
            event_index = int(event_dict['event_number']%100000)
            if 'trigger_index' in event_dict.keys():
                trigger_index = event_dict['trigger_index']
            
                     
        array, info = self._load_event(
            event_index,
            trigger_index=trigger_index,
            trace_length_msec=trace_length_msec,
            trace_length_samples=trace_length_samples,
            pretrigger_length_msec=pretrigger_length_msec,
            pretrigger_length_samples=pretrigger_length_samples,
            detector_chans=detector_chans,
            adctovolt=adctovolt, adctoamp=adctoamp,
            baselinesub=baselinesub,
            baselineinds=baselineinds,
            adc_name=adc_name)


        # increment to next event
        self._current_file_event_counter += 1
        
        
        # return
        if include_metadata:
            return array,info
        else:
            return array
        
              


    def read_single_event(self, event_index,
                          file_name=None,
                          trigger_index=None,
                          trace_length_msec=None,
                          trace_length_samples=None,
                          pretrigger_length_msec=None,
                          pretrigger_length_samples=None,
                          detector_chans=None,
                          adctovolt=False, adctoamp=False,
                          baselinesub=False, baselineinds=None,
                          include_metadata=False, adc_name='adc1'):
        """
        Read a single event from a file based 
        on index ("dataset" number)

        
        Parameters
        ----------
        event_index : int
          event (hdf5 "dataset")  number 
        
        file_name : str, optional
          name of the file
          if None: use current file
        

        detector_chans : str or list, optional
          detector/channel name or list of detectors/channels
          if None, get all channels (default)

        adctovolt : bool, optional
          convert from ADC to volts
          default: False

        adctoamp : bool, optional
          convert from ADC to current amps
          default: False
        
              
        baselinesub: bool, optional
          if True, subtract pre-pulse baseline
          default: False

        baselineinds: tuple (int, int) or list [int, int]
          min/max index for  baseline calculation 
          default: (10, 0.8*pretrigger length))
          
        include_metadata : bool, optional
          return file/event/detector metadata
          default: False

        adc_name : str, optional
          name/ID of the adc
          default: "adc1"

        Return
        ------
        
        array : 2D numpy array
           traces for each channel [nb channel, nb samples]

        info : dict
           file/event/detector metadata (if "include_metadata" = True)

        """

        # check if file needed
        if (not self._file_dict and file_name is None):
            raise ValueError(
                'ERROR: No file available. '
                + 'Use "file_name" argument!') 


        
        # current file dict
        current_file_dict = copy.deepcopy(self._file_dict)
        
        #  set file list (clear internal data)
        if file_name is not None:
            self.set_files(file_name)

        # list of files
        file_list = list(self._file_dict.keys())
            
        # open file if needed 
        if self._current_file is None:
            self._open_file(file_list[0], event_list=None)

        
        # load event
        array, info = self._load_event(
            event_index,
            trigger_index=trigger_index,
            trace_length_msec=trace_length_msec,
            trace_length_samples=trace_length_samples,
            pretrigger_length_msec=pretrigger_length_msec,
            pretrigger_length_samples=pretrigger_length_samples,
            detector_chans=detector_chans,
            adctovolt=adctovolt, adctoamp=adctoamp,
            baselinesub=baselinesub,
            baselineinds=baselineinds,
            adc_name=adc_name)



        # set back file dict
        self.clear()
        self._file_dict = current_file_dict

        # return
        if include_metadata:
            return array, info
        else:
            return array
        

    
    def read_many_events(self, filepath=None,
                         nevents=0,
                         output_format=1,
                         detector_chans=None,
                         event_nums=None, series_nums=None,
                         trigger_indices=None,
                         event_list=None,
                         trace_length_msec=None,
                         trace_length_samples=None,
                         pretrigger_length_msec=None,
                         pretrigger_length_samples=None,
                         include_metadata=False,
                         adctovolt=False, adctoamp=False,
                         baselinesub=False, baselineinds=None,
                         memory_limit=4, adc_name='adc1'):
        """
        Read multiple events (default read all events)
        
        Parameters
        ---------
        filepath: string or list  of strings
           file/path or list of files/paths (default: use current file)
          
        nevents: integer
           number of events to read  (default nb_events=0 -> all events in dumps)

        output_format: integer
            1: list of 2D ndarray[chan, samples]
            2: 3D ndarray[event, chan, samples]
 
        detector_chans: string/int or list of string/int
            detector channel name)(s) (example 'Z1PAS1', 'PD2', or 1)
            following format in setup.ini file
            If None, read all channels available 

        event_nums: list or numpy array
            Event numbers (format: dump_num * 100000 + event_index)
              
        series_nums: list or numpy array
            Series numbers (format: xyyyymmddhhmmss)
            if event_nums argument provided, series_nums should have same length!)

        include_metadata: bool 
            include file/group/dataset metadata (default = False)

        adctovolt: Bool
            Convert  from ADC to volt (Default=False) 
        
        adctoamp: Bool
            Convert  from ADC to close loop/FLL amps (Default=False) 

        baselinesub: Bool
            Apply baseline subtraction

        baselineinds: tuple (int, int) or list [int, int]
            start/stop baseline calculation (default: (10, 0.8*pretrigger length))
          
        memory_limit: Float
            Pulse data memory limit in GB [default: 2GB]

        adc_name: string
              ADC id (default: 'adc1')
          

        Return
        ------
 
        output_data : list or pandas dataframe
           traces for each channels and events

        info : list
           file/event/detector metadata 
           (if "include_metadata" = True)


        """

        # ===============================
        # Check arguments
        # ===============================

 
        # check if file needed
        if (not self._file_dict and filepath is None):
            raise ValueError(
                'ERROR: No file available. '
                + 'Use "file_name" argument!') 


        
        # detector/channel
        if (detector_chans is not None
            and not (isinstance(detector_chans, list)
                     or isinstance(detector_chans, np.ndarray))):
            detector_chans = [detector_chans]
    

        # event list
        if (event_list is not None
            and (event_nums is not None
                 or series_nums is not None
                 or trigger_indices is not None)):
            raise ValueError(
                'ERROR: Choose "event_list" argument '
                + 'OR "event_nums"/"series_nums"/"trigger_indices')


        # preliminary checks of event/series/trigger nums
        if trigger_indices is not None:
            if event_nums is None:
                raise ValueError('ERROR: "even_nums" required if '
                                 + 'event selected with "trigger indices"')
            
            if (trace_length_msec is None
                and trace_length_samples is None):
                raise ValueError('ERROR: Trace length required if '
                                 + 'event selected with "trigger indices"')

            if (pretrigger_length_msec is None
                and pretrigger_length_samples is None):
                raise ValueError('ERROR: Pretrigger length required if '
                                 + 'event selected with "trigger indices"')



        if event_nums is not None:
            
            if series_nums is None:
                raise ValueError(
                    'ERROR: "series_nums" required if '
                    + '"event_nums" argument used!')


            
        # ===============================
        # List of files
        # ===============================

        # let's keep a copy internal file dict
        current_file_dict = copy.deepcopy(self._file_dict)
        
        # convert "event_nums"/"series_nums" to "event_list"
        if event_nums is not None:

            # convert to list if not array/list
            if (not isinstance(event_nums, list)
                and not isinstance(event_nums, np.ndarray)):
                event_nums = [event_nums]

            if (not isinstance(series_nums, list)
                and not isinstance(series_nums, np.ndarray)):
                series_nums = [series_nums]
                if len(series_nums)==1 and len(event_nums)>1:
                    series_nums *= len(event_nums)
                
                
            if (len(event_nums)!=len(series_nums)):
                raise ValueError('ERROR: "series_nums" and "event_nums" '
                                 + 'need to be same length!')

            if trigger_indices is not None:
                if (not isinstance(trigger_indices, list)
                    and not isinstance(trigger_indices, np.ndarray)):
                    trigger_indices = [trigger_indices]
                if (len(event_nums)!=len(trigger_indices)):
                    raise ValueError('ERROR: "trigger_indices" and "event_nums" '
                                     + 'need to be same length!')
                    
                
            # convert to list of dictionaries
            event_list = list()
            for ievent  in range(len(event_nums)):
                event_dict = {'event_number': event_nums[ievent],
                              'series_number': series_nums[ievent]}

                if trigger_indices is not None:
                    event_dict['trigger_index'] = trigger_indices[ievent]
                    
                event_list.append(event_dict)
                
                    
                
        # set files
        file_path = list(self._file_dict.keys())
        if filepath is not None:
            file_path = filepath
        self.set_files(file_path, series=series_nums,
                       event_list=event_list)
                                              
        # set file list
        if not self._file_dict:
            raise ValueError('ERROR: No files selected!')
                        

    
       
        # ===============================
        # Check raw data
        # ===============================
        
        # initialize useful parameters
        nb_events_tot = 0
        nb_channels = 0
        nb_samples = 0

        
        # loop files and check number of channels/events/samples
        for file_name, file_list in self._file_dict.items():
            
            # get metadata
            metadata = self.get_metadata(file_name)
            adc_metadata = metadata['groups'][adc_name]

            
            # check channels
            nb_channels_file = adc_metadata['nb_channels']     
            if detector_chans is not None:
                
                # connections
                connections = self.get_connection_dict(adc_name=adc_name,
                                                       metadata=metadata)
                                
                # loop channels
                nb_channels_file  = 0
                for chan_name in connections['detector_chans']:
                    if chan_name in detector_chans:
                        nb_channels_file +=1

                        
                # error if no channel found
                if (nb_channels_file==0):
                    self.clear()
                    self._file_dict = current_file_dict
                    error_msg = ('Unable to find selected channel(s).'
                                 + ' Check connection table!')
                    if self._raise_errors:
                        raise ValueError(error_msg)
                    else:
                        print('ERROR: ' + error_msg)
                        if include_metadata:
                            return [],[]
                        else:
                            return []
            

            if nb_channels==0:
                nb_channels = nb_channels_file
            elif nb_channels != nb_channels_file:
                self.clear()
                self._file_dict = current_file_dict
                raise ValueError('ERROR: inconsistent number '
                                 + 'of channels between files!')
                
            
            # check number of events:
            nb_events_file = adc_metadata['nb_events']
            if file_list is not None:
                nb_events_file = len(file_list)

            nb_events_tot += nb_events_file
            if nevents>0  and nb_events_tot>=nevents:
                nb_events_tot = nevents

                        
            # check number of samples
            nb_samples_file = adc_metadata['nb_samples']

            # user selected nb samples
            fs = adc_metadata['sample_rate']
            if trace_length_samples is not None:
                nb_samples_file = trace_length_samples
            elif trace_length_msec is not None:
                nb_samples_file = int(
                    fs*trace_length_msec/1000
                )
            
            if nb_samples==0:
                nb_samples = nb_samples_file
            elif  output_format!=1 and nb_samples_file!=nb_samples:
                self.clear()
                self._file_dict = current_file_dict
                error_msg = 'Unable to return 3D arrray due to inconsistent nb of samples!'
                if self._raise_errors:
                    raise ValueError(error_msg)
                else:
                    print('ERROR: ' + error_msg)
                    print('Use output=1 (event list) instead or check files')
                    if include_metadata:
                        return [],[]
                    else:
                        return []

            # check max events
            if (nevents>0  and nb_events_tot>=nevents):
                break

            
        # clear
        self.clear()
        
        # check number of events
        if nb_events_tot == 0:
            self.clear()
            self._file_dict = current_file_dict
            raise ValueError('ERROR: No events found!')
        
       
        # ===============================
        # Memory check
        # ===============================
                
        sample_bytes = 2
        if adctovolt or adctoamp or baselinesub:
            sample_bytes = 8
            
        output_memory_per_event = sample_bytes*nb_samples*nb_channels/1e9
        output_memory = nb_events_tot*output_memory_per_event
        if output_memory>memory_limit:
            nb_events_tot_temp = int(round(memory_limit/output_memory_per_event))
            print('WARNING: Max number events based on memory limit of '
                  + str(memory_limit) + 'GB is '
                  + str(nb_events_tot_temp) + ' out of '
                  + str(nb_events_tot) +'!')
            nb_events_tot = nb_events_tot_temp

            
        # ===============================
        #  Initialize output
        # ===============================
                   
        output_data = list()
        info_list = list()
     
        if output_format==2:
            if adctovolt or adctoamp or baselinesub:
                output_data = np.zeros((nb_events_tot, nb_channels, nb_samples),
                                       dtype=np.float64)
            else:
                output_data = np.zeros((nb_events_tot, nb_channels, nb_samples),
                                       dtype=np.int16)
                
        # ===============================
        #  Loop and read events
        # ===============================
     
        # loop events
        for ievent in range(nb_events_tot):
            
            # read event
            traces = []
            info = dict()
           
            traces, info = self.read_next_event(
                trace_length_msec=trace_length_msec,
                trace_length_samples=trace_length_samples,
                pretrigger_length_msec=pretrigger_length_msec,
                pretrigger_length_samples=pretrigger_length_samples,
                detector_chans=detector_chans,
                adctovolt=adctovolt, adctoamp=adctoamp,
                baselinesub=baselinesub,
                baselineinds=baselineinds,
                include_metadata=True)
                
            # check if reading error
            if info['read_status']>0:
                print('WARNING: Unable to read event #' + str(ievent) + '! Error message: ')
                print('WARNING: "' + info['error_msg'] + '". Stopping event loop')
                break

            
            # add to metadata list
            if include_metadata:
                info_list.append(info)

            
            # store
            if (output_format==1 or output_format==3):
                output_data.append(traces)
            else:
                output_data[ievent,:,:] = traces
                

        # reset file list to original list
        # if needed
        self.clear()
        self._file_dict = current_file_dict


        if include_metadata:
            return output_data, info_list
        else:
            return output_data
        
             

    def get_current_file_name(self):
        """
        Get current file name
        
        Parameters
        ----------
        None


        Return
        ------
        
        file_name : str
          current file name

        """
        
        return self._current_file_name
        


    
    def get_metadata(self, file_name=None, group_name=None, dataset_name=None, 
                     include_dataset_metadata=False):

        """
        Function to get metadata.
       
        Parameters
        ----------
          
        file_name: string, optional
            if no file name provided: use current file

        group_name:  string, optional
            H5 "Group" name
            Default: None, read all groups
          
        dataset_name: string, optional, 
            H5 "Dataset" name
            Default: all datasets
         
        include_dataset_metadata : bool, optional
            If True, include dataset metadata
            Default: False
        

        Return
        ------
        
        metadata: dict
           dictionary with all metadata

        """

        metadata = dict()


        # check input 
        if file_name is None and self._current_file is None:
            error_msg = 'No file currently open and no "file_name" argument not provided!'
            if self._raise_errors:
                    raise ValueError(error_msg)
            else:
                print('ERROR: ' + error_msg)
                print('Please open a file or provide a file name!')
                return metadata

        # open file if needed
        if (file_name is not None
            and self._current_file_name!=file_name):
            
            # check if a file already open
            if self._current_file is not None:
                self._close_file()
            # open
            self._open_file(file_name, event_list=None,
                            load_metadata=False)
            

        # load metadata (if "dataset" metadata requested -> reload)
        if dataset_name is not None:
            include_dataset_metadata = True

        if self._current_file_metadata is None or include_dataset_metadata:
            self._load_metadata(include_dataset_metadata)
                
            
        # find specific metadata
        metadata = dict()
        if group_name is not None:
            if group_name in self._current_file_metadata['group_list']:
                group_metadata = self._current_file_metadata['groups'][group_name]
                if dataset_name is not None:
                    if dataset_name in group_metadata['dataset_list']:
                        metadata = group_metadata['datasets'][dataset_name]
                else:
                    metadata = group_metadata
        else:
            metadata = self._current_file_metadata


        # close file
        if file_name is not None:
            self._close_file()
        

        return metadata
            



    def get_detector_config(self, file_name=None,
                            adc_name='adc1',
                            use_chan_dict=True):   
        """
        Get detector configuration
        """
        
        detector_config = dict()
        
        # get metadata
        metadata = None
        if file_name is not None:
            metadata = self.get_metadata(file_name=file_name)
        elif self._current_file_metadata is not None:
            metadata = self._current_file_metadata
        else:
            raise ValueError('ERROR in get_detector_config: a file name needs to be provided!')
        
        

        # config name
        config_name = 'detconfig1'
        if adc_name!='adc1':
            config_name = 'detconfig' + adc_name[3:]

        # check if available
        if config_name not in metadata['group_list']:
            print('ERROR: unable to find detector config!')
            return []

        # group metadata
        detector_config_dict = metadata['groups'][config_name]
        #if 'adc_name' in detector_config_dict and adc_name!=detector_config_dict['adc_name']:
        #    print('ERROR: Unexpected detector configuration format!')
        #    return []


        # add detector/channel list from adc metadata, needs to match
        # detector settings array order
        tes_chans = list()
        detector_chans = list()
        controller_chans = list()
        connection_dict = self.get_connection_dict(adc_name=adc_name,
                                                   metadata=metadata)

        if connection_dict:
            chan_list = detector_config_dict['channel_list']
            if (not isinstance(chan_list, np.ndarray)
                and not isinstance(chan_list, list)):
                chan_list  = [chan_list]
            for chan in chan_list:
                if chan in connection_dict['adc_chans']:
                    ind = connection_dict['adc_chans'].index(int(chan))
                    if connection_dict['controller_chans']:
                        controller_chans.append(connection_dict['controller_chans'][ind])
                    if connection_dict['tes_chans']:
                        tes_chans.append(connection_dict['tes_chans'][ind])
                    if connection_dict['detector_chans']:
                        detector_chans.append(connection_dict['detector_chans'][ind])
                         
                                
        detector_config_dict['tes_chans'] =  tes_chans
        detector_config_dict['detector_chans'] =  detector_chans
        detector_config_dict['controller_chans'] =  controller_chans   

        # convert to list if needed (size of nb channels)
        nb_chan = len(detector_config_dict['detector_chans'])
        for config in detector_config_dict.keys():
            param = detector_config_dict[config]
            if not isinstance(param, list) and not isinstance(param, np.ndarray):
                detector_config_dict[config] = [detector_config_dict[config]]*nb_chan
    
        # convert to dictionary
        detector_config = dict()
        if use_chan_dict:
            chan_list = detector_config_dict['detector_chans']
            for chan in chan_list:
                chan_index = detector_config_dict['detector_chans'].index(chan)
                detector_config[chan] = dict()
                for config in detector_config_dict:
                    if len(detector_config_dict[config])==nb_chan:
                        detector_config[chan][config] = detector_config_dict[config][chan_index]
        else:
            detector_config = detector_config_dict
            
            
                      
        return detector_config


                                    
    def get_connection_dict(self, file_name=None, adc_name='adc1', metadata=None):
        """
        Get connection dictionary for specifid adc name
        """

        # initialize
        connection_dict=dict()

        # metadata
        adc_metadata = None
        if metadata is None or 'group_list' not in metadata:
            metadata = self.get_metadata(file_name=file_name)

        if 'group_list' in metadata and adc_name in metadata['group_list']:
            adc_metadata  = metadata['groups'][adc_name]

        if adc_metadata is None:
            error_msg = 'ADC metadata not found!'
            if self._raise_errors:
                    raise ValueError(error_msg)
            else:
                print('WARNING: ' + error_msg)
                return conection_dict


        connection_dict['adc_chans'] = list()
        connection_dict['controller_chans'] = list()
        connection_dict['tes_chans'] = list()
        connection_dict['detector_chans'] = list()
        
        # loop metadata to find connections
        for key,value in adc_metadata.items():
            if key.find('connection')!=-1:
                connection_dict['adc_chans'].append(int(key[10:]))
                for connection_type in value:
                    channel_name = connection_type[connection_type.find(':')+1:]
                    if connection_type.find('tes:')!=-1:
                        connection_dict['tes_chans'].append(channel_name)
                    if connection_type.find('detector:')!=-1:
                        connection_dict['detector_chans'].append(channel_name)
                    if connection_type.find('controller:')!=-1:
                        connection_dict['controller_chans'].append(channel_name)

        return connection_dict                              
    

    def get_connection_table(self, file_name=None, metadata=None):
        """
        Get connection table
        """
        
        if metadata is None:
            metadata = self.get_metadata(file_name=file_name)
        
        # check adc list exist 
        if 'adc_list' not in metadata:
            print('ERROR: No ADC metadata found in the file!')
            return

        
        # loop adc and find connection
        connection_list = list()
        connection_name_list = list()
        for adc_id in metadata['adc_list']:
            adc_metadata = metadata['groups'][adc_id]
            for key,val in adc_metadata.items():
                if key[0:10]=='connection':
                    adc_chan = re.sub(r'\s+','', str(key))[10:]
                    name_val_list, name_list, val_list = (
                        connection_utils.extract_adc_connection(list(val)))
                    val_list  = [adc_id,adc_chan] + val_list
                    name_list = ['adc_id','adc_channel'] + name_list
                    connection_list.append(val_list)
                    if not connection_name_list:
                        connection_name_list = name_list
                    elif connection_name_list!=name_list:
                        print('ERROR: missing adc connection values!')
                        
                    
        connection_table = pd.DataFrame(connection_list,
                                        columns=connection_name_list )
        return connection_table



    
    def _open_file(self, file_name, event_list=None,
                   rw_string='r', load_metadata=True):
        """
        open file 
        """
        if self._current_file is not None:
            self._close_file()
            
        file = None
        try:
            file = h5py.File(file_name, rw_string)
        except:
            print('ERROR: unable to open file ' + file_name)
            return

        self._current_file = file
        self._current_file_name = file_name
        self._current_file_nb_events = 0
        self._current_file_event_counter = 0
        
        # load metadata
        if load_metadata:

            self._load_metadata()
            
            # check nb of events in file
            if 'adc_list' not in self._current_file_metadata:
                print('WARNING: No ADC information found in the file')
                return

            for adc_name in self._current_file_metadata['adc_list']:
                nb_events_adc = self._current_file_metadata['groups'][adc_name]['nb_datasets']
                if self._current_file_nb_events==0:
                    self._current_file_nb_events = nb_events_adc
                elif self._current_file_nb_events != nb_events_adc:
                    print('ERROR: Inconsistent number of events between ADC devices!')
                    self._close_file()
                    return False

        self._file_counter += 1


        # event list
        self._current_file_event_list = event_list
        if event_list is not None:
            self._current_file_nb_events = len(event_list)
        
        return True
        
        
            
    

    def _close_file(self):
        """
        Close current file and reset
        current file parameters

        Parameters
        ----------
        None

        Return
        ------
        None

        """

        if self._current_file is not None:
            self._current_file.close()
  
        # initialize
        self._current_file = None
        self._current_file_name = None
        self._current_file_metadata = None
        self._current_file_nb_events = 0
        self._current_file_event_counter = 0
        self._current_file_event_list = None
        

    def _load_metadata(self, include_dataset_metadata=False):

        """
        Function to load all metadata from current file. Store in 
        an internal dictionary

        Parameters
        ----------

        include_dataset_metadata : bool, optional
           if True, read dataset metadata
           Default: False


        Return
        ------
        
        metadata_dict : dict
          dictionary with metadata
        

        """

        # check if file exist
        if self._current_file is None:
            return
               
        # initialize containner
        metadata_dict = dict()
      

        # file matadata
        metadata_dict = self._extract_metadata(self._current_file.attrs)
      
    
        # group/dataset metadata
        metadata_dict['group_list'] = list()
        metadata_dict['adc_list'] = list()
        metadata_dict['groups'] = dict()
           
        # Loop groups
        for key, group in self._current_file.items():
       
            # update list
            metadata_dict['group_list'].append(key)
            if key[0:3]=='adc':
                metadata_dict['adc_list'].append(key)
                                
            # save metadata
            metadata_dict['groups'][key] = dict()
            metadata_dict['groups'][key] =  self._extract_metadata(group.attrs)
        
            # datasets
            dataset_list = list(group.keys())
            metadata_dict['groups'][key]['dataset_list'] = dataset_list
            metadata_dict['groups'][key]['nb_datasets'] = len(dataset_list)
                

            if include_dataset_metadata and len(dataset_list)>0:
                    
                # Loop datasets and add metadata
                metadata_dict['groups'][key]['datasets'] = dict()
                for dataset_key, dataset in group.items():
                    metadata_dict['groups'][key]['datasets'][dataset_key] = (
                        self._extract_metadata(dataset.attrs)
                    )

                        

        # save
        self._current_file_metadata = metadata_dict

        
    def _extract_metadata(self, attributes):
        """
        Extract metadata from attribute dictionary
        """
        
        metadata_dict = dict()
        for key,value in attributes.items():
            if isinstance(value, bytes):
                value = value.decode()
            elif isinstance(value, np.ndarray):
                if value.dtype == np.object:
                    value = value.astype(str)
                # a few particular cases
                if key == 'run_purpose':
                    value = ' '.join(list(value))                    
            metadata_dict[key] = value
        return metadata_dict
        
    
    def _load_event(self, event_index,
                    trigger_index=None,
                    trace_length_msec=None,
                    trace_length_samples=None,
                    pretrigger_length_msec=None,
                    pretrigger_length_samples=None,
                    detector_chans=None,
                    adctovolt=False, adctoamp=False,
                    baselinesub=False, baselineinds=None,
                    adc_name='adc1'):
        
        """
        Load traces and metadata from current file  based on
        event index
 
        Parameters
        ----------
        event_index : int
          event (hdf5 "dataset")  number 
        
        detector_chans : str or list, optional
          detector/channel name or list of detectors/channels
          if None, get all channels (default)

        adctovolt : bool, optional
          convert from ADC to volts
          default: False

        adctoamp : bool, optional
          convert from ADC to current amps
          default: False
        
              
        baselinesub: bool, optional
          if True, subtract pre-pulse baseline
          default: False

        baselineinds: tuple (int, int) or list [int, int]
          min/max index for  baseline calculation 
          default: (10, 0.8*pretrigger length))
          
        adc_name : str, optional
          name/ID of the adc
          default: "adc1"

        Return
        ------
        
        array : 2D numpy array
           traces for each channel [nb channel, nb samples]

        info : dict
           file/event/detector metadata (if "include_metadata" = True)


        
        """

        # ===================================
        # Get HDF5 dataset
        # ===================================

        # check file open
        if self._current_file is None:
            raise ValueError('No file open!')

        # get dataset
        dataset_name = 'event_' + str(event_index)
        dataset = self._current_file[adc_name][dataset_name]
        dataset_dims = dataset.shape

        # get dataset metadata
        info = self._extract_metadata(dataset.attrs)
        info.update(self._extract_metadata(self._current_file.attrs))
        info.update(self._extract_metadata(self._current_file[adc_name].attrs))
        info['read_status'] = 0
        info['error_msg'] = ''
        
        
        # ===================================
        # Channel indices
        # ===================================

        # extract list of adc channels, index correspond to array index!
        adc_nums_file = info['adc_channel_indices']
        if (not isinstance(adc_nums_file, list)
            and not isinstance(adc_nums_file, np.ndarray)):
            adc_nums_file = np.array([adc_nums_file])
        nb_channels_file = len(adc_nums_file)


        # get connection map and convert to numpy array
        connections = self.get_connection_dict(adc_name=adc_name, metadata=info)
              
        # Filter based on detector_chans argument
        selected_array_indices = list()
        selected_adc_nums = list()
        selected_detector_chans = list()
        selected_tes_chans = list()
        selected_controller_chans = list()
        
        
        if detector_chans is not None:
            
            # convert detector_chans to list if needed
            if (not isinstance(detector_chans, list)
                and not isinstance(detector_chans, np.ndarray)):
                detector_chans = [detector_chans]
                            

            # loop selected channels
            for chan in detector_chans:

                # check
                if chan not in connections['detector_chans']:
                    raise ValueError('Detector channel ' + chan
                                     + ' not available in raw data.'
                                     + ' Check connection map!')
                
                # find channel index in connection map
                ind = connections['detector_chans'].index(chan)

                # extract selected ADC number
                selected_adc = int(connections['adc_chans'][ind])
                if selected_adc not in adc_nums_file:
                    raise ValueError('Problem with raw data. Unable to find ADC channel')
                
                # save connections
                selected_adc_nums.append(selected_adc)
                selected_detector_chans.append(connections['detector_chans'][ind])
                if 'tes_chans' in connections:
                    selected_tes_chans.append(connections['tes_chans'][ind])
                if 'controller_chans' in connections:
                    selected_controller_chans.append(connections['controller_chans'][ind])

                # save array index
                ind_adc = int(np.where(adc_nums_file==selected_adc)[0])
                selected_array_indices.append(ind_adc)                
                
        else:
            selected_array_indices = list(range(nb_channels_file))
            selected_adc_nums = list(adc_nums_file)
            for adc_chan in selected_adc_nums:
                ind = connections['adc_chans'].index(adc_chan)
                selected_detector_chans.append(connections['detector_chans'][ind])
                if 'tes_chans' in connections:
                    selected_tes_chans.append(connections['tes_chans'][ind])
                if 'controller_chans' in connections:
                    selected_controller_chans.append(
                        connections['controller_chans'][ind]
                    )

        # check number channels
        if not selected_array_indices or len(selected_array_indices)==0:
            raise ValueError('Unable to find selected channel(s). Check connection table!')

        # store info
        info['adc_channel_indices'] = selected_adc_nums
        info['adc_chans'] = selected_adc_nums
        info['detector_chans'] = selected_detector_chans
        info['tes_chans'] = selected_tes_chans
        info['controller_chans'] = selected_controller_chans
        info['adc_conversion_factor'] =  info['adc_conversion_factor'][selected_array_indices,:]
        info['voltage_range'] = info['voltage_range'][selected_array_indices,:]

        # get detector config
        detector_config = self.get_detector_config()
        info['detector_config'] = dict()
        for det in info['detector_chans']:
            info['detector_config'][det] = detector_config[det]


            
        # ===================================
        # Trigger indices
        # ===================================
        
        trace_min_index = None
        trace_max_index = None

        # check trigger index
        if trigger_index is not None:
            if (trace_length_msec is None 
                and trace_length_samples is None):
                print('WARNING: Unable to extract trace based on '
                      + 'trigger index without trace length. '
                      + 'Returning full trace!')
                trigger_index = None
        else:
            if (trace_length_msec is not None 
                or  trace_length_samples is not None):
                  print('WARNING: Unable to use trace lenght argument'
                        + ' without trigger info. '
                        + 'Returning full trace!')

        # extract trigger
        if trigger_index is not None:

            trigger_index = int(trigger_index)
    
            # number samples
            nb_samples = None
            fs = info['sample_rate']
            if trace_length_samples is not None:
                nb_samples = trace_length_samples
            elif trace_length_msec is not None:
                nb_samples = int(
                    fs*trace_length_msec/1000
                )
            else:
                raise ValueError(
                    'ERROR: Number of samples required to '
                    + 'extract trace'
                )

            # pre-trigger
            nb_pretrigger_samples = int(nb_samples/2)
            if pretrigger_length_samples is not None:
                nb_pretrigger_samples = pretrigger_length_samples
            elif pretrigger_length_msec is not None:
                nb_pretrigger_samples = int(
                    fs*pretrigger_length_msec/1000
                )

            # min/max index
            trace_min_index = int(trigger_index - nb_pretrigger_samples)
            trace_max_index = int(trace_min_index + nb_samples)

            if (trace_min_index<0
                or trace_max_index>dataset_dims[1]):
                raise ValueError(
                    'ERROR: Unable to extract trigger. '
                    + ' Trace length too long!')
            


        # ===================================
        # Extract trace
        # ===================================


        # initialize empty trace
        slice_samples = None
        dim_0 = len(selected_array_indices)
        dim_1 = dataset_dims[1]
        
        if (trace_min_index is not None
            and trace_max_index is not None):
            dim_1 = trace_max_index-trace_min_index
            slice_samples = slice(trace_min_index, trace_max_index)
            
        traces_int = np.empty((dim_0, dim_1), dtype=dataset.dtype)
        
        # Read the portion of the array using read_direct
        for i, index in enumerate(selected_array_indices):
            if  slice_samples is not None:
                dataset.read_direct(traces_int[i],
                                    np.s_[index, slice_samples])
            else:
                dataset.read_direct(traces_int[i], np.s_[index])
        
        
        # convert to volt/amps
        traces = []
        if adctovolt or adctoamp:

            # initialize
            traces = np.zeros_like(traces_int, dtype=np.float64)

            # convert to volts
            for ichan in range(traces_int.shape[0]):
                cal_coeff = info['adc_conversion_factor'][ichan][::-1]
                poly = np.poly1d(cal_coeff)
                traces[ichan,:] = poly(traces_int[ichan,:])

            # convert to amps
            if adctoamp:
                if detector_config is None:
                    raise ValueError('ERROR: Unable to convert to amps. '
                                     + 'No detector config available!')
                for ichan in range(traces.shape[0]):
                    det = info['detector_chans'][ichan]
                    if 'close_loop_norm' in detector_config[det]:
                        traces[ichan,:] = traces[ichan,:]/detector_config[det]['close_loop_norm']
                    else:
                        raise ValueError('ERROR: Unable to convert to amps. '
                                         + 'No normalization available for ' + det)      
        else:
            traces = traces_int
                    
            
        # baseline subtract
        if baselinesub:
            
            # find baseline start/stop
            baseline_start = None
            baseline_stop = None
            if baselineinds is not None:
                if len(baselineinds)!=2:
                    raise ValueError('ERROR: baselineinds should be list/tuple of length 2')
                baseline_start = baselineinds[0]
                baseline_stop =  baselineinds[1]
                
            elif 'nb_samples_pretrigger' in info:
                baseline_start = 10
                baseline_stop = int(round(info['nb_samples_pretrigger']*0.8))

            if (baseline_start is None or baseline_stop is None or
                baseline_stop<=baseline_start or baseline_stop>=traces.shape[1]):
                raise ValueError('ERROR: Unable to find baseline start/stop. '
                                 + 'Add argument "baselineinds"')

            traces = traces - np.mean(traces[:,baseline_start:baseline_stop],
                                      axis=-1, keepdims=True)
            
        
        return traces, info
        


    def _get_file_dict(self, filepaths, series=None, event_list=None):
        """
        Get a list of files (full path)  from directories/files
        and filter based on event_list

        Parameters
        ----------
        filepaths : str or list
         file/directory and/or list of files/directories

        series : str/int or list/array of str/int
         filter file list based on series number(s) or series name(s)

        event_list : list, optional
          list containing dictionary with events metadata
          such as 
             - "series_number"
             - "event_number"
             - "group_name" 
           
           File list is filtered based on requested events        
          

        Return
        ------
        
        file_list : list 
          list of files (full path)

        """

        # =======================
        # Get list of files
        # =======================

        # check if group name
        # available in event_list
        group_names = list()
        if event_list is not None:
            for event_dict in event_list:
                if 'group_name' in event_dict.keys():
                    group_names.append(str(event_dict['group_name']))
        
        # make unique
        group_names = list(set(group_names))
     
        # loop file/path list to get list of files
        file_list  = list()
        if isinstance(filepaths, str):
            filepaths = [filepaths]

        for filepath in filepaths:
            
            # case directory
            if os.path.isdir(filepath):
                
                search_list = list()
                for group_name in group_names:
                    # add group name to path if not
                    # already in path
                    if group_name not in filepath:
                        filepath =  (filepath + '/'
                                     + group_name)
                        
                    # add to search list
                    search_str = filepath + '/*.hdf5'
                    if search_str not in search_list:
                        search_list.append(search_str)

                if not search_list:
                    search_list = [filepath + '/*.hdf5']

                # get files
                for search_str in search_list:
                    file_list.extend(glob(search_str))

            # case a file
            else:
                if filepath[-4:]!='hdf5':
                    filepath += '.hdf5'
                if os.path.isfile(filepath):
                    file_list.append(filepath)

        if not file_list:
            if self._raise_errors:
                raise ValueError('No files found!')
            else:
                print('ERROR: No files found!')
                return

        # make unique and sort
        file_list = list(set(file_list))
        file_list = sorted(file_list)


        # =======================
        # Filter files based on
        # series
        # =======================

        # series
        if series is not None:

            # convert to array
            if (not isinstance(series, list)
                and not isinstance(series, set)
                and not isinstance(series, np.ndarray)):
                series = [series]


            # unique
            series = list(set(series))

            # loop and convert to series name if needed
            for it in range(len(series)):
                if isinstance(series[it], int):
                    series[it] = extract_series_name(series[it])


            # filter list
            file_list_temp = list()
            for afile in file_list:
                for aseries in series:
                    if aseries in afile:
                        file_list_temp.append(afile)
                        break
            # replace
            file_list = file_list_temp
                
                
        # =======================
        # Filter files based on
        # event_list
        # build dictionary
        # =======================

        # initialize
        output_dict = dict()

        # case no event list
        if event_list is None:
            for afile in file_list:
                output_dict[afile] = None
            return output_dict


        # case event list
        
        for event_dict in event_list:

            # checks
            if 'series_number' not in event_dict.keys():
                raise ValueError(
                    'ERROR: "series_number" required in event dictionary!'
                )
            
            if 'event_number' not in event_dict.keys():
                raise ValueError(
                    'ERROR: "event_number" required in event dictionary!'
                )

            
            # build file name (without prefix)
            series_num =  int(event_dict['series_number'])
            series_name = extract_series_name(series_num)
            
            dump_num = int(event_dict['event_number']/100000)
            dump_name = str(dump_num)
            for x in range(1,5-len(dump_name)):
                dump_name = '0' + dump_name

            file_name = (series_name
                         + '_F'
                         + dump_name
                         + '.hdf5')

            # find file in file_list
            full_file_name = str()
            for afile in file_list:
                if file_name in afile:
                    full_file_name = afile
                    break

            if not full_file_name:
                raise ValueError(
                    'ERROR: Unable to find file for a requested event.'
                    + ' Check path!' )

            # double check group if available
            if 'group_name' in event_dict.keys():
                group_name = str(event_dict['group_name'])
                if group_name not in full_file_name:
                    raise ValueError(
                        'ERROR: Inconsistent group name. Unable to '
                        ' find proper data!'
                    )

            # save
            if full_file_name in output_dict.keys():
                output_dict[full_file_name].append(event_dict)
            else:
                output_dict[full_file_name] = [event_dict]
            
        return output_dict
            
    
        







                              


    
class H5Writer:
    
    def __init__(self, raise_errors=True, verbose=True):


        self._raise_errors = raise_errors
        self._verbose = verbose
        
        # file path
        self._series_path = None

        # series
        self._series_name = None
        self._series_num = None
        
        # current file info
        self._current_file = None
        self._current_file_name = None
        self._current_file_nb_events = 0
        self._current_file_event_counter = 0
        self._current_file_adc_group = None
        self._current_file_detconfig_group = None
        
        # metadata
        self._file_metadata = None
        self._detector_config = None
        self._adc_config  = None

        
        # event counter
        self._global_events_counter = 0
         
        # file counter
        self._file_counter = 0

        # max event per dump
        self._nb_events_per_dump_max = 1000
        self._adc_name = 'adc1'


    def initialize(self, series_name, data_path='./'):
        """
        Initialize new writing
        """
        
        # clear everything
        self.clear()
        
        # series name 
        self._series_name = series_name
        self._series_num = extract_series_num(series_name)
        


        # create new directory
        #self._series_path = data_path + '/' + series_name
        self._series_path = data_path
        
        if not os.path.isdir(self._series_path):
            os.mkdir(self._series_path)
            os.chmod(self._series_path,
                     stat.S_IRWXG | stat.S_IRWXU | stat.S_IROTH | stat.S_IXOTH)


    def set_metadata(self, file_metadata=None, adc_config=None, detector_config=None):
        """
        Set metadata which will be written  in each files
        file_metadata = general data taking information (file level metadata)
        adc_config = adc configuration (group level metadata)
        detector_config = detector settings (group level metadata)
        """

        if file_metadata is not None:
        
            if isinstance(file_metadata, dict):
                self._file_metadata = file_metadata
            else:
                print('WARNING: metadata needs to be a dictionary')

                
        if adc_config is not None:
            
            if isinstance(adc_config, dict):
                self._adc_config = adc_config
            else:
                print('WARNING: adc_config needs to be a dictionary')


        if detector_config is not None:

            if isinstance(detector_config, dict):
                self._detector_config = detector_config
            else:
                print('WARNING: detector config needs to be a dictionary')


                

            

    def close(self):
        """
        close current file
        """

        self._close_file()
            
        
    def clear(self):
        self._close_file()
        self._file_counter = 0
        self._current_file = None
        self._current_file_name = None
        self._current_file_adc_group = None
        self._current_file_detconfig_group = None    
        self._current_file_event_counter = 0
        self._global_event_counter = 0
        self._file_metadata = None
        self._detector_config = None
        self._adc_config = None
     
        
    def write_event(self, data_array, prefix=None, dataset_metadata=None,
                    data_mode=None, adc_name='adc1'):
        """
        write pulse data in files
        """


        # open file if needed
        if (self._current_file is None or
            self._current_file_event_counter >= self._nb_events_per_dump_max):
            self._open_file(prefix=prefix)


        # event counter
        self._current_file_event_counter += 1
        self._global_event_counter += 1
        
        # create dataset
        dataset_name = 'event_' + str(self._current_file_event_counter)
        dataset = self._current_file_adc_group.create_dataset(dataset_name, data=data_array)
      
        # add metadata
        if dataset_metadata is not None:
            for key,val in dataset_metadata.items():
                if (isinstance(val, np.ndarray) and val.dtype.type is np.str_):
                    dt = h5py.string_dtype()
                    val = val.astype(dt)
                dataset.attrs[key] = val

        dataset.attrs['event_id'] = self._global_event_counter 
        dataset.attrs['event_index'] = self._current_file_event_counter
        dataset.attrs['event_num'] = self._file_counter *100000 + self._current_file_event_counter
                
        # update number of events
        self._current_file_adc_group.attrs['nb_events'] = self._current_file_event_counter
        if data_mode is not None:
            self._current_file_adc_group.attrs['data_mode'] = str(data_mode)


        # flush
        self._current_file.flush()
        





                    
    def _open_file(self, prefix=None):
        """
        open file 
        """

        # close file if needed
        if self._current_file is not None:
            self._close_file()


        # dump
        self._file_counter +=1
        dump = str(self._file_counter)
        for x in range(1,5-len(dump)):
            if x>=1:
                dump = '0'+dump


        # full file name
        file_name = self._series_path + '/'
        if prefix is not None:
            file_name += prefix + '_'
        file_name += self._series_name + '_F' + dump + '.hdf5'
        print('INFO: Opening file name "' + file_name + '"')
        
        
        file = None
        try:
            file = h5py.File(file_name, 'w')
        except:
            print('ERROR: Unable to open file ' + file_name)
            return

        self._current_file = file
        self._current_file_name = file_name
        self._current_file_nb_events = 0
        self._current_file_event_counter = 0


        # file metadata
        if self._file_metadata is not None:
            for key,val in self._file_metadata.items():
                if (isinstance(val, np.ndarray) and val.dtype.type is np.str_):
                    dt = h5py.string_dtype()
                    val = val.astype(dt)
                self._current_file.attrs[key] = val
        self._current_file.attrs['prefix'] = prefix
        self._current_file.attrs['series_num'] = self._series_num
        self._current_file.attrs['dump_num'] = int(dump)
        
        # detector config
        if self._detector_config is not None:
            for config_key,config_val in self._detector_config.items():
                if isinstance(config_val,dict):
                    self._current_file_detconfig_group = self._current_file.create_group(config_key)
                    for key,val in config_val.items():
                        if (isinstance(val, np.ndarray) and val.dtype.type is np.str_):
                            dt = h5py.string_dtype()
                            val = val.astype(dt)
                        self._current_file_detconfig_group.attrs[key] = val
        
        # create adc group
        if self._adc_config is not None:
            for config_key,config_val in self._adc_config.items():
                if isinstance(config_val,dict):
                    self._current_file_adc_group  = self._current_file.create_group(config_key)
                    for key,val in config_val.items():
                        if (isinstance(val, np.ndarray) and val.dtype.type is np.str_):
                            dt = h5py.string_dtype()
                            val = val.astype(dt)
                        self._current_file_adc_group.attrs[key] = val
                                
        
                   
    def _close_file(self):

        if self._current_file is not None:
            self._current_file.close()
  
        # initialize
        self._current_file = None
        self._current_file_name = None
        self._current_file_nb_events = 0
        self._current_file_adc_group = None
        self._current_file_detconfig_group = None
        self._current_file_event_counter = 0


        
             
