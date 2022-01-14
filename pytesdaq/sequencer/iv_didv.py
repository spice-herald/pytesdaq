import numpy as np
import time
import pprint as pprint

from pytesdaq.daq import daq
import pytesdaq.config.settings as settings
import pytesdaq.instruments.control as instrument
from pytesdaq.sequencer.sequencer import Sequencer
from pytesdaq.utils import connection_utils

class IV_dIdV(Sequencer):
    
    def __init__(self, iv =False, didv =False, rp=False, rn=False,
                 temperature_sweep=False,
                 comment='No comment',
                 detector_channels=None,
                 sequencer_file=None, setup_file=None, sequencer_pickle_file=None,
                 dummy_mode=False,
                 do_relock=False, do_zero=False, do_zap=False,
                 verbose=True):

        # measurements
        self._enable_iv = iv
        self._enable_didv = didv
        self._enable_rp = rp
        self._enable_rn = rn
        self._enable_temperature_sweep = temperature_sweep

        # relock/zap
        self._do_zap_tes = do_zap
        self._do_relock = do_relock
        self._do_zero_offset = do_zero
               
        measurement_list = list()
        if self._enable_iv:
            measurement_list.append('iv')
        if self._enable_didv:
            measurement_list.append('didv')
        if self._enable_rp:
            measurement_list.append('rp')
        if self._enable_rn:
            measurement_list.append('rn')
            
        # base class for sequencer/automation
        super().__init__('iv_didv',
                         measurement_list=measurement_list,
                         comment=comment,
                         detector_channels=detector_channels,
                         sequencer_file=sequencer_file,
                         setup_file=setup_file,
                         sequencer_pickle_file=sequencer_pickle_file,
                         dummy_mode=dummy_mode,
                         verbose=verbose)
            
        
        # configure measurements
        self._configure()


         

  

    def run(self):

        """ 
        Run IV / dIdV sequencer
        """
  
                      
        # Instantiate instrumment controller
        self._instrument = instrument.Control(setup_file=self._setup_file,
                                              dummy_mode=self._dummy_mode)
        
        
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
        sweep_config = self._measurement_config['iv_didv']
        iv_config =  dict()
        didv_config = dict()
        
        if self._enable_iv:
            iv_config =  self._measurement_config['iv']
        if self._enable_didv:
            didv_config = self._measurement_config['didv']
            # signal gen amplitude can be either voltage or current
            if 'signal_gen_voltage' not in didv_config:
                didv_config['signal_gen_voltage'] = None
            if 'signal_gen_current' not in didv_config:
                didv_config['signal_gen_current'] = None
            
        
                
        # Temperature loop
        temperature_vect = []
        nb_temperature_steps = 1
        if self._enable_temperature_sweep:

            # temperature array
            temperature_vect  = sweep_config['temperature_vect']
            nb_temperature_steps = len(temperature_vect)

            # thermometer
            thermometer_global_num = None
            if 'thermometer_global_num' in sweep_config:
                thermometer_global_num = int(sweep_config['thermometer_global_num'])
            thermometer_name = None
            if 'thermometer_name' in sweep_config:
                thermometer_name = sweep_config['thermometer_name']

            # heater
            heater_global_num = None
            if 'heater_global_num' in sweep_config:
                heater_global_num = int(sweep_config['heater_global_num'])
            heater_name = None
            if 'heater_name' in sweep_config:
                heater_name = sweep_config['heater_name']

            wait_stable_time =  300
            if 'temperature_stable_wait_time' in sweep_config:
                wait_stable_time = 60 * float(sweep_config['temperature_stable_wait_time'])

            max_wait_time =  300
            if 'temperature_max_wait_time' in sweep_config:
                max_wait_time = 60 * float(sweep_config['temperature_max_wait_time'])

            tolerance = 0.4
            if 'temperature_tolerance_percent' in sweep_config:
                tolerance = float(sweep_config['temperature_tolerance_percent'])
                            
            
        for istep in range(nb_temperature_steps):
            
            # change temperature
            temperature = None
            if self._enable_temperature_sweep:
                
                temperature = temperature_vect[istep]/1000
                print('INFO: Setting temperature to ' + str(temperature*1000) +'mK!')

                
                self._instrument.set_temperature(temperature,
                                                 channel_name=thermometer_name,
                                                 global_channel_number=thermometer_global_num,
                                                 heater_channel_name=heater_name,
                                                 heater_global_channel_number=heater_global_num,
                                                 wait_temperature_reached=True,
                                                 wait_cycle_time=5,
                                                 wait_stable_time=wait_stable_time,
                                                 max_wait_time=max_wait_time,
                                                 tolerance=tolerance)
            
                

            # create sequencer directory
            basename = str()
            if self._enable_iv:
                basename += '_iv'
            if self._enable_didv:
                basename += '_didv'
        
            if basename[0] == '_':
                basename = basename[1:]

            self._create_measurement_directories(basename)
        


            # ZAP TES
            if self._do_zap_tes:
                tes_bias_max = 500
                if sweep_config['use_negative_tes_bias']:
                    tes_bias_max = -500
                    
                print('INFO: Zapping TES  with bias ' + str(tes_bias_max) + 'uA') 
                for channel in self._detector_channels:
                    self._instrument.set_tes_bias(tes_bias_max, detector_channel=channel)
                time.sleep(5)


            
            # IV-dIdV:  TES bias loop
            sleeptime_s = float(sweep_config['tes_bias_change_sleep_time'])
            tes_bias_vect = sweep_config['tes_bias_vect']
            nb_steps = len(tes_bias_vect)
            istep = 0


            # Instantiate DAQ
            self._daq = daq.DAQ(driver_name=self._daq_driver,
                                verbose=self._verbose,
                                setup_file=self._setup_file)
                

           
            for bias in tes_bias_vect:

                # set bias all channels
                istep+=1
                print('INFO: Sequencer step #' + str(istep) + ' out of total '
                      + str(nb_steps) + ' steps!')
                print('INFO: Setting TES bias all channels to : '
                      + str(bias) + 'uA!')
                for channel in self._detector_channels:
                    self._instrument.set_tes_bias(bias, detector_channel=channel)
                    

                # if step 1: tes zap, relock, zero
                if istep==1:

                    # Relock
                    if self._do_relock:
                        print('INFO: Relocking channel ' + channel) 
                        self._instrument.relock(detector_channel=channel)
                        
                    # Zero
                    if self._do_zero_offset:

                        print('INFO: Zeroing offset channel ' + channel) 

                        # instantiate nidaq
                        daq_online = daq.DAQ(driver_name='pydaqmx', verbose=False)

                        
                        # setup ADC
                        adc_id, adc_chan = connection_utils.get_adc_channel_info(
                            self._detector_connection_table,
                            detector_channel=channel
                        )

                        setup_dict = dict()
                        setup_dict[adc_id] = self._config.get_adc_setup(adc_id).copy()
                        setup_dict[adc_id]['nb_samples'] = 20000
                        setup_dict[adc_id]['channel_list'] = [adc_chan]
                        setup_dict[adc_id]['trigger_type'] = 3

                        daq_online.set_adc_config_from_dict(setup_dict)


                        # initialize array
                        data_array = np.zeros((1,20000), dtype=np.int16)
                        data_buffer = None

                        for ievent in range(50):

                            # get event
                            daq_online.read_single_event(data_array, do_clear_task=False)
                         
                            # normalize to volts
                            data_array_norm = np.zeros_like(data_array, dtype=np.float64)
                            cal_coeff = setup_dict[adc_id]['adc_conversion_factor'][0][::-1]
                            poly = np.poly1d(cal_coeff)
                            data_array_norm[0,:] = poly(data_array[0,:])
            
                            # save in buffer
                            data_array_norm.shape +=(1,)
            
                            if data_buffer is None:
                                data_buffer = data_array_norm
                            else:
                                data_buffer = np.append(data_buffer, data_array_norm, axis=2)

                        
                        daq_online.clear()

                        # calc offset
                        data_mean = np.mean(data_buffer, axis=2)
                        offset = float(np.median(data_mean, axis=1))

                        # zero
                        driver_gain = self._instrument.get_output_total_gain(detector_channel=channel)
                        current_offset = self._instrument.get_output_offset(detector_channel=channel)
                        new_offset = current_offset-offset/driver_gain
                        self._instrument.set_output_offset(new_offset, detector_channel=channel)
                        

                    
                # sleep
                #if tes_bias_change_sleep_time in sweep_config:
                print('INFO: Sleeping for ' + str(sleeptime_s) + ' seconds!')
                time.sleep(sleeptime_s)
                


                # get temperature
                if self._enable_temperature_sweep:
                    temperature = self._instrument.get_temperature(
                        channel_name=thermometer_name,
                        global_channel_number=thermometer_global_num
                    )
                    
                    print('INFO: Temperature is '
                          + str(temperature*1000) +'mK!')
                

             
                    
                # -----------
                # IV
                # ----------
                
                if self._enable_iv:

                    # set detector
                    for channel in self._detector_channels:
                    
                        # disconnect signal generator
                        self._instrument.set_signal_gen_onoff('off', detector_channel=channel)

                        # disconnect from TES
                        self._instrument.connect_signal_gen_to_tes(False, detector_channel=channel)
                        
                        # other parameters
                        if 'output_gain' in iv_config:
                            self._instrument.set_output_gain(float(iv_config['output_gain']),
                                                             detector_channel=channel)
                            
                    # wait 5 seconds
                    time.sleep(5)
                    
                    # setup ADC
                    self._daq.set_adc_config_from_dict(iv_config['adc_setup'])
                    
                    # get/set detector config metadata
                    det_config = dict()
                    adc_channel_dict= connection_utils.get_adc_channel_list(
                        self._detector_connection_table,
                        detector_channel_list=self._detector_channels
                    )

                    for adc_name in adc_channel_dict:
                        det_config[adc_name] = self._instrument.read_all(
                            adc_id=adc_name,
                            adc_channel_list=adc_channel_dict[adc_name]
                        )

                        if temperature is not None:
                            det_config[adc_name]['temperature'] = temperature
                            
                    
                        
                    self._daq.set_detector_config(det_config)
                    
                    # take data
                    run_comment = 'IV: ' + ' TES bias = ' + str(bias) + 'uA'
                    if self._enable_temperature_sweep:
                        run_comment = run_comment + ', T = ' + str(temperature) + 'mK'


                    print('INFO: Starting IV data taking with TES bias = ' + str(bias) + 'uA!')
                    success = self._daq.run(run_time=int(iv_config['run_time']),
                                            run_type=102,
                                            run_comment=run_comment,
                                            group_name=self._group_name,
                                            group_comment=self._comment,
                                            data_path=self._raw_data_path,
                                            data_prefix='iv')

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
                    for channel in self._detector_channels:
                    
                        # signal generator
                        
                        self._instrument.set_signal_gen_params(detector_channel=channel,source='tes', 
                                                               voltage=didv_config['signal_gen_voltage'],
                                                               current=didv_config['signal_gen_current'],
                                                               frequency=didv_config['signal_gen_frequency'],
                                                               shape='square')


                    
                        self._instrument.set_signal_gen_onoff('on', detector_channel=channel)

                        # connect to TES
                        self._instrument.connect_signal_gen_to_tes(True, detector_channel=channel)

                        
                        # other parameters
                        if 'output_gain' in didv_config:
                            self._instrument.set_output_gain(float(didv_config['output_gain']),
                                                             detector_channel=channel)
                            
                        # wait 5 seconds
                        time.sleep(5)
                    
                        
                        if didv_config['loop_channels']:
                                                
                            # get/set detector config metadata
                            det_config = dict()
                            adc_channel_dict = connection_utils.get_adc_channel_list(
                                self._detector_connection_table,
                                detector_channel_list=self._detector_channels
                            )
                            
                            for adc_name in adc_channel_dict:
                                det_config[adc_name] = self._instrument.read_all(
                                    adc_id=adc_name,
                                    adc_channel_list=adc_channel_dict[adc_name]
                                )
                                if temperature is not None:
                                    det_config[adc_name]['temperature'] = temperature
                          
                                
                            self._daq.set_detector_config(det_config)

                    
                            # take data
                            run_comment = 'dIdV chan ' + str(channel) + ': TES bias = ' + str(bias) + 'uA'
                            if self._enable_temperature_sweep:
                                run_comment = run_comment + ', T = ' + str(temperature) + 'mK'
                                
                            print('INFO: Starting dIdV data taking for channel ' + str(channel)
                                  + ' with TES bias = ' + str(bias) + 'uA!')
                            success = self._daq.run(run_time=int(didv_config['run_time']),
                                                    run_type=103,
                                                    run_comment=run_comment,
                                                    group_name=self._group_name,
                                                    group_comment=self._comment,
                                                    data_path=self._raw_data_path,
                                                    data_prefix='didv')
                           
                            if not success:
                                print('ERROR taking data! Stopping sequencer')
                                return False
                     
                            # turn off signal genrator
                            self._instrument.connect_signal_gen_to_tes(False, detector_channel=channel)
                            
                         

                    # take data (if all channels)
                    if not didv_config['loop_channels']:
 
                        # get/set detector config metadata
                        det_config = dict()
                        adc_channel_dict= connection_utils.get_adc_channel_list(
                            self._detector_connection_table,
                            detector_channel_list=self._detector_channels
                        )

                        for adc_name in adc_channel_dict:
                            det_config[adc_name] = self._instrument.read_all(
                                adc_id=adc_name,
                                adc_channel_list=adc_channel_dict[adc_name]
                            )
                            if temperature is not None:
                                det_config[adc_name]['temperature'] = temperature
                          
                        self._daq.set_detector_config(det_config)


                        # start run
                        run_comment = 'dIdV: TES bias = ' + str(bias) + 'uA'
                        if sweep_config['temperature_sweep']:
                            run_comment = run_comment + ', T = ' + str(temperature) + 'mK'


                        print('INFO: Starting dIdV data takibg with TES bias = ' + str(bias) + 'uA!')
                        success = self._daq.run(run_time=int(didv_config['run_time']),
                                                run_type=103,
                                                run_comment=run_comment,
                                                group_name=self._group_name,
                                                group_comment=self._comment,
                                                data_path=self._raw_data_path,
                                                data_prefix='didv')

                        if not success:
                            print('ERROR taking data! Stopping sequencer')
                            return False
                            
            self._daq.clear()



        # Done temperature/tes sweep

        # set heater back to 0%?
        if self._enable_temperature_sweep:
            self._instrument.set_temperature(0,
                                             channel_name=thermometer_name,
                                             global_channel_number=thermometer_global_num,
                                             heater_channel_name=heater_name,
                                             heater_global_channel_number=heater_global_num,
                                             wait_temperature_reached=False)
            
            

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

        for measurement in  measurement_list:
           
            if self._verbose:
                print('\n===============================')
                print(measurement + ' measurement') 
                print('===============================\n')


            # create sequencer directory
            basename = measurement.lower()
            self._create_measurement_directories(basename)
        
                
            # configuration
            config_dict = self._measurement_config[measurement.lower()]
           
            # initialize detector
            for channel in self._detector_channels:
                
                # QET bias
                self._instrument.set_tes_bias(config_dict['tes_bias'],
                                              detector_channel=channel)
                
                # Other detector settings
                if 'output_gain' in config_dict:
                    self._instrument.set_output_gain(float(config_dict['output_gain']),
                                                     detector_channel=channel)
                         


                #  turn off signal generator (avoid cross talk)
                self._instrument.set_signal_gen_onoff('off', detector_channel=channel)
                          
                # Eventually close loop, relock, zero once, etc. 
                

            
            # wait 5 seconds
            time.sleep(5)

            # setup ADC
            self._daq.set_adc_config_from_dict(config_dict['adc_setup'])
            
            # connect signal gen and take data
            run_comment = measurement + ' measurement'
            run_type = 100
            if measurement=='Rn':
                run_type = 101
                
            for channel in self._detector_channels:
                
                
                # signal generator
                self._instrument.set_signal_gen_params(detector_channel=channel,
                                                       source='tes', 
                                                       voltage=didv_config['signal_gen_voltage'],
                                                       current=didv_config['signal_gen_current'],
                                                       frequency=didv_config['signal_gen_frequency'],
                                                       shape='square')
            
                self._instrument.set_signal_gen_onoff('on', detector_channel=channel)
                time.sleep(2)

               
                # take data
                if config_dict['loop_channels']:

                    # read and store detector settings
                    det_config = dict()
                    adc_channel_dict = connection_utils.get_adc_channel_list(
                        self._detector_connection_table,
                        detector_channel_list=self._detector_channels
                    )
                    
                    for adc_name in adc_channel_dict:
                        det_config[adc_name] = self._instrument.read_all(
                            adc_id=adc_name,
                            adc_channel_list=adc_channel_dict[adc_name]
                        )

                    self._daq.set_detector_config(det_config)
                 

                    # take data
                    success = self._daq.run(run_time=int(config_dict['run_time']),
                                            run_type=run_type,
                                            run_comment=run_comment,
                                            group_name=self._group_name,
                                            group_comment=self._comment,
                                            data_path=self._raw_data_path,
                                            data_prefix=measurement.lower())
                    if not success:
                        print('ERROR taking data! Stopping sequencer')
                        return False
                      
                    # disconnect
                    self._instrument.set_signal_gen_onoff('off', detector_channel=channel)
                    


            # take data (case all channels together)
            if not config_dict['loop_channels']:

                # read and store detector settings
                det_config = dict()
                adc_channel_dict= connection_utils.get_adc_channel_list(
                    self._detector_connection_table,
                    detector_channel_list=self._detector_channels
                )

                for adc_name in adc_channel_dict:
                    det_config[adc_name] = self._instrument.read_all(
                        adc_id=adc_name,
                        adc_channel_list=adc_channel_dict[adc_name]
                    )
                    
                self._daq.set_detector_config(det_config)
                                 
                # take data
                success = self._daq.run(run_time=int(config_dict['run_time']),
                                        run_type=run_type,
                                        run_comment=run_comment,
                                        group_name=self._group_name,
                                        group_comment=self._comment,
                                        data_path=self._raw_data_path,
                                        data_prefix=measurement.lower())
                
                if not success:
                    print('ERROR taking data! Stopping sequencer')
                    return False
                                

   


    def _configure(self):
        """
        Configure IV/dIdV/Rp/Rn measurements
        """


        #  IV / dIdV:  TES sweep parameters
        if self._enable_iv or self._enable_didv:

            config_dict = self._measurement_config['iv_didv']
         
            # Build TES bias vector
            tes_bias_vect = []
            temperature_vect = []
            if config_dict['use_tes_bias_vect']: 
                if not config_dict['tes_bias_vect']:
                    raise ValueError('IV/dIdV sweep required bias vector if "use_tes_bias_vect" = true!')
                else:
                    tes_bias_vect = [float(bias) for bias in config_dict['tes_bias_vect']]
                    tes_bias_vect = np.unique(np.asarray(tes_bias_vect))
                    tes_bias_vect = tes_bias_vect[::-1]
             
            else:
                required_parameter = ['use_negative_tes_bias',
                                      'tes_bias_min','tes_bias_max','tes_bias_step_n',
                                      'tes_bias_step_t','tes_bias_t']

                for key in required_parameter:
                    if key not in config_dict:
                        raise ValueError('IV/dIdV measurement require ' + str(key) +
                                         ' if "use_tes_bias_vect" = false! Please check configuration')
                
                tes_bias_vect_n = np.arange(float(config_dict['tes_bias_max']),
                                            float(config_dict['tes_bias_t']),
                                            -float(config_dict['tes_bias_step_n']))
                tes_bias_vect_t = np.arange(float(config_dict['tes_bias_t']),
                                            float(config_dict['tes_bias_sc']),
                                            -float(config_dict['tes_bias_step_t']))
                tes_bias_vect_sc = np.arange(float(config_dict['tes_bias_sc']),
                                             float(config_dict['tes_bias_min']),
                                             -float(config_dict['tes_bias_step_sc']))
                
                tes_bias_vect = np.unique(np.concatenate((tes_bias_vect_n,
                                                          tes_bias_vect_t,
                                                          tes_bias_vect_sc,
                                                          np.array([float(config_dict['tes_bias_min'])])),
                                                         axis=0))

                tes_bias_vect = tes_bias_vect[::-1]

          
            if ('use_negative_tes_bias' in config_dict and
                config_dict['use_negative_tes_bias']):
                tes_bias_vect = [-x for x in tes_bias_vect]
                
                
            config_dict['tes_bias_vect'] =  tes_bias_vect 

          
            # Build temperature vector
            if self._enable_temperature_sweep:
                if config_dict['use_temperature_vect']:
                    temperature_vect = [float(temp) for temp in config_dict['temperature_vect']]
                    temperature_vect = np.unique(np.asarray(temperature_vect))
                else:
                    temperature_vect = np.arange(float(config_dict['temperature_min']),
                                                 float(config_dict['temperature_max']),
                                                 float(config_dict['temperature_step']))
                    temperature_vect = np.unique(
                        np.concatenate((temperature_vect,
                                        np.array([float(config_dict['temperature_max'])])),
                                       axis=0))
                        
                    
                config_dict['temperature_vect'] = temperature_vect 
               
        
            # save
            self._measurement_config['iv_didv'] = config_dict  

