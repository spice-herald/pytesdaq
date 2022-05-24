import h5py
import re
import os
import numpy as np
import pandas as pd
from glob import glob
import stat
import matplotlib.pyplot as plt
import warnings


from pytesdaq.utils import connection_utils


def extract_series_num(series_name):
    """
    Extract series number from file name or series name
    Assume series name has the following. This function
    should only be used if "series_num" is not stored in raw 
    data.

    Naming convention:  Ix_Dyyyymmdd_Thhmmss
        
    Return:

    serie_num [np.uint64] 
    (format xyyyymmddhhmmss)
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
  
    Arguments:
    ----------
    series_num: int

    Return:
    
    serie_num [np.uint64] 
    (format xyyyymmddhhmmss)
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

    # remove poth
    if file_name.find('/')!=-1:
        file_name = file_name.split('/')[-1]


    # find  dump string
    dump_num = None
    pos = file_name.find('_F')
    if pos>0:
        dump_num = int(file_name[pos+2:pos+6])
          
    return dump_num
    







class H5Reader:
    
    def __init__(self, raise_errors=True, verbose=True):


        self._raise_errors = raise_errors
        self._verbose = verbose
        
        # list of files
        self._file_list = list()
        

        # current file info
        self._current_file = None
        self._current_file_name = None
        self._current_file_metadata = None
        self._current_file_nb_events = 0
        self._current_file_event_counter = 0
       
        # event counter
        self._global_event_counter = 0
         
        # file counter
        self._file_counter = 0
        
    
    def set_files(self, filepaths):
        """
        Set file namelist

        Args:
          list of file/path  name (list of string)  
          OR single file/path name (string)
        """
        
        self.clear()
        self._file_list = list()
        
        if isinstance(filepaths, str):
            filepaths = [filepaths]

        # loop file/path list to get list of files
        file_list_temp  = list()
        for filepath in filepaths:
            
            if os.path.isdir(filepath):
                file_list_temp.extend(glob(filepath+'/*.hdf5'))
            else:
                if filepath[-4:]!='hdf5':
                    filepath += '.hdf5'
                if os.path.isfile(filepath):
                    file_list_temp.append(filepath)
            
        if not file_list_temp:
            if self._raise_errors:
                raise ValueError('No files found!')
            else:
                print('ERROR: No files found!')
                return


        # loop again to check for duplicate
        self._file_list = list()
        file_name_list = list()
        for file_name in file_list_temp:
            file_name_split = file_name
            if file_name.find('/')!=-1:
                file_name_split = file_name.split('/')[-1]
            if file_name_split not in file_name_list:
                file_name_list.append(file_name_split)
                self._file_list.append(file_name)
        # sort
        self._file_list = sorted(self._file_list)
        
            
  
    def close(self):
        self._close_file()

        
    def clear(self):
        self._close_file()
        self._file_counter = 0
        self._current_file = None
        self._current_file_name = None
        self._current_file_metadata = None
        self._current_file_event_counter= 0
        self._global_event_counter = 0


    def rewind(self):
        """
        Rewind to beginning of file(s)
        reopen....
        """
        
        
        # if multiple files -> close current file then reopen first file
        if len(self._file_list)>1:
            self._close_file()
            self._open_file(self._file_list[0])
    
        # initialize
        self._file_counter = 0
        self._current_file_event_counter = 0
        self._global_event_counter = 0




    def read_event(self, include_metadata=False, adc_name='adc1'):
        """
        Function to read next event
        """

        info = dict()
        array = []
        
        # check if files available
        if not self._file_list or len(self._file_list)==0:
            info['read_status'] = 1
            info['error_msg'] = 'No file available!'
            return array, info
          
        # open file if needed
        if self._current_file is None:
            self._open_file(self._file_list[self._file_counter])

            
        # check if there are more events
        if self._current_file_event_counter>=self._current_file_nb_events:

            # close 
            self._close_file()
            
            # check if there are more files
            if  self._file_counter>=len(self._file_list):
                info['read_status'] = 1
                info['error_msg'] = 'No more files available'
                return array, info
            else:
                self._open_file(self._file_list[self._file_counter])


            

        # check if file open (shouldn't happen)
        if self._current_file is None:
            info['read_status'] = 1
            info['error_msg'] = 'Problem reading next event. File closed!'
            return array, info
         

        # get dataset
        self._current_file_event_counter+=1
        dataset_name = 'event_' + str(self._current_file_event_counter)
        dataset = self._current_file[adc_name][dataset_name]

        # array
        dims = dataset.shape
        array = np.zeros((dims[0],dims[1]), dtype=np.int16)
        dataset.read_direct(array)
      

        # include info
        if include_metadata:
            info = self._extract_metadata(dataset.attrs)
            info.update(self._extract_metadata(self._current_file.attrs))
            info.update(self._extract_metadata(self._current_file[adc_name].attrs))
                    
        info['read_status'] = 0
        info['error_msg'] = ''

        return array, info
              


    def read_single_event(self, event_index, file_name=None, include_metadata=False,
                          adc_name='adc1'):
        """
        Read a single event
        """

        #  set file list
        if file_name is not None:
            self.set_files(file_name)
            
        # open file if needed 
        if self._current_file is None:
            self._open_file(self._file_list[0])

        # dataset
        dataset_name = 'event_' + str(event_index)
        dataset = self._current_file[adc_name][dataset_name]
        
        # array
        dims = dataset.shape
        array = np.zeros((dims[0],dims[1]), dtype=np.int16)
        dataset.read_direct(array)
      
        # metadata
        if include_metadata:
            info = self._extract_metadata(dataset.attrs)
            info.update(self._extract_metadata(self._current_file.attrs))
            info.update(self._extract_metadata(self._current_file[adc_name].attrs))
            info['read_status'] = 0
            info['error_msg'] = ''
            return array, info
              
        return array





    
    
    def read_many_events(self, filepath=None, nevents=0, output_format=1,
                         detector_chans=None,
                         event_nums=None, series_nums=None,
                         include_metadata=False,
                         adctovolt=False, adctoamp=False,
                         baselinesub=False, baselineinds=None,
                         memory_limit=2, adc_name='adc1'):
        """
        Read multiple events (default read all events in dump)
        
        Args:
          filepath: string or list  of strings
               file/path or list of files/paths (default: use current file)
          
          nevents: integer
               number of events to read  (default nb_events=0 -> all events in dumps)

          output_format: integer
               1: list of 2D ndarray[chan, samples]
               2: 3D ndarray[event, chan, samples]
 
          detector_chans: string/int or list of string/int
               detector channel name (example 'Z1PAS1', 'PD2', or 1) following format in setup.ini file
               If none, all channels available 

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
          


        Return:
         
        """
        
        # ===============================
        # Check arguments
        # ===============================

        #  set file list
        if filepath is not None:
            self.set_files(filepath)
        elif self._current_file is None:
            raise ValueError('ERROR: No file selected!')
        

        # detector/channel
        if detector_chans is not None and not (isinstance(detector_chans, list) or
                                               isinstance(detector_chans, np.ndarray)):
            detector_chans = [detector_chans]
    

        # series nums
        if series_nums is not None:
            if not isinstance(series_nums, list) and not isinstance(series_nums, np.ndarray):
                series_nums = [series_nums]

        # event nums: create dump number list, convert event_nums to list of tuple
        dump_nums = None
        event_tuple_nums = None
        if event_nums is not None:

            # convert to list if not array/list
            if not isinstance(event_nums, list) and not isinstance(event_nums, np.ndarray):
                event_nums = [event_nums]
                
            if series_nums is not None and  len(event_nums) != len(series_nums):
                raise ValueError('ERROR: series_nums and event_nums need to be same length!')

            dump_nums = list()
            event_tuple_nums = list()
            for ievent in range(len(event_nums)):
                event_num = event_nums[ievent]
                dump_num = int(event_num/100000)
                if dump_num == 0:
                    raise ValueError('ERROR: Unexpected event number format!' +
                                     ' Required format = "dump_num*100000+event_index"')
                dump_nums.append(dump_num)
                event_tuple_nums.append((event_num,))
            event_nums = event_tuple_nums

     
        # ===============================
        # Preliminary raw data checks
        # using metadata
        # ===============================
        nb_events_tot = 0
        nb_channels = 0
        nb_samples = 0
        array_indices = list()
        selected_file_list = list()
              
        # loop files
        for file_name in self._file_list:

                      
            # get metadata
            metadata = self.get_metadata(file_name)
            adc_metadata = metadata['groups'][adc_name]

            # extract series number
            file_series_num = None
            if 'series_num' in metadata:
                file_series_num = metadata['series_num']
            else:
                file_series_num = extract_series_num(file_name)

            if series_nums is not None and file_series_num is None:
                raise ValueError('ERROR: unable to get series number!')
            
            # extract dump number
            file_dump_num = None
          
            if 'dump_num' in metadata:
                file_dump_num = int(metadata['dump_num'])
            else:
                file_dump_num = extract_dump_num(file_name)

            if dump_nums is not None and file_dump_num is None:
                raise ValueError('ERROR: unable to get dump number!')
            
            
            # skip files that are not needed
            if series_nums is not None and file_series_num not in series_nums:
                continue
            if dump_nums is not None and file_dump_num not in dump_nums:
                continue

        
            # if event_nums:  check file if available and store it
            if event_nums is not None:

                keep_file = False
                for ievent in range(len(event_nums)):

                    # check if dump number match current file
                    dump_num =  dump_nums[ievent]
                    if dump_num != file_dump_num:
                        continue

                    # check series match current file
                    if series_nums is not None:
                        series_num = series_nums[ievent]
                        if series_num != file_series_num:
                            continue
                        
                    # Found file!
                    keep_file  = True

                    # check index available
                    event_num = event_nums[ievent][0]
                    even_index = int(event_num % 100000)
                    if even_index>int(adc_metadata['nb_events']):
                        raise ValueError('ERROR: Find file for event number '
                                         + str(event_num) + ' however, event does not exist!')
                    
                    # store in list as a tuple
                    event_nums[ievent] = event_nums[ievent] + (file_name,)
                    if len(event_nums[ievent])>2:
                        raise ValueError('ERROR: Multiple files found for event number '
                                         + str(event_num)
                                         + '! You may need to add "series_nums" argument!')
                    
                    nb_events_tot += 1
                    

                # continue file loop if not needed
                if not keep_file :
                    continue

            else:
                nb_events_tot += adc_metadata['nb_events']
                if nevents>0  and nb_events_tot>=nevents:
                    nb_events_tot = nevents
                selected_file_list.append(file_name)

            
            # channels
            array_indices_file = list()
            nb_channels_file = adc_metadata['nb_channels']
            
            if detector_chans is not None:
                              
                # available adc channels  
                adc_chan_list = adc_metadata['adc_channel_indices']
                if not isinstance(adc_chan_list, list) and not isinstance(adc_chan_list, np.ndarray):
                    adc_chan_list = np.array([adc_chan_list])
                    

                # connections
                connections = self.get_connection_dict(adc_name=adc_name, metadata=metadata)
                                
                # loop channels
                chan_counter = 0
                for chan_name in connections['detector_chans']:
                    if chan_name in detector_chans:
                        chan_adc = int(connections['adc_chans'][chan_counter])
                        if chan_adc in adc_chan_list:
                            ind = np.where(adc_chan_list==chan_adc)[0]
                            if len(ind)==1:
                                array_indices_file.append(int(ind))
                            else:
                                raise ValueError('Problem with raw data..')
                    chan_counter+=1
                            
                nb_channels_file = len(array_indices_file)
                if (nb_channels_file==0):
                    error_msg = 'Unable to find selected channel(s). Check connection table!'
                    if self._raise_errors:
                        raise ValueError(error_msg)
                    else:
                        print('ERROR: ' + error_msg)
                        if include_metadata:
                            return [],[]
                        else:
                            return []
                else:
                    array_indices_file.sort()

            else:
                array_indices_file = list(range(nb_channels_file))

            if nb_channels==0:
                nb_channels =  nb_channels_file
                
            if not array_indices:
                array_indices = array_indices_file
            
                
            # check channel consistency
            if array_indices!=array_indices_file:
                error_msg = 'Unable to return arrray due to inconsistent list of channels between files!'
                if self._raise_errors:
                    raise ValueError(error_msg)
                else:
                    print('ERROR: ' + error_msg)
                    if include_metadata:
                        return [],[]
                    else:
                        return []


            # number of samples
            nb_samples_file = adc_metadata['nb_samples']   
            if nb_samples==0:
                nb_samples =  nb_samples_file
            elif  output_format!=1 and nb_samples_file!=nb_samples:
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
            if nevents>0  and nb_events_tot>=nevents:
                break
            
                    
        # clear
        self.clear()


        # check bumber of events
        if nb_events_tot == 0:
            raise ValueError('ERROR: No events found!')
        

        

        # selected events
        selected_event_nums = None
        if event_nums is not None:

            selected_event_nums = list()
            for event in event_nums:
                if len(event)==2:
                    selected_event_nums.append(event)
                    
            if len(selected_event_nums)!=nb_events_tot:
                raise ValueError('ERROR: inconsistent number of events! Possible bug in the code...')
                
            if nb_events_tot<len(event_nums):
                print('WARNING: Only ' + str(nb_events_tot) + ' events out of '
                      + str(len(event_nums)) + ' have been found!')
            
        else:
            # refresh file list
            self.set_files(selected_file_list)
            
        
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
            print('WARNING: Max number events based on memory limit of ' + str(memory_limit) + 'GB is ' +
                  str(nb_events_tot_temp) + ' out of ' + str(nb_events_tot) +'!')
            nb_events_tot = nb_events_tot_temp




            
        # ===============================
        #  Initialize output
        # ===============================
                   
        output_data = list()
        info_list = list()
     
        if output_format==2:
            if adctovolt or adctoamp or baselinesub:
                output_data = np.zeros((nb_events_tot, nb_channels, nb_samples), dtype=np.float64)
            else:
                output_data = np.zeros((nb_events_tot, nb_channels, nb_samples), dtype=np.int16)


                
        # ===============================
        #  Loop and read events
        # ===============================
        
        for ievent in range(nb_events_tot):
            
            # read event
            traces_int = []
            info = dict()

            if selected_event_nums is None:
                traces_int, info = self.read_event(include_metadata=True)
            else:
                event_index = int(selected_event_nums[ievent][0] % 100000)
                file_name = selected_event_nums[ievent][1]
                traces_int, info = self.read_single_event(event_index, file_name=file_name,
                                                         include_metadata=True)


            # check if reading error
            if info['read_status']>0:
                print('WARNING: Unable to read event #' + str(ievent) + '! Error message: ')
                print('WARNING: "' + info['error_msg'] + '". Stopping event loop')
                break
                
                
            # add connections to metadata
            connections = self.get_connection_dict(adc_name=adc_name, metadata=info)
            info['detector_chans'] = [connections['detector_chans'][i] for i in array_indices]
            info['tes_chans'] = [connections['tes_chans'][i] for i in array_indices]
            info['controller_chans'] = [connections['controller_chans'][i] for i in array_indices]
            
            # detector settings
            detector_config = self.get_detector_config()
            info['detector_config'] = dict()
            for det in info['detector_chans']:
                info['detector_config'][det] = detector_config[det]


            # add to metadata list
            if include_metadata:
                info_list.append(info)


            # reshape with only selected events
            if len(array_indices)!=traces_int.shape[0] and array_indices:
                traces_int = traces_int[array_indices,:]

            
            # convert to volt
            traces = []
            if adctovolt or adctoamp:
                traces = np.zeros_like(traces_int, dtype=np.float64)
                for ichan in range(traces_int.shape[0]):
                    icoeff = ichan
                    if array_indices:
                        icoeff = array_indices[ichan]
                    cal_coeff = info['adc_conversion_factor'][icoeff][::-1]
                    poly = np.poly1d(cal_coeff)
                    traces[ichan,:] = poly(traces_int[ichan,:])
            else:
                traces = traces_int 
                    
            # convert to amps
            if adctoamp:
                if detector_config is None:
                    raise ValueError('ERROR: Unable to convert to amps. No detector config available!')
                for ichan in range(traces.shape[0]):
                    det = info['detector_chans'][ichan]
                    if 'close_loop_norm' in detector_config[det]:
                        traces[ichan,:] = traces[ichan,:]/detector_config[det]['close_loop_norm']
                    else:
                        raise ValueError('ERROR: Unable to convert to amps. No normalization available for ' + det)



            
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
                    raise ValueError('ERROR: Unable to find baseline start/stop. Add argument "baselineinds"')

                traces = traces - np.mean(traces[:,baseline_start:baseline_stop], axis=-1, keepdims=True)
            
                
            
            # store
            if (output_format==1 or output_format==3):
                output_data.append(traces)
            else:
                output_data[ievent,:,:] = traces
                
          
        if include_metadata:
            return output_data, info_list

        return output_data
        
        
        
            
            
        

    def get_current_file_name(self):
        return self._current_file_name
        


    
    def get_metadata(self, file_name=None, group_name=None, dataset_name=None, 
                     include_dataset_metadata=False):

        """
        Function to get metadata.
       
        Args:
          
          file_name: string (optional)
             if no file name provided: use current file

          group_name:  string 
             H5 "Group" name
          
          dataset_name: string 
             H5 "Dataset" name
         
        Returns:
          metadata: dict
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
        if file_name is not None and self._current_file_name != file_name:
            
            # check if a file already open
            if self._current_file is not None:
                self._close_file()
            # open
            self._open_file(file_name, load_metadata=False)
            

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


        # convert to list if only one channel
        for config in detector_config_dict:
            param = detector_config_dict[config]
            if not isinstance(param, list) and not isinstance(param, np.ndarray):
                detector_config_dict[config] = [detector_config_dict[config]]
    

        # add detector/channel list from adc metadata, needs to match
        # detector settings array order
        tes_chans = list()
        detector_chans = list()
        controller_chans = list()
        connection_dict = self.get_connection_dict(adc_name=adc_name, metadata=metadata)

        if connection_dict:
            chan_list = detector_config_dict['channel_list']
            if not isinstance(chan_list, np.ndarray) and not isinstance(chan_list, list):
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


        # convert to dictionary
        detector_config = dict()
        nb_chan = len(detector_config_dict['detector_chans'])
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
                    name_val_list, name_list, val_list  = connection_utils.extract_adc_connection(list(val))
                    val_list  = [adc_id,adc_chan] + val_list
                    name_list = ['adc_id','adc_channel'] + name_list
                    connection_list.append(val_list)
                    if not connection_name_list:
                        connection_name_list = name_list
                    elif connection_name_list!=name_list:
                        print('ERROR: missing adc connection values!')
                        
                    
        connection_table = pd.DataFrame(connection_list, columns = connection_name_list )
        return connection_table


    
  

    def _open_file(self, file_name, rw_string='r', load_metadata=True):
        """
        open file 
        """
        if self._current_file is not None:
            self._close_file()
            
        file = None
        try:
            file = h5py.File(file_name,rw_string)
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
            
            # check events
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
        return True
        
        
            
    

    def _close_file(self):

        if self._current_file is not None:
            self._current_file.close()
  
        # initialize
        self._current_file = None
        self._current_file_name = None
        self._current_file_metadata = None
        self._current_file_nb_events = 0
                            
        
        



    def _load_metadata(self, include_dataset_metadata=False):

        """
        Function to load all metadata from current file. Store in 
        an internal dictionary
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
                    metadata_dict['groups'][key]['datasets'][dataset_key] = self._extract_metadata(dataset.attrs)
                    

                        

        # save
        self._current_file_metadata = metadata_dict
     






    def _extract_metadata(self, attributes):   
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
        self._global_event_counter = 0
         
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
             

def getrandevents(basepath, evtnums, seriesnums, cut=None, channels=None,
                  sumchans=False, lgcplot=False, ntraces=1, nplot=20,
                  seed=None, indbasepre=None):
    """
    Function for loading (and plotting) random events from a datasets.
    Has functionality to pull randomly from a specified cut.

    Parameters
    ----------
    basepath : str
        The base path to the directory that contains the folders that
        the event dumps are in. The folders in this directory should be
        the series numbers.
    evtnums : array_like
        An array of all event numbers for the events in all datasets.
    seriesnums : array_like
        An array of the corresponding series numbers for each event
        number in evtnums.
    cut : array_like, optional
        A boolean array of the cut that should be applied to the data.
        If left as None, then no cut is applied.
    channels : list, optional
        A list of strings that contains all of the channels that should
        be loaded. If left as None, all channels are loaded.
    sumchans : bool, optional
        A boolean flag for whether or not to sum the channels when
        plotting. If False, each channel is plotted individually.
        Default is False.
    ntraces : int, str, optional
        The number of traces to randomly load from the data (with the
        cut, if specified). If all traces from a specfied cut are
        desired, pass the string "all". Default is 1.
    lgcplot : bool, optional
        Logical flag on whether or not to plot the pulled traces.
    nplot : int, optional
        If lgcplot is True, the number of traces to plot.
    seed : int, optional
        A value to pass to np.random.seed if the user wishes to use
        the same random seed each time getrandevents is called.
    indbasepre : NoneType, int, optional
        The number of indices up to which a trace should be averaged to
        determine the baseline. This baseline will then be subtracted
        from the traces when plotting. If left as None, no baseline
        subtraction will be done.

    Returns
    -------
    t : ndarray
        The time values for plotting the events.
    x : ndarray
        Array containing all of the events that were pulled.
    crand : ndarray
        Boolean array that contains the cut on the loaded data.

    """

    if seed is not None:
        np.random.seed(seed)

    if isinstance(channels, str):
        channels = [channels]

    if not isinstance(evtnums, pd.Series):
        evtnums = pd.Series(data=evtnums)
    if not isinstance(seriesnums, pd.Series):
        seriesnums = pd.Series(data=seriesnums)

    if cut is None:
        cut = np.ones(len(evtnums), dtype=bool)

    if np.sum(cut) == 0:
        raise ValueError(
            "The inputted cut has no events, cannot load any traces."
        )

    if ntraces == 'all' or ntraces > np.sum(cut):
        ntraces = np.sum(cut)
        if ntraces > 1000:
            warnings.warn(
                "You are loading a large number of traces "
                f"({ntraces}). Be careful with your RAM usage."
            )

    inds = np.random.choice(
        np.flatnonzero(cut),
        size=ntraces,
        replace=False,
    )

    crand = np.zeros(len(evtnums), dtype=bool)
    crand[inds] = True

    h5_reader = H5Reader()

    first_file = sorted(glob(f'{basepath}/**/*.hdf5', recursive=True))[0]

    if channels is None:
        connection_dict = h5_reader.get_connection_dict(
            file_name=first_file,
        )
        channels = connection_dict['detector_chans']

    fs_list = []
    metadata = h5_reader.get_metadata(file_name=first_file)
    for label in metadata['group_list']:
        fs_list.append(metadata['groups'][label].get('sample_rate'))

    fs = np.unique(list(filter(None, fs_list)))[0]

    arr, metadata = h5_reader.read_many_events(
        filepath=glob(f'{basepath}/*'),
        event_nums=np.asarray(evtnums[cut & crand]),
        series_nums=np.asarray(seriesnums[cut & crand]),
        output_format=2,
        include_metadata=True,
        detector_chans=channels,
        adctoamp=True,
    )

    if channels != metadata[0]['detector_chans']:
        chans = [metadata[0]['detector_chans'].index(ch) for ch in channels]
        x = arr[:, chans].astype(float)
    else:
        x = arr.astype(float)

    t = np.arange(x.shape[-1])/fs

    if lgcplot:
        if nplot>ntraces:
            nplot = ntraces

        for ii in range(nplot):

            fig, ax = plt.subplots(figsize=(10, 6))
            if sumchans:
                trace_sum = x[ii].sum(axis=0)

                if indbasepre is not None:
                    baseline = np.mean(trace_sum[..., :indbasepre])
                else:
                    baseline = 0

                ax.plot(t * 1e6, trace_sum * 1e6, label="Summed Channels")
            else:
                colors = plt.cm.viridis(
                    np.linspace(0, 1, num=x.shape[1]),
                    alpha=0.5,
                )
                for jj, chan in enumerate(channels):
                    label = f"Channel {chan}"

                    if indbasepre is not None:
                        baseline = np.mean(x[ii, jj, :indbasepre])
                    else:
                        baseline = 0

                    ax.plot(
                        t * 1e6,
                        x[ii, jj] * 1e6 - baseline * 1e6,
                        color=colors[jj],
                        label=label,
                    )
            ax.grid()
            ax.set_ylabel("Current [μA]")
            ax.set_xlabel("Time [μs]")
            ax.set_title(
                f"Pulses, Evt Num {evtnums[crand].iloc[ii]}, "
                f"Series Num {seriesnums[crand].iloc[ii]}"
            )
            ax.legend()

    return t, x, crand
  
