import time
import numpy as np
import qetpy as qp


class Analyzer:
    
    def __init__(self):
        
        
        # initialize data array
        self._data_array = []
        self._data_config = dict()
        self._psd_array = []
        self._freq_array = []
        self._analysis_config = dict()


    def set_data(self,data_array,data_config):
        self._data_array = data_array
        self._data_config = data_config
      


    def get_processed_data(self):
        if self._analysis_config ['calc_psd']:
            return self._psd_array
        else:
            return self._data_array
  
    def get_freq_array(self):
        return self._freq_array




    
    def process(self,analysis_config):

        # analysis dictionary
        self._analysis_config = analysis_config



        # pileup rejection...

        
        # running avg


        # normalization
        #if self._analysis_config['unit']!='adc' or self._analysis_config['norm']!='None':
        #    self.normalize()


        # PSD calculation 
        if  analysis_config['calc_psd']:
            self.calc_psd()
            
    




    def normalize(self):
        print('Normalize')

        

    def calc_psd(self,sample_rate=[]):

        # initialize
        self._psd_array = []
        self._freq_array = []

        # sample rate 
        if not sample_rate and 'sample_rate' in self._data_config:
            sample_rate = self._data_config['sample_rate']
        
        if not sample_rate:
            print('ERROR in calc_psd: No sample rate provided!')
            return
        
        # loop channel and calculate psd
        nb_channels = np.size(self._data_array,0)
        for ichan in range(0,nb_channels):
            trace_chan = self._data_array[ichan,:]
            f_fold, psd_fold  = qp.calc_psd(trace_chan, fs=sample_rate, folded_over=True)
            if ichan==0:
                self._psd_array = np.zeros((nb_channels,len(psd_fold)), dtype=np.float64)
                self._psd_array[ichan,:] =  psd_fold
                self._freq_array = f_fold
            else:
                self._psd_array[ichan,:] =  psd_fold
           
        
