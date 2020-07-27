import time
import numpy as np
import qetpy as qp


class Analyzer:
    
    def __init__(self):
        
        
        # Frequency array
        self._freq_array = None
      

        # default analysis configuration
        self._analysis_config = dict()
        self._analysis_config['unit'] = 'ADC'
        self._analysis_config['norm'] = 'None'
        self._analysis_config['calc_psd'] = False
        self._analysis_config['enable_running_avg'] = False
        self._analysis_config['reset_running_avg'] = False
        self._analysis_config['nb_events_avg'] = 1
        self._analysis_config['calc_didv'] = False
        self._analysis_config['enable_pileup_rejection'] = False
      
        


        # initialize data buffer for running avg
        self._buffer = None
        self._nb_events_buffer = 0
       
        
    
    @property
    def freq_array(self):
        return self._freq_array

    
    def process(self,data_array, data_config, analysis_config):
        """
        process data based on analysis configuration
        """
        
        # ---------------------
        # analysis configuration
        # ---------------------
        for key,val in analysis_config.items():
            self._analysis_config[key] = val

    

        # ---------------------
        # Pileup rejection...
        # ---------------------

        
        # ---------------------
        # normalization
        # ---------------------
        if self._analysis_config['unit']!='ADC' or self._analysis_config['norm']!='None':
            data_array = self.normalize(data_array,data_config,
                                        self._analysis_config['unit'],self._analysis_config['norm'])



        # ---------------------
        # PSD
        # ---------------------
        
        if  self._analysis_config['calc_psd']:
            data_array = self.calc_psd(data_array, data_config['sample_rate'])
        else:
            self._freq_array = None
    



        # ---------------------
        # Running average 
        # ---------------------


        if self._analysis_config['enable_running_avg']:
            self._store_data(data_array,self._analysis_config['reset_running_avg'])
            data_array = self._calc_running_avg()
            
        else:
            self._buffer = None
            self._nb_events_buffer = 0
          
               

        # ---------------------
        # PSD -> sqrt
        # ---------------------
        if  self._analysis_config['calc_psd']:
            data_array = np.sqrt(data_array)
        
      

        # return data
        return data_array
        



    def normalize(self,data_array,data_config, unit, norm):
        """
        Normalize array
        """

        # intialize output
        data_array_norm = np.zeros_like(data_array, dtype=np.float64)
       
        # loop and normalize
        nb_channels = np.size(data_array,0)
        for ichan in range(0,nb_channels):
            chan_index = data_config['selected_channel_index'][ichan]
            cal_coeff = data_config['adc_conversion_factor'][chan_index][::-1]
            poly = np.poly1d(cal_coeff)
            data_array_norm[ichan,:] = poly(data_array[ichan,:])
            
        
        return data_array_norm
        
        

    def calc_psd(self,data_array, sample_rate):
        """
        calculate PSD
        """
        
        # initialize
        psd_array = None
        freq_array = None

               
        # loop channel and calculate psd
        nb_channels = np.size(data_array,0)
        for ichan in range(0,nb_channels):
            trace_chan = data_array[ichan,:]
            f_fold, psd_fold  = qp.calc_psd(trace_chan, fs=sample_rate, folded_over=True)
            if ichan==0:
                psd_array = np.zeros((nb_channels,len(psd_fold)), dtype=np.float64)
                psd_array[ichan,:] =  psd_fold
                self._freq_array = f_fold
            else:
                psd_array[ichan,:] =  psd_fold
           
        
        return psd_array


    def _store_data(self,data_array,do_reset=False):
        """
        Store data in buffer for running_avg
        """

        # add extra dimension
        data_array.shape +=(1,)

        # check dimension
        dims_buf = []
        if self._buffer is not None:
            dims_buf = self._buffer.shape
            dims_array = data_array.shape
            if dims_buf[0:2] != dims_array[0:2]:
                do_reset = True
            
        # reset if needed
        if do_reset or self._buffer is None:
            self._buffer = data_array
            self._nb_events_buffer = 1
            return
            

        # delete elements
        if self._analysis_config['nb_events_avg']<=dims_buf[2]:
            nb_to_delete = dims_buf[2]-self._analysis_config['nb_events_avg']+1
            self._buffer = np.delete(self._buffer,list(range(nb_to_delete)),axis=2)
            
        # append element
        self._buffer = np.append(self._buffer,data_array,axis=2)
        self._nb_events_buffer = self._buffer.shape[2]

        

    def _calc_running_avg(self):
     
        data_array = None
        if self._buffer is not None:
            data_array = np.mean(self._buffer,axis=2)
        
        
        return data_array
        
            

