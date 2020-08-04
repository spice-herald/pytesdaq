import h5py
import numpy as np
import pandas as pd
from glob import glob


class H5Core:
    
    def __init__(self):

        # list of files
        self._file_list = list()


        # current file 
        self._current_file = None
        self._current_file_name = None
        self._current_file_adc_list= None
        self._current_file_nb_events = 0

        # event counter
        self._event_counter= 0
         
        # file counter
        self._file_counter = 0
        
    
    def set_files(self,files):
        """
        Set file name list

        Args:
          list of file name (list string)  or single file name (string)
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
        self._current_file = None
        self._current_file_name = None
        self._current_file_adc_list= None
        self._current_file_nb_events = 0
        self._event_counter= 0
        self._file_list = list()



    def rewind(self):

        self._close_file()
        
        # initialize
        self._file_counter = 0
        self._current_file = None
        self._current_file_name = None
        self._current_file_adc_list= None
        self._current_file_nb_events = 0
        self._event_counter= 0

        # open first file
        if self._file_list and len(self._file_list)>0:
            self._open_file(self._file_list[0])


    def read_event(self,include_metadata=False,adc_name='adc1'):
        """
        Function to read next event
        """

        # check if files available
        if not self._file_list or len(self._file_list)==0:
            error_msg = 'No file available!'
            return error_msg,error_msg
          
        # open file if needed
        if not self._current_file:
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
        if not self._current_file:
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
        

    def get_file_info(self,file_name=str(),group_name=str(),dataset_name=str()):
        """
        Function to get file metadata.
       
        Args:
          
          file_name: string (optional)
             if no file name provided: use current file
             if no file name and no current file, use file from file_list if only
             single file, otherwise return empty dictionary and display error
          
          group_name:  string (optional)
             H5 "Group" name
          
          dataset_name: string (optional)
              H5 "Dataset" name

        Returns:
          metadata: dict
             If no argument, returns all metadata (file,groups,datasets level)
        """


        if file_name:

            # check if file already open
            if (self._current_file and 
                (file_name  != self._current_file_name)):
                print('ERROR: Please close current file first using  "close()"')
                return
            else:
                self._open_file(file_name)

        elif self._current_file is None:
            
            # only open if single file 
            if len(self._file_list)==1:
                self._open_file(self._file_list[0])
            else:
                print('ERROR: File name not provided!')
                return
                
     
    

        return self._get_info(group_name=group_name,dataset_name=dataset_name)

    

    def _open_file(self,file_name, rw_string='r'):
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

        # get event info
        info = self._get_info()
        self._current_file_adc_list = list()
        self._current_file_nb_events = 0
        try:
            groups = info['group_list']
            adc_list = list()
            for group_name in groups:
                if group_name[0:3]=='adc':
                    datasets = info[group_name]['dataset_list']
                    self._current_file_adc_list.append(group_name)
                    nb_events = len(datasets)
                    if self._current_file_nb_events==0:
                        self._current_file_nb_events = nb_events
                    elif self._current_file_nb_events!=nb_events:
                        print('ERROR: Inconsistent number of events between ADC devices!')
                        self._close_file()
                        return False
            
        except:
            print('ERROR: Unable to find event list')
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
        self._current_file_adc_list= None
        self._current_file_nb_events = 0
        self._event_counter= 0

        
    def _get_info(self,group_name=str(),dataset_name=str()):
        """
        Function to get file metadata
       
        Args:
          group_name (optional): H5 "Group" name
          dataset_name (optional): H5 "Dataset" name

        Returns:
          Dictionary with metadata. If no argument, returns
          all metadata (file,groups,datasets level)
        """


        
        # initialize output
        output_dict = dict()
        
        if self._current_file is None:
            return  output_dict

            
        # Check what needs to be included
        include_file_metadata = True
        if group_name or dataset_name:
            include_file_metadata = False

        include_group_metadata = True
        if dataset_name:
            include_group_metadata = False
            

        # file metadata
        if include_file_metadata:
            output_dict = self._extract_metadata(self._current_file.attrs)
            output_dict['group_list'] = list()
 
        # groups
        for key_name in list(self._current_file.keys()):
            
            if (group_name and group_name!=key_name):
                continue
            
            if include_file_metadata:
                output_dict['group_list'].append(key_name)
                
            group = self._current_file[key_name]
            
            # group metadata
            if include_group_metadata:
                output_dict[key_name] = self._extract_metadata(group.attrs)
            else:
                output_dict[key_name] = dict()
                

            # loop dataset
            if not dataset_name:
                output_dict[key_name]['dataset_list'] = list()

            for dataset_key_name in list(group.keys()):
                
                if (dataset_name and dataset_name!=dataset_key_name):
                    continue

                if not dataset_name:
                    output_dict[key_name]['dataset_list'].append(dataset_key_name)

                dataset = group[dataset_key_name]
                dataset_dict = dict()
                dataset_dict[dataset_key_name] = self._extract_metadata(dataset.attrs)
                output_dict[key_name].update(dataset_dict)


        return output_dict



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
        


   
