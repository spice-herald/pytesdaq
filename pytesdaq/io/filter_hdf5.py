import os
import pandas as pd
import numpy as np
from pprint import pprint

__all__ = ['FilterH5IO']

class FilterH5IO:
    """
    Class to manage HDF5 filter file, which contains 
    noise PSD, template, and pre-calculated optimal filter
    quantities.

    The data are stored in the file as pandas Series or DataFrame. 
    Attibutes (metadata) can be included.

    Overall format of the filter file:
    /channel_name/parameter_name: pandas.Series or pandas.DataFrame 

    Note that parameter name with + (sum) and | (NxM) 
    are converted to natural naming with __plus__ and __and__ respectively

    """

    
    def __init__(self, filter_file, verbose=True):
        """
        Initialize class

        Parameters:
        ----------

        filter_file : str (required)
              filter file name (full path)
        verbose : Bool (optional)
              display informations (default = False)

        """

        self._filter_file = filter_file
        self._verbose = verbose


    @property
    def verbose(self):
        return self._verbose
        
    @verbose.setter
    def verbose(self,value):
        self._verbose=value
        
       
    def set_filter_file(self, file_name):
        """
        Set filter file name 
 
        Parameters:
        ----------

        filter_file : str (required)
              filter file name (full path)
        
        Return:
        ------
        None

        
        """
        self._filter_file  = file_name
        

    def describe(self):
        """
        Display informations about the file content
        
        Parameters:
        ----------
        None


        Return:
        ------
        None

        """

        filter_file = pd.HDFStore(self._filter_file)

        msg_title = 'Filter file: ' + self._filter_file + ':'
        print(msg_title)
        sep = '='
        for i in range(len(msg_title)):
            sep += '='
        print(sep + '\n')

        # loop keys
        for key in filter_file.keys():
            
            # modify key to have  "natural naming"
            key_name = self._convert_from_natural_naming(key)
                    
            msg = key_name + ':  '
            
            val = filter_file[key]
            if isinstance(val, pd.Series):
                msg += 'pandas.Series '
            elif  isinstance(val, pd.DataFrame):
                msg += 'pandas.DataFrame '
            else: 
                msg += str(type(val))

            msg += str(val.shape)
                
            if 'metadata' in filter_file.get_storer(key).attrs:
                msg += ('\n     metadata: '
                        + str(filter_file.get_storer(key).attrs.metadata)
                        + '\n')
                
            print(msg)
            
        filter_file.close()
        
               
    
    def get_param(self, channel, param_name,
                  add_metadata=False):
        """
        Get parameter  and associated metadata (optional) for the specified 
        channel. Return pandas Series or Dataframe or 2D/3D numpy array

        
        Parameters:
        ----------
        
        channel : str (required)
             channel name

        param_name : str (required)
             parameter name 
        
        add_medatata: bool (optional, default=False)
             if True, return metadata

        
        Return:
        ------
        
        value : pandas Series or DataFrame or 2D/3D numpy array
             parameter values
       
        metadata : dict  (if add_metadata=True)
             Metadata associated with parameter
        """

        # key name 
        key = '/' + channel + '/' + param_name
        
        # check if available
        val = None
        metadata = None
        if self._is_key(key):
            val, medatata = self._get(key)
            if (isinstance(val, pd.DataFrame)
                and metadata and 'type' in metadata):
                if metadata['type'] == '2darray':
                    val = val.values

        elif self._is_key(f'{key}_slice_0'):
            _, medatata = self._get(f'{key}_slice_0')
            dfs  = []
            for i in range(medatata['nb_slices']):
                df, _ =  self._get(f'{key}_slice_{i}')
                dfs.append(df.values)
            val =  np.stack(dfs, axis=0)

        else:
            raise ValueError(f'ERROR: parameter {param_name} for '
                             f'channel {channel} not found in hdf5 '
                             f'file {self._filter_file}')
                
        if add_metadata:
            return val, medatata
        else:
            return val


    
    def save_param(self, channel, param_name, param_value,
                   param_index=None, attributes=None,
                   overwrite=False):
        """
        Save parameter values, index, 
        and associated metadata for the specified channel

        
        Parameters:
        ----------
        
        channel : str (required)
             channel name

        param_name : str (required)
             parameter name 

        param_value : numpy array or pandas Series/DataFrame (required)
             values of the parameter (numpy arrays are converted to pandas)

        param_index : 1D numpy array (optional, default=None)
             index of the parameter (if param_value is a 1D numpy array)

        attributes : dict (optional, default=None)
             metadata associated with parameter

        overwrite : bool (optional, default=False)
             overwrite existing parameter in filter file (other parameters are unmodified)

        Return:
        ------

        None

        """

        # attributes
        if attributes is None:
            attributes = dict()
        
             
        # convert to series or dataframe(s)
        param_value_sliced = dict()
        if isinstance(param_value, np.ndarray):
            
            if param_value.ndim == 1:
                param_value = pd.Series(param_value, param_index)
                attributes['type'] = 'series'
            elif param_value.ndim == 2:
                param_value = pd.DataFrame(param_value)
                attributes['type'] = '2darray'
            elif param_value.ndim == 3:
                attributes['type'] = '3darray'
                attributes['nb_slices'] = param_value.shape[0]
                for i in range(param_value.shape[0]):
                    df = pd.DataFrame(param_value[i, :, :])
                    slice_name = f'{param_name}_slice_{i}'
                    param_value_sliced[slice_name] = df
                    
        elif isinstance(param_value, pd.Series):
            attributes['type'] = 'series'
        elif  isinstance(param_value, pd.DataFrame):
            attributes['type'] = 'dataframe'
        else:
            raise ValueError(f'ERROR: Parameter "{param_name}" '
                             f'should be eiter a numpy array'
                             f'or pandas Series/dataFrame')
        

        if param_value_sliced:
            for key_name, df in param_value_sliced.items():
                key = '/' + channel + '/' +  key_name
                self._put(key,
                          df,
                          attributes=attributes,
                          overwrite=overwrite)
        else:
            # key name
            key = '/' + channel + '/' + param_name
            self._put(key,
                      param_value,
                      attributes=attributes,
                      overwrite=overwrite)

            
    def save_fromdict(self, filter_dict, overwrite=False):
        """
        Save parameter from dictionary 
        
        Parameters:
        ----------
        
        filter_dict : dict (required)
            dictionary with following format:
              ['channel_name']
                  ['parameter_name']: array or pandas Series/DataFrame
                  ['parameter_name_metadata']: metadata dictionary
                  ...
              ['channel_name_2']
               ...

        overwrite : bool (optional, default=False)
             overwrite existing parameter(s) in filter file 


        Return:
        ------

        None


        """
        
        # loop filter data and save data
        for chan_name, chan_dict in filter_dict.items():

            # first get list of parameters
            param_name_list = list()
            for param_name in chan_dict.keys():
                if '_metadata' in param_name:
                    continue
                else:
                    param_name_list.append(param_name)


            # loop parameters and get value and metadata
            for param_name in param_name_list:
                
                # parameter value
                val = chan_dict[param_name]

                # parameter metadata
                metadata = None
                param_name_metadata = param_name + '_metadata'
                if param_name_metadata in chan_dict.keys():
                    metadata = chan_dict[param_name_metadata]

                # save
                self.save_param(chan_name, param_name, val,
                                attributes=metadata,
                                overwrite=overwrite)
                
                    

        
    def load(self):
        """
        Load filter file into dictionary

              
        Parameters:
        ----------
        
        None


        Return:
        -------

        filter_dict : dict
             dictionary with following format:
              ['channel_name']
                  ['parameter_name']: array or pandas Series/DataFrame
                  ['parameter_name_metadata']: metadata dictionary
                  ...
              ['channel_name_2']
               ...

           ['channel_name']
                ['parameter_name']: array or pandas Series/DataFrame
                ['parameter_name_metadata']: metadata dictionary
                ...

        """

        output_dict = dict()

        # open file and key list of keys
        filter_file = pd.HDFStore(self._filter_file)
        file_keys = filter_file.keys()
        filter_file.close()
                
        # loop keys to deal with sliced data
        list_of_keys = [] 
        for key in file_keys:

            pos = key.find('slice_')
            if pos != -1:
                key = key[0:pos-1]

            if key not in list_of_keys:
                list_of_keys.append(key)

        # loop and get dat
        for key in list_of_keys:
                        
            key = self._convert_from_natural_naming(key)
                        
            # split channel / parameter name             
            key_split = key.split('/')
            if len(key_split) != 3:
                continue

            # channel/par name 
            channel = key_split[1]
            param_name = key_split[2]

            # get value
            val, metadata = self.get_param(channel,
                                           param_name,
                                           add_metadata=True)

            
            # create channel dict if needed
            if channel not in output_dict:
                output_dict[channel] = dict()
                
            # fill value
            output_dict[channel][param_name] = val
            output_dict[channel][param_name + '_metadata'] =  metadata
                
        return  output_dict

        
    def _put(self, key, value, attributes=None, overwrite=False):
        """
        Save parameter in hdf5 file
        
        Parameters:
        ----------
        
        key : str (required)
             key name in the form of '/channel_name/parameter_name'

        value : pandas Series or DataFrame (required)
             parameter values

        attributes : dict (optional, default=None)
             metadata associated with parameter

        overwrite : bool (optional, default=False)
             overwrite existing parameter in filter file (other parameters are unmodified)


        Return:
        ------

        None
      
        """
        
        # open file
        filter_file = pd.HDFStore(self._filter_file)

        # verbose
        if self._verbose:
            print(f'INFO: Storing {key} in {self._filter_file}')

        # modify key to have  "natural naming"
        key_natural = self._convert_to_natural_naming(key)
                    
        # check if key exist already
        file_keys = filter_file.keys()
        if (key_natural in file_keys and not overwrite):
            raise ValueError(f'Key {key} already stored in '
                             f'{self._filter_file}. Use "overwrite=True" '
                             f'to overwrite parameter or '
                             f'change file name')

        # save
        filter_file.put(key_natural, value, format='fixed')

        # add attributes
        if attributes is not None:
            filter_file.get_storer(key_natural).attrs.metadata = attributes

        # close
        filter_file.close()


        
    def _get(self, key):
        """
      
        Get parameter fromhdf5 file
        
        Parameters:
        ----------
        
        key : str (required)
             key name in the form of '/channel_name/parameter_name'


        Return:
        ------
        
        value : pandas Series or DataFrame
            channel/parameter values
        
        metadata : dict
            metadata associated with parameter 
            (return None if no metadata available)

        """

        # open file
        filter_file = pd.HDFStore(self._filter_file)

        # modify key to have  "natural naming"
        key_natural = self._convert_to_natural_naming(key)
        
        # check key
        file_keys = filter_file.keys()
        
        if key_natural not in file_keys:
            raise ValueError(f'Key {key} is not in  '
                             f'{self._filter_file}. '
                             f'Check file with "describe()"')

        # get
        value = filter_file.get(key_natural)

        # get attributes
        metadata = None
        attributes = filter_file.get_storer(key_natural).attrs
        if 'metadata' in attributes:
            metadata = filter_file.get_storer(key_natural).attrs.metadata 

            
        # close
        filter_file.close()

        return value, metadata
    

    def _is_key(self, key):
        """
      
        Check if key in hdf5 file
        
        Parameters:
        ----------
        
        key : str (required)
             key name in the form of '/channel_name/parameter_name'


        Return:
        ------
        
        is_key : boolean
          True is key exist, False if key doesn't exist
        

        """

        # open file
        filter_file = pd.HDFStore(self._filter_file)


        # modify key to have  "natural naming"
        key_natural = self._convert_to_natural_naming(key)
        
        # check key
        file_keys = filter_file.keys()

        is_key = False
        if key_natural in file_keys:
            is_key = True


        # close
        filter_file.close()
            
        return is_key

    
    def _convert_to_natural_naming(self, key):
        """
        convert to natural naming
        = string containing only 
              ^[a-zA-Z_][a-zA-Z0-9_]*$
        """

        if '+' in key:
            key = key.replace('+', '__plus__')

        if '|' in key:
            key = key.replace('|', '__and__')
          
        return key

    def _convert_from_natural_naming(self, key):
        """
        convert from natural naming
        = string containing only 
              ^[a-zA-Z_][a-zA-Z0-9_]*$
        """

        if '__plus__' in key:
            key = key.replace('__plus__', '+')
        
        if '__and__' in key:
            key = key.replace('__and__', '|')
          
        return key





    # obsolete function
    def get_psd(self, channel, tag=None, fold=False,
                add_metadata=False):
            
        """
        OBSOLETE function
        """

        raise ValueError('ERROR: This function is obsolete! The more '
                         'general "get_param()" function can be used instead. '
                         'To ensure format compatibility with detprocess, best is to '
                         'use detprocess "FilterData" class for filter file I/O')
    
        
    def get_psd_series(self, channel,
                       tag=None,
                       fold=False,
                       add_metadata=False):
        """
        OBSOLETE
        """

        raise ValueError('ERROR: This function is obsolete! The more '
                         'general "get_param()" function can be used instead. '
                         'To ensure format compatibility with detprocess, best is to '
                         'use detprocess "FilterData" class for filter file I/O.')
    
        
    def get_template(self, channel, tag=None,
                     add_metadata=False):
        """
        OBSOLETE
        """

        raise ValueError('ERROR: This function is obsolete! The more '
                         'general "get_param()" function can be used instead. '
                         'To ensure format compatibility with detprocess, best is to '
                         'use detprocess "FilterData" class for filter file I/O')
            
    def get_template_series(self, channel, tag=None,
                            add_metadata=False):
        """
        OBSOLETE
        """
        raise ValueError('ERROR: This function is obsolete! The more '
                         'general "get_param()" function can be used instead. '
                         'To ensure format compatibility with detprocess, best is to '
                         'use detprocess "FilterData" class for filter file I/O')
            
    def plot_psd(self, channels, tag=None, fold=True, unit='pA'):
        """
        OBSOLETE
        """

        raise ValueError('ERROR: This function is obsolete! Use detprocess "FilterData" '
                         'class instead to plot psd')


    def save_psd(self, channel, psd, freq=None,
                 sample_rate=None, tag=None,
                 fold=False, attributes=None,
                 overwrite=False):
        """
        OBSOLETE
        """

        raise ValueError('ERROR: This function is obsolete! The more '
                         'general "save_param()" function can be used instead. '
                         'To ensure format compatibility with detprocess, best is to '
                         'use detprocess "FilterData" class for filter file I/O')
    
    def save_template(self, channel, template, template_time=None,
                      tag=None, attributes=None, overwrite=False):
        """
        OBSOLETE
        """

        raise ValueError('ERROR: This function is obsolete! The more '
                         'general "save_param()" function can be used instead. '
                         'To ensure format compatibility with detprocess, best is to '
                         'use detprocess "FilterData" class for filter file I/O')
    
