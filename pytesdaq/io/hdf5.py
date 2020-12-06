import h5py
import re
import os
import numpy as np
import pandas as pd
from glob import glob
from pytesdaq.utils import connection_utils



class H5Reader:
    
    def __init__(self, raise_errors=True, verbose=True):


        self._raise_errors = raise_errors
        self._verbose = verbose
        
        # list of files
        self._file_list = list()
        

        # current file  info
        self._current_file = None
        self._current_file_name = None
        self._current_file_metadata = dict()
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
            if filepaths.find('.hdf5')==-1:
                filepaths = filepaths + '.hdf5'
            filepaths = [filepaths]

        # loop file/path list
        for filepath in filepaths:
            
            if os.path.isdir(filepath):
                self._file_list.extend(glob(filepath+'/*.hdf5'))
            elif os.path.isfile(filepath):
                self._file_list.append(filepath)
            
        if not self._file_list:
            if self._raise_errors:
                raise ValueError('No files found!')
            else:
                print('ERROR: No files found!')
                return
        else:
            self._file_list = sorted(self._file_list)
            
            
  
    def close(self):
        self._close_file()

        
    def clear(self):
        self._close_file()
        self._file_counter = 0
        self._current_file = None
        self._current_file_name = None
        self._current_file_metadata = dict()
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
        
        # check if files available
        if not self._file_list or len(self._file_list)==0:
            error_msg = 'No file available!'
            return error_msg, error_msg
          
        # open file if needed
        if self._current_file is None:
            self._open_file(self._file_list[self._file_counter])

            
        # check if there are more events
        if self._current_file_event_counter>=self._current_file_nb_events:

            # close 
            self._close_file()
            
            # check if there are more files
            if  self._file_counter>=len(self._file_list):
                error_msg = 'No more events in the file!'
                return error_msg, error_msg
            else:
                self._open_file(self._file_list[self._file_counter])


            

        # check if file open (shouldn't happen)
        if self._current_file is None:
            error_msg = 'Problem reading next event. File closed!'
            return error_msg, error_msg


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
            info.update(self._extract_metadata(self._current_file[adc_name].attrs))
            return array, info
              
        return array


    
    def read_many_events(self, filepath=None, nevents=0,
                         output_format=1,
                         include_metadata=False,
                         adc_name='adc1',
                         detector_chans=None,
                         adctovolt=False,
                         memory_limit=2):
        """
        Read multiple events (default read all events in dump)
        
        Args:
          filepath: string or list  
               file/path or list of files/paths (default: use current file)
          
          nevents: integer
               number of events to read  (default nb_events=0 -> all events in dumps)

          output_format: integer
               1: list of 2D ndarray[chan, samples]
               2: 3D ndarray[event, chan, samples]
               3: data frame 

          include_metadata: bool 
               include file/group/dataset metadata (default = False)


          adc_name: string
              ADC id (default: 'adc1')
          

          detector_chans: string/int or list of string/int
               detector channel name (example 'Z1PAS1', 'PD2', or 1) following format in setup.ini file
               If none, all channels available 

          adctovolt: Bool
               Convert  from ADC to volt (Default=False) 
          
          memory_limit: Float
               Pulse data memory limit in GB

 


        Return:
         
        """
        
        # ---------------------
        # Check arguments
        # Set file lists
        # --------------------

        #  set file list
        if filepath is not None:
            self.set_files(filepath)


        # detector/channel
        if detector_chans is not None and not isinstance(detector_chans,list):
            detector_chans = [detector_chans]


                 
        # ---------------------
        # Check data, output
        # dimension
        # --------------------
        nb_events_tot = 0
        nb_channels = 0
        nb_samples = 0
        array_indices = list()

        # loop files
        for file in self._file_list:

            
            metadata = self.get_metadata(file)
            adc_metadata = metadata['groups'][adc_name]
            
            # channels
            array_indices_file = list()
            nb_channels_file = adc_metadata['nb_channels']
            
            if detector_chans is not None:
                              
                # available adc channels  
                adc_chan_list = adc_metadata['adc_channel_indices']
                if not isinstance(adc_chan_list,list):
                    adc_chan_list = [adc_chan_list]

                # connections
                connections = self.get_connection_dict(adc_name=adc_name, metadata=metadata)

                # loop
                channel_counter = 0
                for channel in connections['detector_chans']:
                    if channel in detector_chans:
                        chan_adc = int(connections['adc_chans'][channel_counter])
                        if chan_adc in adc_chan_list:
                            array_indices_file.append(adc_chan_list.index(chan_adc))
                    
                            
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

            
            # nb events
            nb_events_tot += adc_metadata['nb_events']

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
                nb_events_tot = nevents
                break


        # clear
        self.clear()

        
        # ---------------------
        # Memory check
        # --------------------

        
        sample_bytes = 2
        if adctovolt:
            sample_bytes = 8
            
        output_memory_per_event = sample_bytes*nb_samples*nb_channels/1e9
        output_memory = nb_events_tot*output_memory_per_event
        if output_memory>memory_limit:
            nb_events_tot_temp = int(round(memory_limit/output_memory_per_event))
            print('WARNING: Max number events based on memory limit of ' + str(memory_limit) + 'GB is ' +
                  str(nb_events_tot_temp) + ' out of ' + str(nb_events_tot) +'!')
            nb_events_tot = nb_events_tot_temp

    
        # ---------------------
        # Initialize output
        # --------------------
              
        output_data = list()
        info_list = list()
     
        if output_format==2:
            if adctovolt:
                output_data = np.zeros((nb_events_tot,nb_channels,nb_samples),dtype=np.float64)
            else:
                output_data = np.zeros((nb_events_tot,nb_channels,nb_samples),dtype=np.int16)
            
        

        # ---------------------
        # Loop and read events
        # --------------------
        for ievent in range(nb_events_tot):
            
            # read event
            array_int, info = self.read_event(include_metadata=True)

            # add connections to metadata
            connections = self.get_connection_dict(adc_name=adc_name, metadata=info)
            info['detector_chans'] = [connections['detector_chans'][i] for i in array_indices]
            info['tes_chans'] = [connections['tes_chans'][i] for i in array_indices]
            info['controller_chans'] = [connections['controller_chans'][i] for i in array_indices]
            
            
            if include_metadata:
                info_list.append(info)
            
                
            # check if reading error
            if isinstance(array_int, str):
                break


            # reshape with only selected events
            if len(array_indices)!=array_int.shape[0] and array_indices:
                array_int = array_int[array_indices,:]

            
            # convert to volt
            array = []
            if adctovolt:
                array = np.zeros_like(array_int, dtype=np.float64)
                for ichan in range(array_int.shape[0]):
                    icoeff = ichan
                    if array_indices:
                        icoeff = array_indices[ichan]
                    cal_coeff = info['adc_conversion_factor'][icoeff][::-1]
                    poly = np.poly1d(cal_coeff)
                    array[ichan,:] = poly(array_int[ichan,:])
            else:
                array = array_int 
                    
            
            
            # store
            if (output_format==1 or output_format==3):
                output_data.append(array)
            else:
                output_data[ievent,:,:] = array
                
          
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

        if not self._current_file_metadata or include_dataset_metadata:
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
            



    def get_detector_config(self, file_name=None, adc_name='adc1',
                            use_chan_dict=True):   
        """
        Get detector configuration
        """
        
        detector_config = dict()
        
        # get metadata
        metadata = self.get_metadata(file_name=file_name)
    

        # config name
        config_name = 'detconfig1'
        if adc_name!='adc1':
            config_name = 'detconfig' + adc_name[3:]

        # check if available
        if config_name not in metadata['group_list']:
            print('ERROR: unable to find detector config!')
            return []

        # group metadata
        detector_config_list = metadata['groups'][config_name]
        if 'adc_name' in detector_config_list and adc_name!=detector_config_list['adc_name']:
            print('ERROR: Unexpected detector configuration format!')
            return []


        # convert to list if only one channel
        for config in detector_config_list:
            if not isinstance(config, list):
                detector_config_list[config] = [detector_config_list[config]]
            

        # add detector/channel list from adc metadata, needs to match
        # detector settings array order
        tes_chans = list()
        detector_chans = list()
        controller_chans = list()
        connection_dict = self.get_connection_dict(adc_name=adc_name, metadata=metadata)

        if connection_dict:
            
            chan_list = detector_config_list['channel_list']
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
                         
                                
        detector_config_list['tes_chans'] =  tes_chans
        detector_config_list['detector_chans'] =  detector_chans
        detector_config_list['controller_chans'] =  controller_chans   


        # convert to dictionary
        detector_config = dict()
        if use_chan_dict and len(detector_config_list['detector_chans'])>0:
            chan_list = detector_config_list['detector_chans']
            for chan in chan_list:
                chan_index = detector_config_list['detector_chans'].index(chan)
                detector_config[chan] = dict()
                for config in detector_config_list:
                    detector_config[chan][config] = detector_config_list[config][chan_index]
        else:
            detector_config = detector_config_list
            
            
        
        
        
                
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


    

    def get_connection_table(self, file_name=None):
        """
        Get connection table
        """
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


    
  

    def _open_file(self,file_name, rw_string='r', load_metadata=True):
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
        self._current_file_metadata = dict()
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
        for key_name in list(self._current_file.keys()):
            
            # update list
            metadata_dict['group_list'].append(key_name)
            if key_name[0:3]=='adc':
                metadata_dict['adc_list'].append(key_name)
                    
            # get group 
            group = self._current_file[key_name]
            
            # save metadata
            metadata_dict['groups'][key_name] = dict()
            metadata_dict['groups'][key_name] =  self._extract_metadata(group.attrs)

            # datasets
            dataset_list = list(group.keys())
            metadata_dict['groups'][key_name]['dataset_list'] = dataset_list
            metadata_dict['groups'][key_name]['nb_datasets'] = len(dataset_list)
                

            if include_dataset_metadata and len(dataset_list)>0:
                    
                # Loop datasets and add metadata
                metadata_dict['groups'][key_name]['datasets'] = dict()
                for dataset_key_name in list(group.keys()):
                    dataset = group[dataset_key_name]
                    metadata_dict['groups'][key_name]['datasets'][dataset_key_name] = self._extract_metadata(dataset.attrs)
                    

                        

        # save
        self._current_file_metadata = metadata_dict
     






    def _extract_metadata(self,attributes):   
        metadata_dict = dict()
        for key in attributes.keys():
            value = attributes[key]
            if isinstance(value,bytes):
                value = value.decode()
            elif (isinstance(value,np.ndarray) and 
                  value.dtype=='object'):
                value = value.astype('str')
            metadata_dict[key] = value
        return metadata_dict
        

