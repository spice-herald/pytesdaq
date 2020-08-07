import h5py
import re
import numpy as np
import pandas as pd
from glob import glob
from pytesdaq.utils import connection_utils

class H5Core:
    
    def __init__(self):

        # list of files
        self._file_list = list()


        # current file  info
        self._current_file = None
        self._current_file_name = None
        self._current_file_metadata = dict()
        self._current_file_nb_events = 0
        
       
        # event counter
        self._event_counter= 0
         
        # file counter
        self._file_counter = 0
        
    
    def set_files(self,files):
        """
        Set file namelist

        Args:
          list of file name (list string)  
          OR single file name (string)
        """
        
        self.clear()
        
        if isinstance(files, str):
            files = [files]
        self._file_list  = files

        # fixeme: check files?

  
    def close(self):
        self._close_file()

        
    def clear(self):
        self._close_file()
        self._event_counter= 0
        self._file_counter = 0
        self._file_list = list()



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
        self._event_counter= 0




    def read_event(self,include_metadata=False,adc_name='adc1'):
        """
        Function to read next event
        """

        # check if files available
        if not self._file_list or len(self._file_list)==0:
            error_msg = 'No file available!'
            return error_msg,error_msg
          
        # open file if needed
        if self._current_file is None:
            self._open_file(self._file_list[self._file_counter])

        # check if there are more events
        if self._event_counter>=self._current_file_nb_events:
            
            # close 
            self._close_file()
            
            # check if there are more files
            if  self._file_counter>=len(self._file_list):
                error_msg = 'No more events in the file!'
                return error_msg,error_msg
            else:
                self._open_file(self._file_list[self._file_counter])


        # check if file open (shouldn't happen)
        if self._current_file is None:
            error_msg = 'Problem reading next event. File closed!'
            return error_msg, error_msg


        # get dataset
        event_id = self._event_counter+1
        dataset_name = 'event_'+str(event_id)
        dataset = self._current_file[adc_name][dataset_name]

        # array
        dims = dataset.shape
        array = np.zeros((dims[0],dims[1]), dtype=np.int16)
        dataset.read_direct(array)
         
        # counter
        self._event_counter+=1


        # include info
        if include_metadata:
            info = self._extract_metadata(dataset.attrs)
            info.update(self._extract_metadata(self._current_file[adc_name].attrs))
            return array,info
              
        return array

        


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

            
        # open file if needed
        if file_name is not None and self._current_file_name != file_name:
            
            # check if file already open
            if self._current_file is not None:
                print('ERROR: Please close current file first using  "close()"')
                return
            else:
                self._open_file(file_name, load_metadata=False)

        elif self._current_file is None:
            print('ERROR: No file currently open and no "file_name" argument not provided!')
            print('Please open a file or provide a file name!')
            return
            

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
        
       

        return metadata
            



    def get_detector_config(self, file_name=None):   
        """
        Get detector configuration
        """
        
        detector_config = dict()
        
        # get metadata
        metadata = self.get_metadata(file_name=file_name)
        

        # loop detector config group
        for group_key in metadata['group_list']:
            if group_key[0:9]=='detconfig':
                group_metadata = metadata['groups'][group_key]
                adc_id = 'adc' + group_key[10:]
                if 'adc_name' in group_metadata:
                    adc_id = group_metadata['adc_name']
                detector_config[adc_id] = group_metadata
                
        return detector_config




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
            print('ERROR: unable to open file')
            return

        self._current_file = file
        self._current_file_name = file_name


        # load metadata
        if load_metadata:

            self._load_metadata()
            
            # check events
            self._current_file_nb_events = 0
            if 'adc_list' not in self._current_file_metadata:
                print('WARNING: No ADC information found in the file')
                return

            for adc_name in self._current_file_metadata['adc_list']:
                nb_events = self._current_file_nb_events = self._current_file_metadata['groups'][adc_name]['nb_datasets']
                if self._current_file_nb_events==0:
                    self._current_file_nb_events = nb_events
                elif self._current_file_nb_events!=nb_events:
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
        


   
