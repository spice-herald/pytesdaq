from pytesdaq.daq import daq
import pytesdaq.config.settings as settings
import pytesdaq.instruments.control as instrument
from pytesdaq.sequencer.sequencer import Sequencer
from pytesdaq.utils import connections
import numpy as np
import time


class IV_dIdV(Sequencer):
    
    def __init__(self,iv =False,didv =False,rp=False,rn=False, 
                 temperature_sweep=False, channel_list = list(),
                 sequencer_file='',setup_file='',pickle_file=''):

         super().__init__(channel_list = channel_list,
                          sequencer_file=sequencer_file,
                          setup_file=setup_file,
                          pickle_file=pickle_file)
         
         # measurements
         self._enable_iv = iv
         self._enable_didv = didv
         self._enable_rp = rp
         self._enable_rn = rn
         self._enable_temperature_sweep = temperature_sweep
         
        
         # configure sweep
         self._sweep_config = dict()
         self._configure()
         

    def _configure(self):
        

        """
        Configure IV/dIdV/Rp/Rn measurments
        """
        required_parameter_adc = ['sample_rate','voltage_min','voltage_max']
        required_parameter_didv = ['signal_gen_amplitude', 'signal_gen_frequency',
                                   'signal_gen_shape','loop_channels']
        required_parameter_didv.extend(required_parameter_adc)
        


        # iv-didv configure (from sequencer.ini)
        iv_didv_config =  self._config.get_iv_didv_setup()
        self._sweep_config = dict()
        
        # measurement_list
        measurements = list()
        if self._enable_rp:
            measurements.append('rp')
        if self._enable_rn:
            measurements.append('rn')
        if self._enable_iv:
            measurements.append('iv')
        if self._enable_didv:
            measurements.append('didv')
            

        for measurement_name in  measurements:
                                    
            # get config dictionary
            config_dict= dict()
            if measurement_name:
                config_dict  = iv_didv_config.get(measurement_name)
            else:
                raise ValueError('Unable to find configuration for ' + measurement_name)

                
                # check config
            param_list = required_parameter_didv
            if measurement_name=='iv':
                param_list = required_parameter_adc
            for item in param_list:
                if item not in config_dict:
                    raise ValueError(measurement_name + '  measurement require ' + str(item) +
                                     ' ! Please check configuration')
            
            # adc setup
            config_dict['adc_setup'] = self._get_adc_setup(config_dict , measurement_name)
            
            
            
            # TES bias
            if measurement_name=='rp' or measurement_name=='rn':
                bias_name = 'tes_bias_' + measurement_name
                if bias_name in self._sequencer_config:
                    bias = float(self._sequencer_config[bias_name])
                    config_dict['tes_bias'] = bias
                else:
                    raise ValueError( measurement_name + ' measurement requires tes bias setting')
                 
          
            self._sweep_config[measurement_name] = config_dict
          

        #  IV / dIdV sweep
        if self._enable_iv or self._enable_didv:

            config_dict = dict()

            # TES/Temperature vector 
            tes_bias_vect = []
            temperature_vect = []
            config_dict['use_bias_vect'] = self._sequencer_config['use_tes_bias_vect']
            if self._enable_temperature_sweep:
                config_dict['use_temperature_vect'] = self._sequencer_config['use_temperature_vect']
                config_dict['temperature_sweep_type']= self._sequencer_config['temperature_sweep_type']


            # Build TES bias vector
            if config_dict['use_bias_vect']: 
                if not self._sequencer_config['tes_bias_vect']:
                    raise ValueError('IV/dIdV sweep required bias vector if "iv_didv_use_vect" = true!')
                else:
                    tes_bias_vect = [float(bias) for bias in self._sequencer_config['tes_bias_vect']]
                    tes_bias_vect = np.unique(np.asarray(tes_bias_vect))

            else:
                required_parameter = ['tes_bias_min','tes_bias_max','tes_bias_step_N',
                                      'tes_bias_step_T','tes_bias_T']

                for key in required_parameter:
                    if key not in self._sequencer_config:
                        raise ValueError('IV/dIdV measurement require ' + str(key) +
                                         ' if "iv_didv_use_vect" = false! Please check configuration')
                                
                tes_bias_vect_n = np.arrange(self._sequencer_config['tes_bias_max'],
                                             self._sequencer_config['tes_bias_t'],
                                             -self._sequencer_config['tes_bias_step_n'])
                tes_bias_vect_t = np.arrange(self._sequencer_config['tes_bias_t'],
                                             self._sequencer_config['tes_bias_min'],
                                             -self._sequencer_config['tes_bias_step_t'])

                tes_bias_vect = np.unique(np.concatenate((tes_bias_vect_n, tes_bias_vect_t),axis=0))
                
            config_dict['tes_bias_vect'] =  tes_bias_vect 


            # Build Temperature vector
            if self._enable_temperature_sweep:
                if config_dict['use_temperature_vect']:
                    temperature_vect = [float(temp) for temp in self._sequencer_config['temperature_vect']]
                    temperature_vect = np.unique(np.asarray(temperature_vect))
                else:
                    temperature_vect = np.unique(np.arrange(self._sequencer_config['temperature_min'],
                                                            self._sequencer_config['temperature_max'],
                                                            self._sequencer_config['temperature_step']))
                config_dict['temperature_vect'] = temperature_vect 
                config_dict['temperature_sweep_type'] = self._sequencer_config['temperature_sweep_type']
                config_dict['max_temperature_wait_time'] = int(self._sequencer_config['max_temperature_wait_time'])
                config_dict['thermometer_num'] = int(self._sequencer_config['thermometer_num'])
        
            # save
            self._sweep_config['iv_didv_sweep'] = config_dict  


      

        

    def _get_adc_setup(self,config_dict,measurement_name):
        


        adc_dict = dict()

        # didv measurement type
        is_didv = (measurement_name == 'rp' or measurement_name == 'rn' or measurement_name == 'didv')
        # fill channel list
        for channel in  self._selected_channel_list:
            adc_info = connections.get_adc_info(self._connection_table,tes_channel=channel)
            adc_name = adc_info[0]
            if adc_name not in adc_dict:
                adc_dict[adc_name] = self._config.get_adc_setup(adc_name).copy()
                adc_dict[adc_name]['channel_list'] = list()
            adc_dict[adc_name]['channel_list'].append(int(adc_info[1]))

            


                
        # check required parameter
        required_parameter_adc = ['sample_rate','voltage_min','voltage_max']
        for item in required_parameter_adc:
            if item not in config_dict:
                raise ValueError(measurement_name + ' measurement require ' + str(item) +
                                 ' ! Please check configuration')
        
        # calculate nb_samples
        nb_samples = 0
        sample_rate = int(config_dict['sample_rate'])
        if (is_didv and 'nb_cycles' in config_dict):
            signal_gen_freq = float(config_dict['signal_gen_frequency'])
            nb_samples= round(float(config_dict['nb_cycles'])*sample_rate/signal_gen_freq)
        elif 'trace_length_ms' in config_dict:
            nb_samples= round(float(config_dict['trace_length_ms'])*sample_rate/1000)
        elif 'trace_length_adc' in config_dict:
            nb_samples = int(config_dict['trace_length_adc'])
        else:
            raise ValueError('Nb of cycles or trace length required for TES measurement!')
                    

        # trigger
        trigger_type = 3
        if is_didv:
            trigger_type = 2

        # fill dictionary
        for adc_name in adc_dict:
            adc_dict[adc_name]['nb_samples'] = int(nb_samples)
            adc_dict[adc_name]['sample_rate'] = int(config_dict['sample_rate'])
            adc_dict[adc_name]['voltage_min'] = float(config_dict['voltage_min'])
            adc_dict[adc_name]['voltage_max'] = float(config_dict['voltage_max'])
            adc_dict[adc_name]['trigger_type'] =  trigger_type
            
        
        return adc_dict




    def run(self):

        """ 
        Run IV / dIdV sequencer
        """
  
        
        # Instantiate DAQ
        mydaq = daq.DAQ(driver_name = self._daq_driver,
                        facility = self._facility,
                        verbose = self._verbose)
        

        # Instantiate instrumment controller
        myinstrument = instrument.Control(dummy_mode= self._dummy_mode)
        

        # ====================
        # Rp/Rn
        # ====================

        measurement_list = list()
        if self._enable_rp:
            measurement_list.append('Rp')
        if self._enable_rn:
            measurement_list.append('Rn')

        for measurement_name in  measurement_list:
           
            if self._verbose:
                print('\n' + measurement_name + ' measurement\n') 

            # configuration
            config_dict = self._sweep_config[measurement_name.lower()]
           
            # initialize detector
            for channel in self._selected_channel_list:
                
                # QET bias
                myinstrument.set_tes_bias(config_dict['tes_bias'],tes_channel=channel)
                
                # Other detector settings
                if 'output_gain' in config_dict:
                    myinstrument.set_output_gain(config_dict['output_gain'],tes_channel=channel)
                         


                # disconnect signal generator
                myinstrument.connect_signal_gen_tes(False,tes_channel=channel) 

                # set signal generator
                myinstrument.set_signal_gen_amplitude(config_dict['signal_gen_amplitude'])
                myinstrument.set_signal_gen_frequency(config_dict['signal_gen_frequency'])
                myinstrument.set_signal_gen_shape(config_dict['signal_gen_shape'])
                
                # eventually close loop, relock, zero once, etc. 
                
            
            # wait 5 seconds
            time.sleep(5)

            # setup ADC
            mydaq.set_adc_config_from_dict(config_dict['adc_setup'])
            
            # connect signal gen and take data
            run_comment = measurement_name + ' measurement'
            run_type = 100
            if measurement_name=='Rn':
                run_type = 101
                
            for channel in self._selected_channel_list:
                
                # connect to TES line
                myinstrument.connect_signal_gen_tes(True,tes_channel=channel) 
                time.sleep(2)

                # take data
                if config_dict['loop_channels']:
                    # fixme: get all settings (for hdf5 metadata)
                    # daq.set_detector_config(det_config)
                 
                    success = mydaq.run(int(config_dict['run_time']),run_type,run_comment)
                    if not success:
                        print('ERROR taking data! Stopping sequencer')
                        return False
                      
                    # disconnect
                    myinstrument.connect_signal_gen_tes(False,tes_channel=channel) 


            # take data (case all channels together)
            if not config_dict['loop_channels']:
                # mydaq.set_detector_config(det_config)
                success = mydaq.run(int(config_dict['run_time']),run_type,run_comment)
                if not success:
                    print('ERROR taking data! Stopping sequencer')
                    return False
                    




            
        # ====================
        # IV / dIdV sweep
        # ====================
        
        if not (self._enable_iv or self._enable_didv):
            return True


        # sweep config
        sweep_config = self._sweep_config['iv_didv_sweep']
        iv_config =  dict()
        didv_config = dict()
        
        if self._enable_iv:
            iv_config =  self._sweep_config['iv']
        if self._enable_didv:
            didv_config = self._sweep_config['didv']
            
        
        # Initialize detector
        for channel in self._selected_channel_list:
            #FIXME -> relock, zero once, etc.
            continue

            
        # Temperature loop
        temperature_vect = []
        nb_temperature_steps = 1
        if self._enable_temperature_sweep:
            temperature_vect  = sweep_config['temperature_vect']
            nb_temperature_steps = len(temperature_vect)
            
        for istep in range(nb_temperature_steps):

            # change temperature
            if self._enable_temperature_sweep:
            
                value = temperature_vect[istep]
                
                if sweep_config['temperature_sweep_type']=='percent':
                    # use heater without PID control
                    
                    myinstrument.set_heater(value)
                    
                    # wait time (FIXME: add slope calculation)
                    for itemp in range(sweep_config['max_temperature_wait_time']*2):
                        temperature = myinstrument.get_temperature(channel=sweep_config['thermometer_num'])
                        if self._verbose:
                            print('Current temperature: ' + str(temperature) + 'mK')
                        
                        # FIXME: slope calculation
                        time.wait(30)

                else:
                    
                    # PID controlled temperature 
                    myinstrument.set_temperature(value)
                    

            # bias sweep
            tes_bias_vect = sweep_config['tes_bias_vect']
            for bias in tes_bias_vect:

                # set bias all channels
                for channel in self._selected_channel_list:
                    myinstrument.set_tes_bias(bias,tes_channel=channel)
                    
                
                # -----------
                # IV
                # ----------
                
                if self._enable_iv:

                    # set detector
                    for channel in self._selected_channel_list:
                    
                        # disconnect signal generator, ("turn off?")
                        myinstrument.connect_signal_gen_tes(False,tes_channel=channel) 
                        
                        # other parameters
                        if 'output_gain' in iv_config:
                            myinstrument.set_output_gain(iv_config['output_gain'],tes_channel=channel)
                            
                    # wait 5 seconds
                    time.sleep(5)
                    
                    # setup ADC
                    mydaq.set_adc_config_from_dict(iv_config['adc_setup'])
                    
                    # get/set detector config metadata
                    # mydaq.set_detector_config(det_config)

                    # take data
                    run_comment = 'IV: ' + ' Bias = ' + str(bias) + 'uA'
                    if self._enable_temperature_sweep:
                        run_comment = run_comment + ', T = ' + str(temperature) + 'mK'
                  
                    success = mydaq.run(iv_config['run_time'],102,run_comment)
                    if not success:
                        print('ERROR taking data! Stopping sequencer')
                        return False
                                  
                    
                # -----------
                # dIdV
                # ----------
                
                if self._enable_didv:


                    # ADC setup
                    mydaq.set_adc_config_from_dict(didv_config['adc_setup'])
                    

                    # set detector
                    for channel in self._selected_channel_list:
                    
                        # signal generator, ("turn on?")
                        myinstrument.set_signal_gen_amplitude(didv_config['signal_gen_amplitude'])
                        myinstrument.set_signal_gen_frequency(didv_config['signal_gen_frequency'])
                        myinstrument.set_signal_gen_shape(didv_config['signal_gen_shape'])
                        myinstrument.connect_signal_gen_tes(True,tes_channel=channel) 
                
                        # other parameters
                        if 'output_gain' in iv_config:
                            myinstrument.set_output_gain(iv_config['output_gain'],tes_channel=channel)
                            
                        # wait 5 seconds
                        time.sleep(5)
                    
                        
                        if didv_config['loop_channels']:
                                                
                            # get/set detector config metadata
                            # mydaq.set_detector_config(det_config)

                            # take data
                            run_comment = 'dIdV chan ' + str(channel) + ': Bias = ' + str(bias) + 'uA'
                            if self._enable_temperature_sweep:
                                run_comment = run_comment + ', T = ' + str(temperature) + 'mK'
                            print(run_comment) 
                     
                            success = mydaq.run(didv_config['run_time'],103,run_comment)
                            if not success:
                                print('ERROR taking data! Stopping sequencer')
                                return False
                     
                            # disconnect!
                            myinstrument.connect_signal_gen_tes(False,tes_channel=channel) 

                    # take data (if all channels)
                    if not didv_config['loop_channels']:
                        run_comment = 'dIdV chan ' + str(channel) + ': Bias = ' + str(bias) + 'uA'
                        if sweep_config['temperature_sweep']:
                            run_comment = run_comment + ', T = ' + str(temperature) + 'mK'
                        success = mydaqrun(didv_config['run_time'],103,run_comment)
                        if not success:
                            print('ERROR taking data! Stopping sequencer')
                            return False
                            

        # Done

        # set heater back to 0%?
        if self._enable_temperature_sweep:
            myinstrument.set_heater(0)
            

        if self._verbose:
            print('IV/dIdV successfully finished!')

        return True
