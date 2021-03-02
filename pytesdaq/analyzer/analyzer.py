import time
import numpy as np
import qetpy as qp


class Analyzer:
    
    def __init__(self):
        
        
        # Frequency array
        self._freq_array = None

        # intialize analysis configuration
        self._initialize_config()

        # Running avg data buffer
        self._buffer = None
        self._nb_events_running_avg = 0

        # Running avg data buffer cuts
        self._buffer_cuts = None
                
        # didv fit results
        self._didv_fit_results = None
        
    
    @property
    def freq_array(self):
        return self._freq_array



    def get_config(self, config_name):
        """
        Get analysis configuration name
        """

        if config_name in self._analysis_config:
            return self._analysis_config[config_name]
        else:
            raise ValueError('Analysis configuration "' + config_name +
                             '" not available!')
        
        
    def set_config(self, config_name, config_val):
        """
        Set/Update analysis config
        """

        self._analysis_config[config_name] = config_val
            

        if self._analysis_config['norm_type']=='NoNorm':
            self._analysis_config['norm_list'] = None
        
        
      
    def process(self, data_array, adc_config, analysis_config=None):
        """
        process data based on analysis configuration
        """
        
        # ---------------------
        # analysis configuration
        # ---------------------
        if analysis_config is not None:
            for key,val in analysis_config.items():
                self._analysis_config[key] = val
            if self._analysis_config['norm_type']=='NoNorm':
                self._analysis_config['norm_list'] = None


                

        # ---------------------
        # Pileup rejection calc
        # (for running avg)
        # ---------------------
        cuts_val = None
        if (self._analysis_config['enable_pileup_rejection']
            and self._analysis_config['pileup_cuts'] is not None):
            cuts_val = self._calc_cuts(data_array, adc_config['sample_rate'])
           
           
    
          
        # ---------------------
        # normalization
        # ---------------------
        if self._analysis_config['unit']!='ADC' or self._analysis_config['norm_type']!='NoNorm':
            data_array = self.normalize(data_array, adc_config,
                                        self._analysis_config['unit'],
                                        self._analysis_config['norm_list'])



        # ---------------------
        # PSD
        # ---------------------        
        if self._analysis_config['calc_psd']:
            data_array = self.calc_psd(data_array, adc_config['sample_rate'])
        else:
            self._freq_array = None
    



        # ---------------------
        # Running average 
        # ---------------------
        if self._analysis_config['enable_running_avg']:
                        
            # store in buffer
            self._store_data(data_array, cuts_val)

            # get running average
            data_array = self._calc_running_avg()
                        
        else:
            self._buffer = None
            self._nb_events_running_avg = 0
            self._buffer_cuts = None


                
        # ---------------------
        # dIdV Fit
        # ---------------------
        didv_data_dict = None
        if self._analysis_config['fit_didv'] and self._nb_events_running_avg>=25:
            
            # check if prior results available
            #if self._didv_fit_results is not None:
            #    didv_data_dict['prior_results'] = self._didv_fit_results

            # fit
            data_array, didv_data_dict = self.fit_didv(data_array, adc_config['sample_rate'],
                                                       unit=self._analysis_config['unit'])
            
            # save results
            self._didv_fit_results = didv_data_dict['results']
        else:
            self._didv_fit_results = None
            
        # ---------------------
        # PSD -> sqrt
        # ---------------------
        if self._analysis_config['calc_psd']:
            data_array = np.sqrt(data_array)
        
            
        return data_array, didv_data_dict
    



    
    def normalize(self,data_array, adc_config, unit, norm_list=None):
        """
        Normalize array
        """

        # check if normalization needed
        if unit=='ADC':
            return data_array
        
        
        # intialize output
        data_array_norm = np.zeros_like(data_array, dtype=np.float64)
        
        # loop and normalize
        nb_channels = np.size(data_array,0)
        for ichan in range(0,nb_channels):
            chan_index = adc_config['selected_channel_index'][ichan]
            cal_coeff = adc_config['adc_conversion_factor'][chan_index][::-1]
            poly = np.poly1d(cal_coeff)
            data_array_norm[ichan,:] = poly(data_array[ichan,:])
            
            # normalize
            if norm_list is not None:
                data_array_norm[ichan,:] /= norm_list[ichan]
                
            # unit
            if unit=='mVolts':
                data_array_norm[ichan,:] *= 1000
            elif unit=='nVolts':
                data_array_norm[ichan,:] *= 1e9
            elif unit=='uAmps':
                data_array_norm[ichan,:] *= 1e6
            elif unit=='pAmps':
                data_array_norm[ichan,:] *= 1e12
            
        
        return data_array_norm
        


    



    
    def calc_psd(self, data_array, sample_rate):
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
            f_fold, psd_fold  = qp.calc_psd(trace_chan, fs=sample_rate,
                                            folded_over=True)
            if ichan==0:
                psd_array = np.zeros((nb_channels,len(psd_fold)),
                                     dtype=np.float64)
                psd_array[ichan,:] =  psd_fold
                self._freq_array = f_fold
            else:
                psd_array[ichan,:] =  psd_fold
           
        return psd_array


                
    def calc_offset(self, data_array):
        """
        Calculate offset
        """
                
        offset = np.mean(data_array, axis=1)
        return offset


    
            
    def fit_didv(self, data_array, sample_rate, unit=None, prior_didv=None):
        
        """
        Fit dIdV
        """

        # intialize
        data_array_truncated = []
        fit_array = []
        result_list = list()
        didv_data_dict = dict()
        
        # Test signal information
        sg_freq = self._analysis_config['signal_gen_frequency']
        sg_current = self._analysis_config['signal_gen_current']
        rshunt = self._analysis_config['rshunt']
        rp = self._analysis_config['rp']
        dt = self._analysis_config['dt']
        r0 = self._analysis_config['r0'] 
        dutycycle=0.5
        add180phase = self._analysis_config['add_180phase']
             
        # check normalization
        norm = 1
        if unit is not None:
            if unit=='uAmps':
                norm = 1e6
            elif unit=='pAmps':
                norm = 1e12  
                    

        
        # loop channels
        nb_channels = np.size(data_array,0)
        for ichan in range(0,nb_channels):

            # channel traces
            traces = self._buffer[ichan,:,:]/norm
            traces = np.swapaxes(traces,0,1)

            # instantiate DIDV
            didv_inst = qp.DIDV(traces,
                                sample_rate,
                                sg_freq,
                                sg_current,
                                rshunt,
                                r0=r0, rp=rp,
                                dutycycle=dutycycle,
                                add180phase=add180phase,
                                dt0=dt)
            
            # process
            print('Info: dIdV processing')
            didv_inst.processtraces()


            # save trace
            nb_samples = didv_inst._tmean.shape[0]
            if ichan==0:
                nb_samples = didv_inst._tmean.shape[0]
                data_array_truncated = np.zeros((nb_channels,nb_samples),
                                                dtype=np.float64)
                fit_array = np.zeros((nb_channels,nb_samples),
                                     dtype=np.float64)
                
            data_array_truncated[ichan,:] = (didv_inst._tmean - didv_inst._offset)*norm
          
            
            # fit
            result = None
            if self._analysis_config['didv_1pole']:
                print('Info: Starting dIdV 1-pole Fit')
                didv_inst.dofit(1)
                result = didv_inst.fitresult(1)
                print('Info: dIdV 1-pole Fit Done')

            if self._analysis_config['didv_2pole']:
                print('Info: Starting dIdV 2-pole Fit')
                didv_inst.dofit(2)
                result = didv_inst.fitresult(2)
                print('Info: dIdV 2-pole Fit Done')

            if self._analysis_config['didv_3pole']:
                print('Info: Starting dIdV 3-pole Fit')
                didv_inst.dofit(3)
                result = didv_inst.fitresult(3)
                print('Info: dIdV 3-pole Fit Done')



            # Calculate R0/I0/P0 (infinite loop
            # approximation)
            if ((self._analysis_config['didv_2pole'] or
                 self._analysis_config['didv_3pole'])
                and 'smallsignalparams' in result):
                didv = result['didv0']
                tes_bias = self._analysis_config['tes_bias_list'][ichan]
              
                # R0
                r0_infinite = (abs(1/didv) + rp + rshunt)

                # IO
                i0_infinite = (tes_bias*rshunt)/(r0_infinite+rshunt+rp)

                # P0
                p0_infinite = tes_bias*rshunt*i0_infinite - (rp + rshunt)*pow(i0_infinite,2)
                result['infinite_l'] = dict()
                result['infinite_l']['r0'] = r0_infinite
                result['infinite_l']['i0'] = i0_infinite
                result['infinite_l']['p0'] = p0_infinite
            

                
            # Add result to list
            result_list.append(result)

            # Fitted response
            dt = 1/sample_rate
            time = np.arange(0,nb_samples)*dt
                      
            key = 'params'
            if 'smallsignalparams' in result:
                key = 'smallsignalparams'

            fit_array[ichan,:] = norm*qp.squarewaveresponse(
                time,
                sg_current,
                sg_freq,
                dutycycle,
                **result[key],)
            
        didv_data_dict['fit_array'] = fit_array
        didv_data_dict['results'] = result_list
            
        return data_array_truncated, didv_data_dict



    
    
    def _store_data(self, data_array, cuts_val):
        """
        Store data in buffer for running_avg
        Buffer dimensions: (nb_channels, nb_samples, nb_events)
        """

        # add extra dimension to data array
        data_array.shape +=(1,)
        
        
        # check data buffer dimension
        dims_buffer = []
        do_reset_buffer = False

        if (self._analysis_config['reset_running_avg']
            or self._buffer is None
            or (self._analysis_config['enable_pileup_rejection']
                and self._buffer_cuts is None)):      
            do_reset_buffer = True
        else:
            
            # data buffer
            dims_buffer = self._buffer.shape
            dims_array = data_array.shape
            if dims_buffer[0:2] != dims_array[0:2]:
                do_reset_buffer = True

            # cut buffer
            if self._analysis_config['enable_pileup_rejection']:

                for cut_name,val in self._buffer_cuts.items():

                    # dimension
                    if (val.shape[0] != dims_buffer[0]
                        or val.shape[1] != dims_buffer[2]):
                        do_reset_buffer = True

                    # cut availability
                    if cut_name not in cuts_val:
                        do_reset_buffer = True

                
                        

        # reset if needed
        if do_reset_buffer:
            
            # data buffer
            self._buffer = data_array

            # cut buffer
            if self._analysis_config['enable_pileup_rejection']:
                self._buffer_cuts = cuts_val
             
            # reset internal parameters
            self._nb_events_running_avg = 1
            self._analysis_config['reset_running_avg'] = False
            
            return

        
        # delete elements
        if self._nb_events_running_avg>=self._analysis_config['nb_events_avg']:

            nb_to_delete = self._nb_events_running_avg-self._analysis_config['nb_events_avg']+1
                    
            # data buffer
            self._buffer = np.delete(self._buffer, list(range(nb_to_delete)), axis=2)

            # cut buffer
            if self._analysis_config['enable_pileup_rejection']:
                for cut_name,val in self._buffer_cuts.items():
                    self._buffer_cuts[cut_name] = np.delete(val,
                                                            list(range(nb_to_delete)),
                                                            axis=1)
                
        # append elements
        self._buffer = np.append(self._buffer, data_array, axis=2)
        if self._analysis_config['enable_pileup_rejection']:
            for cut_name,val in self._buffer_cuts.items():
                self._buffer_cuts[cut_name] = np.append(self._buffer_cuts[cut_name],
                                                        cuts_val[cut_name], axis=1)


        
        

    def _calc_running_avg(self):
        """
        Calculate running average
        """
        
        data_array = []
        if self._buffer is None:
            return  data_array

    
        # apply pileup rejection cuts
        nb_events = self._buffer.shape[2]
        self._nb_events_running_avg = nb_events
        if (self._analysis_config['enable_pileup_rejection']
            and self._buffer_cuts is not None
            and nb_events>2):

            # initialize
            nb_channels = self._buffer.shape[0]
            nb_samples =  self._buffer.shape[1]
            data_array = np.zeros((nb_channels,nb_samples), dtype=np.float64)
            
            # loop channels
            nb_events_min = 999999
            for ichan in range(nb_channels):
                    
                cut_inds = np.arange(nb_events)
                cut = np.ones(nb_events, dtype=bool)


                for cut_name,cut_sigma in self._analysis_config['pileup_cuts'].items():
                    cut_data = self._buffer_cuts[cut_name][ichan,cut_inds]
                    cut = qp.cut.iterstat(cut_data, cut=cut_sigma, precision=10000.0)[2]
                    cut_inds = np.where(cut)[0]
               

                # apply cut
                ctot = np.zeros(nb_events, dtype=bool)
                ctot[cut_inds] = True
                data = self._buffer[ichan,:,ctot]
                if data.shape[1]<nb_events_min:
                    nb_events_min = data.shape[0]
                data_array[ichan,:] = np.mean(data, axis=0)

            self._nb_events_running_avg = nb_events_min
        else:
            data_array = np.mean(self._buffer, axis=2)

                   
        return data_array



    
    def _calc_cuts(self, data_array, sample_rate):
        """
        Calculate cut values for pile-up rejection
        """

        # initialize 
        cuts_val = dict()
        nb_channels = data_array.shape[0]
        nb_samples = data_array.shape[1]
        

        # --------
        # min max
        # --------    
        if 'minmax' in self._analysis_config['pileup_cuts']:
            data_max = np.amax(data_array, axis=1)
            data_min = np.amin(data_array, axis=1)
            cut_val = data_max-data_min
            cut_val.shape += (1,)
            cuts_val['minmax'] = cut_val


        # -----------
        # OF amp/chi2
        # -----------
        if ('ofamp' in self._analysis_config['pileup_cuts'] or
            'ofchi2' in self._analysis_config['pileup_cuts']):
                        
            #  Build template
            tau_risepulse = 10.0e-6
            tau_fallpulse = 100.0e-6
            
            ind_trigger = round(nb_samples/2)
            time = 1.0/sample_rate*(np.arange(1, nb_samples+1)-ind_trigger)
            lgc_b0 = time < 0.0
            
            dummytemplate = (1.0-np.exp(-time/tau_risepulse))*np.exp(-time/tau_fallpulse)
            dummytemplate[lgc_b0]=0.0
            dummytemplate = dummytemplate/max(dummytemplate)
            
            # assume we just have white noise
            dummypsd = np.ones(nb_samples)
            
            # OF
            amp = list()
            chi2 = list()
            for ichan in range(0, nb_channels):
                trace = data_array[ichan, :]
                trace_amp, trace_t0, trace_chi2 = qp.ofamp(trace, dummytemplate, dummypsd, sample_rate)
                amp.append(trace_amp)
                chi2.append(trace_chi2)

            # store
            if 'ofamp' in self._analysis_config['pileup_cuts']:
                cut_val = np.asarray(amp)
                cut_val.shape += (1,)
                cuts_val['ofamp'] = cut_val

            if 'ofchi2' in self._analysis_config['pileup_cuts']:
                cut_val = np.asarray(chi2)
                cut_val.shape += (1,)
                cuts_val['ofchi2'] = cut_val
        
            

            
        
        # -----------
        # slope
        # -----------

        if 'slope' in self._analysis_config['pileup_cuts']:
        
            # interval definition
            slope_rangebegin = range(0, int(nb_samples/10))
            slope_rangeend = range(int(9*nb_samples/10), nb_samples)
            
            # calculate meam
            traces_begin = np.mean(data_array[:, slope_rangebegin], axis=1)
            traces_end = np.mean(data_array[:, slope_rangeend], axis=1)

            # slope
            cut_val = traces_end - traces_begin
            cut_val.shape += (1,)

            # store
            cuts_val['slope'] = cut_val 



        
        # -----------
        # baseline
        # ----------- 
        if 'baseline' in self._analysis_config['pileup_cuts']:
            cut_val =  np.mean(data_array, axis=1)
            cut_val.shape += (1,)
            cuts_val['baseline'] = cut_val 
        

        return cuts_val
    

  

        
        
    def _initialize_config(self):
        """
        Initialize analysis configuration
        """
        
        self._analysis_config = dict()
        self._analysis_config['unit'] = 'ADC'
        self._analysis_config['norm_type'] = 'NoNorm'
        self._analysis_config['norm_list'] = None
        self._analysis_config['calc_psd'] = False
        self._analysis_config['enable_running_avg'] = False
        self._analysis_config['reset_running_avg'] = False
        self._analysis_config['nb_events_avg'] = 1
        self._analysis_config['signal_gen_current'] = None
        self._analysis_config['signal_gen_frequency'] = None
        self._analysis_config['tes_bias_list'] = None
        self._analysis_config['rshunt'] = 0.005
        self._analysis_config['rp'] = 0.003
        self._analysis_config['r0'] = 0.2
        self._analysis_config['dt'] = 2e-6
        self._analysis_config['add_180phase'] = False
        self._analysis_config['fit_didv'] = False
        self._analysis_config['didv_1pole'] = False
        self._analysis_config['didv_2pole'] = False
        self._analysis_config['didv_3pole'] = False
        self._analysis_config['didv_measurement'] = False
        self._analysis_config['enable_pileup_rejection'] = False
        self._analysis_config['pileup_cuts'] = None
        
        
        
