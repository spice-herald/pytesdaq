from pytesdaq.daq import daq
import pytesdaq.config.settings as settings
import pytesdaq.instruments.control as instrument
from pytesdaq.sequencer.sequencer import Sequencer
from pytesdaq.utils import connection_utils
import numpy as np
import time


class IV_dIdV(Sequencer):
    
    def __init__(self, iv =False, didv =False, rp=False, rn=False, 
                 temperature_sweep=False, channel_list = list(),
                 sequencer_file=None, setup_file=None, pickle_file=None,
                 verbose=True):

         super().__init__(channel_list = channel_list,
                          sequencer_file=sequencer_file,
                          setup_file=setup_file,
                          pickle_file=pickle_file,
                          verbose=verbose)
         
         # measurements
         self._enable_iv = iv
         self._enable_didv = didv
         self._enable_rp = rp
         self._enable_rn = rn
         self._enable_temperature_sweep = temperature_sweep
         
        
         # configure sweep
         self._sweep_config = dict()
         self._configure()


         

  

    def run(self):

        """ 
        Run IV / dIdV sequencer
        """
  
        
        # Instantiate DAQ
        self._daq = daq.DAQ(driver_name = self._daq_driver,
                            verbose = self._verbose,
                            setup_file=self._setup_file)
        
        
        # Instantiate instrumment controller
        self._instrument = instrument.Control(dummy_mode= self._dummy_mode)
        
        
        # ------------
        # Rp/Rn
        # ------------

        if self._enable_rp or  self._enable_rn:
            self._run_rp_rn()
        

        # ------------
        # IV/dIdV sweep
        # ------------
        if self._enable_iv or self._enable_didv:
            self._run_iv_didv()


        print('INFO: Sequencer done!')




    def _run_iv_didv(self):
        """
        IV/dIdV sweep
        """


        if not (self._enable_iv or self._enable_didv):
            return True

    

        # display
        if self._verbose:
            measurement = str()
            if self._enable_iv and self._enable_didv:
                measurement = 'IV and dIdV measurements'
            elif self._enable_iv:
                measurement = 'IV measurement'
            else:
                measurement = 'dIdV measurement'
        
            print('\n===============================')
            print(measurement) 
            print('===============================\n')



        # sweep config
        sweep_config = self._sweep_config['iv_didv_sweep']
        iv_config =  dict()
        didv_config = dict()
        
        if self._enable_iv:
            iv_config =  self._sweep_config['iv']
        if self._enable_didv:
            didv_config = self._sweep_config['didv']
            # signal gen amplitude can be either voltage or current
            if 'signal_gen_voltage' not in didv_config:
                didv_config['signal_gen_voltage'] = None
            if 'signal_gen_current' not in didv_config:
                didv_config['signal_gen_current'] = None
            
        
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
                    
                    self._instrument.set_heater(value)
                    
                    # wait time (FIXME: add slope calculation)
                    for itemp in range(sweep_config['max_temperature_wait_time']*2):
                        temperature = self._instrument.get_temperature(channel=sweep_config['thermometer_num'])
                        if self._verbose:
                            print('Current temperature: ' + str(temperature) + 'mK')
                        
                        # FIXME: slope calculation
                        time.wait(30)

                else:         
                    # PID controlled temperature 
                    self._instrument.set_temperature(value)
                    

            # bias sweep
            tes_bias_vect = sweep_config['tes_bias_vect']
            nb_steps = len(tes_bias_vect)
            istep = 0
           
            for bias in tes_bias_vect:

                # set bias all channels
                istep+=1
                print('INFO: Sequencer step #' + str(istep) + ' out of total ' + str(nb_steps) + ' steps!')
                print('INFO: Setting TES bias all channels to : ' + str(bias) + 'uA!')
                for channel in self._selected_channel_list:
                    self._instrument.set_tes_bias(bias, tes_channel=channel)
                    

                # sleep
                sleeptime_s = 15
                #if tes_bias_change_sleep_time in sweep_config:
                #    sleeptime_s = sweep_config['tes_bias_change_sleep_time']
                #print('INFO: Sleeping for ' + str(sleeptime_s) + ' seconds!')
                time.sleep(sleeptime_s)
                


                    
                # -----------
                # IV
                # ----------
                
                if self._enable_iv:

                    # set detector
                    for channel in self._selected_channel_list:
                    
                        # disconnect signal generator
                        self._instrument.set_signal_gen_onoff('off',tes_channel=channel)

                        # disconnect from TES
                        self._instrument.connect_signal_gen_to_tes(False, tes_channel=channel)
                        
                        # other parameters
                        if 'output_gain' in iv_config:
                            self._instrument.set_output_gain(float(iv_config['output_gain']),
                                                             tes_channel=channel)
                            
                    # wait 5 seconds
                    time.sleep(5)
                    
                    # setup ADC
                    self._daq.set_adc_config_from_dict(iv_config['adc_setup'])
                    
                    # get/set detector config metadata
                    det_config = dict()
                    adc_channel_dict= connection_utils.get_adc_channel_list(self._connection_table,
                                                                            tes_channel_list=self._selected_channel_list)
                    for adc_name in adc_channel_dict:
                        det_config[adc_name] = self._instrument.read_all(adc_id=adc_name,
                                                                         adc_channel_list=adc_channel_dict[adc_name])
                    self._daq.set_detector_config(det_config)
                    
                    # take data
                    run_comment = 'IV: ' + ' TES bias = ' + str(bias) + 'uA'
                    if self._enable_temperature_sweep:
                        run_comment = run_comment + ', T = ' + str(temperature) + 'mK'


                    print('INFO: Starting IV data taking with TES bias = ' + str(bias) + 'uA!')
                    success = self._daq.run(run_time = int(iv_config['run_time']),run_type = 102,
                                            run_comment = run_comment, data_path = self._data_path,
                                            data_prefix = 'iv')

                    if not success:
                        print('ERROR taking data! Stopping sequencer')
                        return False
                                  
                    
                # -----------
                # dIdV
                # ----------
                
                if self._enable_didv:


                    # ADC setup
                    self._daq.set_adc_config_from_dict(didv_config['adc_setup'])
                    

                    # set detector
                    for channel in self._selected_channel_list:
                    
                        # signal generator
                        
                        self._instrument.set_signal_gen_params(tes_channel=channel,source='tes', 
                                                               voltage=didv_config['signal_gen_voltage'],
                                                               current=didv_config['signal_gen_current'],
                                                               frequency=didv_config['signal_gen_frequency'],
                                                               shape='square')


                    
                        self._instrument.set_signal_gen_onoff('on',tes_channel=channel)

                        # connect to TES
                        self._instrument.connect_signal_gen_to_tes(True, tes_channel=channel)

                        
                        # other parameters
                        if 'output_gain' in didv_config:
                            self._instrument.set_output_gain(float(didv_config['output_gain']),tes_channel=channel)
                            
                        # wait 5 seconds
                        time.sleep(5)
                    
                        
                        if didv_config['loop_channels']:
                                                
                            # get/set detector config metadata
                            det_config = dict()
                            adc_channel_dict= connection_utils.get_adc_channel_list(self._connection_table,
                                                                                    tes_channel_list=self._selected_channel_list)
                            for adc_name in adc_channel_dict:
                                det_config[adc_name] = self._instrument.read_all(adc_id=adc_name,
                                                                                 adc_channel_list=adc_channel_dict[adc_name])
                            self._daq.set_detector_config(det_config)

                    
                            # take data
                            run_comment = 'dIdV chan ' + str(channel) + ': TES bias = ' + str(bias) + 'uA'
                            if self._enable_temperature_sweep:
                                run_comment = run_comment + ', T = ' + str(temperature) + 'mK'
                                
                            print('INFO: Starting dIdV data taking for channel ' + str(channel)
                                  + ' with TES bias = ' + str(bias) + 'uA!')
                            success = self._daq.run(run_time = int(didv_config['run_time']),run_type = 103,
                                                    run_comment = run_comment, data_path = self._data_path,
                                                    data_prefix = 'didv')
                           
                            if not success:
                                print('ERROR taking data! Stopping sequencer')
                                return False
                     
                            # turn off signal genrator
                            self._instrument.set_signal_gen_onoff('off',tes_channel=channel)
                         

                    # take data (if all channels)
                    if not didv_config['loop_channels']:
 
                        # get/set detector config metadata
                        det_config = dict()
                        adc_channel_dict= connection_utils.get_adc_channel_list(self._connection_table,
                                                                                tes_channel_list=self._selected_channel_list)
                        for adc_name in adc_channel_dict:
                            det_config[adc_name] = self._instrument.read_all(adc_id=adc_name,
                                                                             adc_channel_list=adc_channel_dict[adc_name])
                        self._daq.set_detector_config(det_config)


                        # start run
                        run_comment = 'dIdV: TES bias = ' + str(bias) + 'uA'
                        if sweep_config['temperature_sweep']:
                            run_comment = run_comment + ', T = ' + str(temperature) + 'mK'


                        print('INFO: Starting dIdV data takibg with TES bias = ' + str(bias) + 'uA!')
                        success = self._daq.run(run_time=int(didv_config['run_time']), run_type=103,
                                                run_comment=run_comment, data_path=self._data_path,
                                                data_prefix='didv')

                        if not success:
                            print('ERROR taking data! Stopping sequencer')
                            return False
                            

        # Done

        # set heater back to 0%?
        if self._enable_temperature_sweep:
            self._instrument.set_heater(0)
            

        if self._verbose:
            print('IV/dIdV successfully finished!')

      





    def _run_rp_rn(self):
        """
        Measure Rp/Rn
        """

        if self._daq is None or self._instrument is None:
            print('WARNING: daq or instrument has not been instanciated!')
            self._daq = None
            self._instrument = None
            return


        # measurement list
        measurement_list = list()
        if self._enable_rp:
            measurement_list.append('Rp')
        if self._enable_rn:
            measurement_list.append('Rn')

        for measurement_name in  measurement_list:
           
            if self._verbose:
                print('\n===============================')
                print(measurement_name + ' measurement') 
                print('===============================\n')


            # configuration
            config_dict = self._sweep_config[measurement_name.lower()]
           
            # initialize detector
            for channel in self._selected_channel_list:
                
                # QET bias
                self._instrument.set_tes_bias(config_dict['tes_bias'],tes_channel=channel)
                
                # Other detector settings
                if 'output_gain' in config_dict:
                    self._instrument.set_output_gain(float(config_dict['output_gain']),
                                                     tes_channel=channel)
                         


                #  turn off signal generator (avoid cross talk)
                self._instrument.set_signal_gen_onoff('off',tes_channel=channel)
                          
                # Eventually close loop, relock, zero once, etc. 
                

            
            # wait 5 seconds
            time.sleep(5)

            # setup ADC
            self._daq.set_adc_config_from_dict(config_dict['adc_setup'])
            
            # connect signal gen and take data
            run_comment = measurement_name + ' measurement'
            run_type = 100
            if measurement_name=='Rn':
                run_type = 101
                
            for channel in self._selected_channel_list:
                
                
                # signal generator
                self._instrument.set_signal_gen_params(tes_channel=channel,
                                                       source='tes', 
                                                       voltage=didv_config['signal_gen_voltage'],
                                                       current=didv_config['signal_gen_current'],
                                                       frequency=didv_config['signal_gen_frequency'],
                                                       shape='square')
            
                self._instrument.set_signal_gen_onoff('on',tes_channel=channel)
                time.sleep(2)

               
                # take data
                if config_dict['loop_channels']:

                    # read and store detector settings
                    det_config = dict()
                    adc_channel_dict = connection_utils.get_adc_channel_list(self._connection_table,
                                                                             tes_channel_list=self._selected_channel_list)
                    for adc_name in adc_channel_dict:
                        det_config[adc_name] = self._instrument.read_all(adc_id=adc_name,
                                                                         adc_channel_list=adc_channel_dict[adc_name])
                    self._daq.set_detector_config(det_config)
                 


                    # take data
                    success = self._daq.run(run_time = int(config_dict['run_time']),run_type = run_type,
                                            run_comment = run_comment, data_path = self._data_path,
                                            data_prefix = measurement_name.lower())
                    if not success:
                        print('ERROR taking data! Stopping sequencer')
                        return False
                      
                    # disconnect
                    self._instrument.set_signal_gen_onoff('off',tes_channel=channel)
                    


            # take data (case all channels together)
            if not config_dict['loop_channels']:

                # read and store detector settings
                det_config = dict()
                adc_channel_dict= connection_utils.get_adc_channel_list(self._connection_table,
                                                                        tes_channel_list=self._selected_channel_list)
                for adc_name in adc_channel_dict:
                    det_config[adc_name] = self._instrument.read_all(adc_id=adc_name,
                                                                     adc_channel_list=adc_channel_dict[adc_name])
                self._daq.set_detector_config(det_config)
                                 
                # take data
                success = self._daq.run(run_time = int(config_dict['run_time']),run_type = run_type,
                                        run_comment = run_comment, data_path = self._data_path,
                                        data_prefix = measurement_name.lower())
                
                if not success:
                    print('ERROR taking data! Stopping sequencer')
                    return False
                                

   


    def _configure(self):
        """
        Load IV/dIdV/Rp/Rn measurements
        Store configuration in dictionnary
        """

        required_parameter_adc = ['sample_rate','voltage_min','voltage_max']
        required_parameter_didv = ['signal_gen_frequency','signal_gen_shape','loop_channels']
        if self._config.get_signal_generator()=='magnicon':
            required_parameter_didv.append('signal_gen_current')
        else:
            required_parameter_didv.append('signal_gen_voltage')
            
        required_parameter_didv.extend(required_parameter_adc)
        
        # initialize sweep configuration
        self._sweep_config = dict()

        # iv-didv configure (from sequencer.ini)
        iv_didv_config =  self._config.get_iv_didv_setup()
      
       
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
           
            
            
            # Rp/Rn TES bias
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
                    tes_bias_vect = tes_bias_vect[::-1]
             
            else:
                required_parameter = ['use_negative_bias', 'tes_bias_min','tes_bias_max','tes_bias_step_n',
                                      'tes_bias_step_t','tes_bias_t']

                for key in required_parameter:
                    if key not in self._sequencer_config:
                        raise ValueError('IV/dIdV measurement require ' + str(key) +
                                         ' if "iv_didv_use_vect" = false! Please check configuration')
                
                tes_bias_vect_n = np.arange(float(self._sequencer_config['tes_bias_max']),
                                            float(self._sequencer_config['tes_bias_t']),
                                            -float(self._sequencer_config['tes_bias_step_n']))
                tes_bias_vect_t = np.arange(float(self._sequencer_config['tes_bias_t']),
                                            float(self._sequencer_config['tes_bias_sc']),
                                            -float(self._sequencer_config['tes_bias_step_t']))
                tes_bias_vect_sc = np.arange(float(self._sequencer_config['tes_bias_sc']),
                                             float(self._sequencer_config['tes_bias_min']),
                                             -float(self._sequencer_config['tes_bias_step_sc']))
                
                tes_bias_vect = np.unique(np.concatenate((tes_bias_vect_n,
                                                          tes_bias_vect_t,
                                                          tes_bias_vect_sc,
                                                          np.array([float(self._sequencer_config['tes_bias_min'])])),
                                                         axis=0))

                tes_bias_vect = tes_bias_vect[::-1]
                if self._sequencer_config['use_negative_bias']:
                    tes_bias_vect = [-x for x in tes_bias_vect]
             
                
            config_dict['tes_bias_vect'] =  tes_bias_vect 
           

            # Build temperature vector
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



            
            # create sequencer directory
            basename = str()
            if self._enable_iv:
                basename = basename + '_iv'
            if self._enable_didv:
                basename = basename + '_didv'
            if self._enable_rp:
                basename = basename + '_rp'
            if self._enable_rn:
                basename = basename + '_rn'
                self._enable_rp = rp

            if basename[0] == '_':
                basename = basename[1:]
                
            self._create_directory(basename)
