import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pprint import pprint
from numpy.fft import fftfreq, rfftfreq

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

    Parameters calculated from the sum of multiple channels are stored
    with channel name = "channel_name_1__channel_name_2__..." 

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
            
            msg = key + ': '
            if '__plus__' in key:
                msg  = key.replace('__plus__', '+') + ': '
            elif '__' in key:
                msg = key.replace('__','|') + ': '
            
            val = filter_file[key]

            if isinstance(val, pd.Series):
                msg += 'pandas.Series '
            elif  isinstance(val, pd.DataFrame):
                msg += 'pandas.DataFrame '
            else: 
                msg += str(type(val)) + ' '

            msg += str(val.shape)
                
            if 'metadata' in filter_file.get_storer(key).attrs:
                msg += ', metadata: ' + str(filter_file.get_storer(key).attrs.metadata)
                
            print(msg)
            
        filter_file.close()
        
        
   
        
    def get_psd(self, channel, tag=None, fold=False, add_metadata=False):
        """
        Get PSD and associated metadata (optional) for specified channel

        
        Parameters:
        ----------
        
        channel : str (required)
             channel name

        tag : str (optional)
              psd name suffix:  "psd_[tag]" or "psd_fold_[tag]"
              if tag is None, then "psd" or "psd_fold" is used  

        fold : bool (optional, default=False)
             if True, get "psd_fold" parameter
             if False, get "psd" parameter
        
        add_medatata: bool (optional, default=False)
             if True, return metadata

        
        Return:
        ------
        
        psd : 1D numpy array
             PSD values (in Amps)
        
        freq : 1D numpy array
             Frequency associated with PSD
       
        metadata : dict  (if add_metadata=True)
             Metadata associated with parameter
        """

        psd_series, metadata = self.get_psd_series(channel, tag=tag, fold=fold,
                                                   add_metadata=True)

        psd = psd_series.values
        freq = psd_series.index

        if add_metadata:
            return psd, freq, metadata
        else:
            return psd, freq


        
        
    def get_psd_series(self, channel, tag=None, fold=False, add_metadata=False):
        """
        Get PSD and associated metadata (optional) for specified channel

        
        Parameters:
        ----------
        
        channel : str (required)
             channel name
        
        tag : str (optional)
              psd name suffix:  "psd_[tag]" or "psd_fold_[tag]"
              if tag is None, then "psd" or "psd_fold" is used  


        fold : bool (optional, default=False)
             if True, get "psd_fold" parameter
             if False, get "psd" parameter
        
        add_medatata: bool (optional, default=False)
             if True, return metadata

        
        Return:
        ------
        
        psd : pandas Series
             PSD values (in Amps), index=frequencies
       
        metadata : dict  (if add_metadata=True)
             Metadata associated with parameter
        """


        param_name = 'psd'
        if fold:
            param_name = 'psd_fold'

        if tag is not None:
            param_name += '_' + tag 
      

        return self.get_param(channel, param_name,
                              add_metadata=add_metadata)
    

        
    def get_template(self, channel, tag=None,
                     add_metadata=False):
        """
        Get template and associated metadata (optional) for specified channel

        
        Parameters:
        ----------
        
        channel : str (required)
             channel name

        tag : str (optional)
              template name suffix:  "template_[tag]"
              if tag is None, then "template" name is used

        template_name : str (optional, default='template')
             name of the template saved in the file
        
        add_medatata: bool (optional, default=False)
             if True, return metadata

        
        Return:
        ------
        
        template: 1D numpy array
             template values (in Amps)
        
        index : 1D numpy array
             Template ADC bins or time
       
        metadata : dict  (if add_metadata=True)
             Metadata associated with template
        """
      

        template_series, metadata = self.get_template_series(
            channel, tag=tag,
            add_metadata=True)
        
        template = template_series.values
        time = template_series.index
        
        if add_metadata:
            return template, time, metadata
        else:
            return template, time


        
    def get_template_series(self, channel, tag=None,
                            add_metadata=False):
        """
        Get template and associated metadata (optional) for specified channel

        
        Parameters:
        ----------
        
        channel : str (required)
             channel name

        tag : str (optional)
              template name suffix:  "template_[tag]"
              if tag is None, then "template" name is used
        
        add_medatata: bool (optional, default=False)
             if True, return metadata

        
        Return:
        ------
        
        template: pandas Series, index=ADC bins or time
              Template values
        metadata : dict  (if add_metadata=True)
             Metadata associated with template

        """

        template_name = 'template'
        if tag is not None:
            template_name += '_' + tag
            

        return self.get_param(channel, template_name,
                              add_metadata=add_metadata)
    


    
    def get_param(self, channel, param_name, add_metadata=False):
        """
        Get parameter values, index,
        and associated metadata (optional) for the specified channel

        
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
        
        value : pandas Series or DataFrame
             parameter values
       
        metadata : dict  (if add_metadata=True)
             Metadata associated with parameter
        """

        key = '/' + channel + '/' + param_name
        val, medatata = self._get(key)
        
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

        param_value : 1D numpy array or pandas Series/DataFrame (required)
             values of teh parameter

        param_index : 1D numpy array (optional, default=None)
             index of the parameter (if param_value is a numpy array)

        attributes : dict (optional, default=None)
             metadata associated with parameter

        overwrite : bool (optional, default=False)
             overwrite existing parameter in filter file (other parameters are unmodified)

        Return:
        ------

        None

        """


        # convert to series if needed
        if isinstance(param_value, np.ndarray):
            param_value = pd.Series(param_value, param_index)

        # check
        if (not isinstance(param_value, pd.Series) and
            not isinstance(param_value, pd.DataFrame)):
            raise ValueError('Parameter "' + param_name
                             + ' should be eiter a numpy array'
                             + ' or pandas Series/dataFrame')
            

        # key name
        key = '/' + channel + '/' + param_name
        
                
        self._put(key,
                  param_value,
                  attributes=attributes,
                  overwrite=overwrite)
        
        
        
    def save_psd(self, channel, psd, freq=None, sample_rate=None, tag=None,
                 fold=False, attributes=None, overwrite=False):
        """
        Save PSD for the specified channel

        
        Parameters:
        ----------
        
        channel : str (required)
             channel name

        psd : 1D numpy array or pandas Series/DataFrame (required)
             values of teh parameter

        freq : 1D numpy array (optional if "fs" argument, default=None)
             frequencies of the PSD index (if input  psd  is a numpy array)


        fs: float (optional if "freq" argument not None, default None)
             sample rate 
        
        tag : str (optional)
              psd name suffix:  "psd_[tag]" or "psd_fold_[tag]"
              if tag is None, then "psd" or "psd_fold" is used  

        fold : bool (optional, default=False)
             if True, save "psd_fold" parameter
             if False, save "psd" parameter

        attributes : dict (optional, default=None)
             metadata associated with parameter

        overwrite : bool (optional, default=False)
             overwrite existing parameter in filter file (other parameters are unmodified)


        Return:
        ------

        None

        
        """

        # check
        if (not isinstance(psd, np.ndarray) and not
            not isinstance(psd, pd.Series)):
            raise ValueError('PSD should be eiter a numpy array'
                             + ' or pandas series')

        # calculte frequencies
        if isinstance(psd, np.ndarray):

            if (freq is None and sample_rate is None):
                raise ValueError('PSD frequencies '
                                 ' or sample rate need to be provided!')

            if freq is None:

                if fold:
                    freq = rfftfreq(len(psd),d=1.0/sample_rate)
                else:
                    freq = fftfreq(len(psd),d=1.0/sample_rate)
                    
        
        if freq is not None and not isinstance(freq, np.ndarray):
            raise ValueError('PSD frequencies should be a numpy array')

        # convert to pandas Series
        if isinstance(psd, np.ndarray):
            psd = pd.Series(psd, freq)
            
        # name
        psd_name = 'psd'
        if fold:
            psd_name += '_fold'
        
        if tag is not None:
            psd_name += '_' + tag

        # full key name
        key = '/' + channel + '/' + psd_name


        # add sample rate to attribute
        if sample_rate is not None:
            if attributes is None:
                attributes = dict()
            attributes['sample_rate'] = sample_rate
            
        
        # save
        self._put(key,
                  psd,
                  attributes=attributes,
                  overwrite=overwrite)

        
    def save_template(self, channel, template, template_time=None,
                      tag=None, attributes=None, overwrite=False):
        """
        Save template for the specified channel
        
        Parameters:
        ----------
        
        channel : str (required)
             channel name

        template : 1D numpy array or pandas Series/DataFrame (required)
             values of teh parameter

        template_time : 1D numpy array (optional, default=None)
             time array for template (if input template  is a numpy array)

        tag : str (optional)
              template name suffix:  "template_[tag]"
              if tag is None, then "template" name is used
    
        attributes : dict (optional, default=None)
             metadata associated with parameter

        overwrite : bool (optional, default=False)
             overwrite existing parameter in filter file (other parameters are unmodified)


        Return:
        ------

        None
        """

        # check
        if (not isinstance(template, np.ndarray) and not
            not isinstance(template, pd.Series)):
            raise ValueError('Template should be eiter a numpy array'
                             + ' or pandas series')

        if template_time is not None and not isinstance(template_time, np.ndarray):
            raise ValueError('time parameter should be a numpy array')

        # convert to pandas Series
        if isinstance(template, np.ndarray):
            template = pd.Series(template, template_time)

        # template name
        template_name = 'template'
        if tag is not None:
            template_name += '_' + tag

            
        # store
        key = '/' + channel + '/' + template_name
        
        self._put(key,
                  template,
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

        # open file
        filter_file = pd.HDFStore(self._filter_file)
        for key in filter_file.keys():
            key_split = key.split('/')
            if len(key_split)!=3:
                continue
            chan = key_split[1]
            if '__plus__' in chan:
                chan = chan.replace('__plus__', '+')
            if '__' in chan:
                chan = chan.replace('__','|')

            chan_key = key_split[2]

            # create channel dict if needed
            if chan not in output_dict:
                output_dict[chan] = dict()

            # fill value
            output_dict[chan][chan_key] = filter_file[key]

            # fill metadata
            attributes = filter_file.get_storer(key).attrs
            if 'metadata' in attributes:
                chan_key += '_metadata'
                output_dict[chan][chan_key] = attributes.metadata


        # close file
        filter_file.close()
        
        return  output_dict




    

            
    def plot_psd(self, channels, tag=None, fold=True, unit='pA'):
        """
        Plot PSD for specified channel(s)

        Parameters:
        ----------
        
        channels :  str or list of str (required)
           channel name or list of channels

        tag : str (optional)
              psd name suffix:  "psd_[tag]" or "psd_fold_[tag]"
              if tag is None, then "psd" or "psd_fold" is used  

        fold : bool (optional, default=False)
             if True, plot "psd_fold" parameter
             if False, plot "psd" parameter

        unit : str (optional, default='pA')
            plot in Amps ('A') or pico Amps 'pA')


        Return:
        -------
        None

        """

        if not isinstance(channels, list):
            channels = [channels]

        # define fig size
        fig, ax = plt.subplots(figsize=(8, 5))
        
            
        for chan in channels:
            psd, psd_meta = self.get_psd_series(chan, tag=tag,
                                                fold=fold, add_metadata=True)
            f = psd.index
            val = psd.values**0.5
            if unit=='pA':
                val *= 1e12
            ax.loglog(f, val, label=chan)

        # add axis
        ax.legend()
        ax.tick_params(which='both', direction='in', right=True, top=True)
        ax.grid(which='minor', linestyle='dotted')
        ax.grid(which='major')
        ax.set_title('Noise PSD',fontweight='bold')
        ax.set_xlabel('Frequency [Hz]',fontweight='bold')
        if  unit=='pA':
            ax.set_ylabel('PSD [pA/rtHz]',fontweight='bold')
        else:
            ax.set_ylabel('PSD [A/rtHz]',fontweight='bold')
        
        
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
            print('Storing ' + key + ' in ' + self._filter_file)

        # check if key contains + or | (not able to save in file)
        if '+' in key:
            key = key.replace('+','__plus__')
            
        if '|' in key:
            key = key.replace('|','__')
            
            
        # check if key exist already
        file_keys = filter_file.keys()
        if (key in file_keys and not overwrite):
            raise ValueError('Key ' + key + ' already stored in '
                             + self._filter_file + '. Use "overwrite=True"'
                             + ' to overwrite or change file name')

        # save
        filter_file.put(key, value, format='fixed')

        # add attributes
        if attributes is not None:
            filter_file.get_storer(key).attrs.metadata = attributes

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


        # check if key contains + or | (not able to save in file)
        if '__plus__' in key:
            key = key.replace('__plus__', '+')
            
        if '__' in key:
            key = key.replace('__','|')
            
            
        # check key
        file_keys = filter_file.keys()
        

        if key not in file_keys:
            raise ValueError('Key ' + key + ' is not in  '
                             + self._filter_file + '. '
                             + 'Check file with "describe()"')

        
        # get
        value = filter_file.get(key)

        # get attributes
        metadata = None
        attributes = filter_file.get_storer(key).attrs
        if 'metadata' in attributes:
            metadata = filter_file.get_storer(key).attrs.metadata 

            
        # close
        filter_file.close()

        return value, metadata




    
