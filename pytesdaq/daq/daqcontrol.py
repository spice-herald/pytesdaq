import numpy as np
import time
import struct
from pytesdaq.config import settings
from pytesdaq.daq import DAQ
from pytesdaq.utils import arg_utils
from pytesdaq.utils import connection_utils
from pytesdaq.instruments import control as instrument
from pytesdaq.io import convert_length_msec_to_samples
import os
from pprint import pprint
import copy
from datetime import datetime
import stat

class DAQControl:
    
    def __init__(self, acquisition_type,
                 setup_file=None,
                 daq_config_file=None,
                 channels=None,
                 adc_channels=None,
                 data_purpose='test',
                 driver_name='polaris',
                 verbose=True):
        """
        Data Acquisition control for different types
        """
        
        # ---------------------
        # check arguments
        # ---------------------
        
        acquisition_types = ['continuous', 'didv', 'iv',
                             'accel_freq_sweep',
                             'exttrig', 'randoms',
                             'threshold', 'calibration']
        if  acquisition_type not in  acquisition_types:
            raise ValueError(
                f'DAQControl: Acquisition type {acquisition_type} '
                f'is not recognized!'
            )

        if (setup_file is None or daq_config_file is None):
            raise ValueError('DAQControl: setup and daq configuration files '
                             'need to be provided!')
        else:

            # check files exist
            if not os.path.isfile(setup_file):
                raise ValueError(f'DAQControl: Instruments setup file '
                                 f'"{setup_file}" not found!')
            
            if not os.path.isfile(daq_config_file):
                raise ValueError(f'DAQControl: Data taking configuration file '
                                 f'"{daq_config_file}" not found!')
            
        # store some variables
        self._verbose = verbose
        self._driver_name = driver_name
        self._acquisition_type = acquisition_type
        self._data_purpose = data_purpose
        self._setup_file = setup_file

        # -----------------------
        # User configuration
        # ------------------------
        self._config = settings.Config(setup_file=setup_file,
                                       daq_file=daq_config_file)

        # get wiring connection table
        self._connection_dataframe = self._config.get_adc_connections()
        self._connection_dict = connection_utils.get_items(
            self._connection_dataframe
        )

        # channels
        self._channels_dict = self._get_channels_dict(channels, adc_channels)
              
        # read daq config
        self._daq_config = dict()
        self._daq_config[acquisition_type] = self._config.get_daq_config(acquisition_type)
        self._daq_config['didv'] = self._config.get_daq_config('didv')
        self._daq_config['iv'] = self._config.get_daq_config('iv')
        self._daq_config['calibration'] = self._config.get_daq_config('calibration')

             
        # -----------------------
        # instruments control
        # -----------------------
        self._instruments_inst = instrument.Control(
            setup_file=setup_file,
            verbose=verbose
        )
        self._current_signal_gen = self._read_signal_gen()
        self._current_tes_bias = self._read_tes_bias()

        # ------------------------
        # IV/dIdV/calibration specific
        # configuration
        # ------------------------

        self._iv_didv_config = self._get_iv_didv_configuration()
        self._calibration_config = self._get_calibration_configuration()
      
        
        #-------------------------
        # ADC setup(s)
        # ------------------------

        adc_setup_default = dict()
        for adc_id in self._channels_dict['adc_ids']:
            adc_setup_default[adc_id] = self._config.get_adc_setup(adc_id)
            
        # ADC setup
        self._adc_config = dict()
        self._adc_config[acquisition_type] = self._get_adc_configuration(
            acquisition_type,
            adc_setup_default
        )

        # IV/dIdV ADC setup  (for beginning/end series IV/dIdV)
        if (self._iv_didv_config['didv']['channels'] is not None
            and self._daq_config['didv'] is not None):
            self._adc_config['didv'] = self._get_adc_configuration(
                'didv',
                adc_setup_default
            )

        if (self._iv_didv_config['iv']['channels'] is not None
            and self._daq_config['iv'] is not None):
            self._adc_config['iv'] = self._get_adc_configuration(
                'iv',
                adc_setup_default
            )
            
    def run(self, duration=None, comment='No Comment'):
        """
        run daq
        """

        # get adc and daq  config
        # for the acquisition type
        
        daq_config = copy.deepcopy(
            self._daq_config[self._acquisition_type]
        )
        adc_config = copy.deepcopy(
            self._adc_config[self._acquisition_type]
        )
    
        # -----------------------
        # duration and number of
        # series
        # -----------------------
        
        if duration is None:
            raise ValueError('DAQControl: "duration" is required!')
        
        duration_sec = arg_utils.convert_to_seconds(duration)

        # individual series time
        nb_runs = 1
        series_time_sec =  duration_sec
        
        if 'series_max_time' in self._daq_config[self._acquisition_type].keys():
            series_max_time_sec = (
                arg_utils.convert_to_seconds(
                    self._daq_config[self._acquisition_type]['series_max_time']
                )
            )
            nb_runs = int(round(duration_sec/series_max_time_sec))
            if nb_runs < 1:
                nb_runs = 1
            else:
                series_time_sec = series_max_time_sec

        if self._verbose:
            series_time_val = series_time_sec
            series_time_unit = 'seconds'
            if series_time_sec > 120:
                series_time_val = series_time_sec/60
                series_time_unit = 'minutes'
            series_time_string = f'{series_time_val:.2g}'
                
            if nb_runs > 1:
                print(f'INFO: Data taking will be divided in '
                      f'{nb_runs} series of {series_time_string} '
                      f'{series_time_unit} each!')
            else:
                 print(f'INFO: Data taking duration = '
                       f'{series_time_string} {series_time_unit}!')
            
        
        # -----------------------
        # group name/path
        # -----------------------
        # build output path
        group_name, group_path, group_timestamp = (
            self._create_output_path()
        )
        if self._verbose:
            print(f'INFO: Data taking group = {group_name}')
            print(f'INFO: Ouput Directory = {group_path}')
            
    
        # -----------------------
        # Run DAQ
        # -----------------------

        # initialize
        mydaq = DAQ(driver_name=self._driver_name,
                    verbose=self._verbose,
                    setup_file=self._setup_file)
        
        
        # data taking process lock 
        mydaq.lock_daq = True
            
        # raw data prefix
        data_prefix = 'raw'
        if self._acquisition_type == 'continuous':
            data_prefix = 'cont'
        elif self._acquisition_type == 'didv':
            data_prefix = 'didv'
        elif self._acquisition_type == 'accel_freq_sweep':
            data_prefix = 'accel_freq_sweep'
        elif self._acquisition_type == 'exttrig':
            data_prefix = 'exttrig'
        elif self._acquisition_type == 'threshold':
            data_prefix = 'thresh'
        elif self._acquisition_type == 'randoms':
            data_prefix = 'rand'
        elif self._acquisition_type == 'calibration':
            data_prefix = 'cont'

            
        # keep in a list
        raw_prefix_list = [data_prefix]
            
        # split restricted/open
        split_series = False
        if ('split_series' in daq_config
            and bool(daq_config['split_series'])):
            split_series = True

        if split_series:
            series_time_sec = series_time_sec//2
            raw_prefix_list = [f'restricted_{data_prefix}',
                               f'open_{data_prefix}']

        # didv / iv / calib config
        didv_config = self._iv_didv_config['didv']
        iv_config = self._iv_didv_config['iv']
        calib_config = copy.deepcopy(self._calibration_config)
               
        # loop sub-runs
        for irun in range(nb_runs):

            if self._verbose:
                print('\n===========================================')
                print(f'INFO: Starting series #{irun+1} '
                      f' (out of {nb_runs} total)')
                print('===========================================')
                
                
            # --------------------
            # Calibration
            # (Beg of Series)
            # --------------------
            if (self._acquisition_type == 'calibration'
                or calib_config['do_beginning_series']):

                # calib config
                calib_prefix = data_prefix
                calib_comment = comment
                calib_runtime = series_time_sec
                           
                if calib_config['do_beginning_series']:
                    calib_prefix = 'calib_bor'
                    calib_comment = 'Beginning of Series Calibration'
                    calib_runtime = calib_config['run_time']

                # run daq
                self._run_calib(mydaq,
                                run_time=calib_runtime,
                                run_comment=calib_comment,
                                group_name=group_name,
                                group_comment=comment,
                                group_time=group_timestamp,
                                data_prefix=calib_prefix,
                                data_path=group_path)
                
                # done is calib only acquisition
                if self._acquisition_type == 'calibration':
                    continue
                
            # --------------------
            # dIdV (Beg of Series)
            # --------------------
            if (self._acquisition_type == 'didv'
                or didv_config['series']['do_beginning_series']):

                # didv config
                didv_prefix = data_prefix
                didv_comment = comment
                didv_runtime = series_time_sec
                           
                if didv_config['series']['do_beginning_series']:
                    didv_prefix = 'didv_bor'
                    didv_comment = 'Beginning of Series dIdV'
                    didv_runtime = didv_config['series']['run_time']

                # run daq
                self._run_didv(mydaq,
                               run_time=didv_runtime,
                               run_comment=didv_comment,
                               group_name=group_name,
                               group_comment=comment,
                               group_time=group_timestamp,
                               data_prefix=didv_prefix,
                               data_path=group_path)
                
                # done is didv only acquisition
                if self._acquisition_type == 'didv':
                    continue

            # --------------------
            # IV (Beg of Series)
            # --------------------
            if (self._acquisition_type == 'iv'
                or iv_config['series']['do_beginning_series']):

                # iv config
                iv_prefix = data_prefix
                iv_comment = comment
                iv_runtime = series_time_sec
                           
                if iv_config['series']['do_beginning_series']:
                    iv_prefix = 'iv_bor'
                    iv_comment = 'Beginning of Series IV'
                    iv_runtime = iv_config['series']['run_time']

                # run daq
                self._run_iv(mydaq,
                             run_time=iv_runtime,
                             run_comment=iv_comment,
                             group_name=group_name,
                             group_comment=comment,
                             group_time=group_timestamp,
                             data_prefix=iv_prefix,
                             data_path=group_path)
                
                # done is iv only acquisition
                if self._acquisition_type == 'iv':
                    continue

            # --------------------
            # Accel freq sweep
            # (Beg of Series)
            # --------------------
            if self._acquisition_type == 'accel_freq_sweep':

                # accel freq sweep config
                sweep_prefix = data_prefix
                sweep_comment = comment

                # run daq
                self._run_accel_freq_sweep(
                    mydaq,
                    run_comment=sweep_comment,
                    group_name=group_name,
                    group_comment=comment,
                    group_time=group_timestamp,
                    data_prefix=sweep_prefix,
                    data_path=group_path
                )

                # done if accel_freq_sweep only acquisition
                continue
            
                
            # for split series, reverse order each time
            # so we reverse order of restricted/open
            # series datasets
            if split_series:
                raw_prefix_list.reverse()

            # --------------------
            # Loop restricted/open
            # if split series and
            # take regular data
            # --------------------
            if self._verbose:
                print('-------------------------------------')
                print(f'INFO: Starting {self._acquisition_type} '
                      f'data taking')
                print('-------------------------------------')
            # Loop data prefix
            #   - one series if not split,
            #   - restricted/open series is split
            for raw_prefix in raw_prefix_list:

                # restricted/open
                restricted = False
                if split_series:
                    if 'restricted' in raw_prefix:
                        restricted = True
                    if self._verbose:
                        if restricted:
                            print(f'INFO: Starting "restricted" series!')
                        else:
                            print(f'INFO: Starting "open" series!')


                # set adc
                mydaq.set_adc_config_from_dict(adc_config)
                
                # set detector config
                detector_config = self._read_detector_settings(adc_config)
                mydaq.set_detector_config(detector_config)
                time.sleep(2)
                
                # take data
                success = mydaq.run(run_time=series_time_sec,
                                    run_type=self._data_purpose,
                                    run_comment=comment,
                                    group_name=group_name,
                                    group_comment=comment,
                                    group_time=group_timestamp,
                                    data_prefix=raw_prefix,
                                    data_path=group_path,
                                    restricted=restricted)
                if not success:
                    mydaq.clear()
                    print('ERROR: Problem with data taking. Exiting!')
                    return

                
            # --------------------
            # Calibration
            # (end of series)
            # --------------------
            
            if calib_config['do_end_series']:

                # calib config
                calib_prefix = 'calib_eor'
                calib_comment = 'End of Series Calibration'
                calib_runtime = calib_config['run_time']
                
                # run daq
                self._run_calib(mydaq,
                                run_time=calib_runtime,
                                run_comment=calib_comment,
                                group_name=group_name,
                                group_comment=comment,
                                group_time=group_timestamp,
                                data_prefix=calib_prefix,
                                data_path=group_path)
            # --------------------
            # dIdV (End of series)
            # --------------------
            if didv_config['series']['do_end_series']:

                # didv config
                didv_prefix = 'didv_eor'
                didv_comment = 'End of Series dIdV'
                didv_runtime = didv_config['series']['run_time']

                # run daq
                self._run_didv(mydaq,
                               run_time=didv_runtime,
                               run_comment=didv_comment,
                               group_name=group_name,
                               group_comment=comment,
                               group_time=group_timestamp,
                               data_prefix=didv_prefix,
                               data_path=group_path)
             
            # --------------------
            # IV (End of series)
            # --------------------
            if iv_config['series']['do_end_series']:

                iv_prefix = 'iv_eor'
                iv_comment = 'End of Series IV'
                iv_runtime = iv_config['series']['run_time']
                
                # run daq
                self._run_iv(mydaq,
                             run_time=iv_runtime,
                             run_comment=iv_comment,
                             group_name=group_name,
                             group_comment=comment,
                             group_time=group_timestamp,
                             data_prefix=iv_prefix,
                             data_path=group_path)
        # cleanup
        if self._verbose:
            print(f'INFO: Data taking for group {group_name} '
                  f'successfully done!')
            print(f'INFO: Ouput Directory = {group_path}')
            
        mydaq.clear()
    
    def _run_didv(self, daq_inst,
                  run_time=None,
                  run_comment=None,
                  group_name=None,
                  group_comment=None,
                  group_time=None,
                  data_prefix=None,
                  data_path=None):
        """
        Function to run dIdV
        """
        
        if self._verbose:
            print('\n-------------------------------------')
            print(f'INFO: Starting dIdV\n'
                  f'({run_comment})')
            print('-------------------------------------')
                  
        if run_time is None:
            daq_inst.clear()
            raise ValueError('DAQControl: didv run time missing!')

        # didv config
        didv_config = self._iv_didv_config['didv']
        tes_bias_list = didv_config['tes_bias_list']
        didv_channels = didv_config['channels']
        signal_gen_config = didv_config['signal_gen']
        runlist_channels = signal_gen_config['runlist_channels']

        # check if TES bias will be modified
        modify_tes = False
        if (len(tes_bias_list) > 1
            or tes_bias_list[0] != 'current'):
            modify_tes = True


        # ------------------
        # Loop tes bias
        # ------------------
        step_num = 0
        for tes_bias in tes_bias_list:

            # modify TES bias
            if modify_tes:
                
                for chan in didv_channels:

                    tes_bias_input = tes_bias
                    if tes_bias == 'current':
                        tes_bias_input = self._current_tes_bias[chan]

                    self._instruments_inst.set_tes_bias(
                        tes_bias_input, unit='uA',
                        detector_channel=chan
                    )

            # relock
            if ((step_num == 0
                 and didv_config['relock_first_step'])
                or  didv_config['relock_all_steps']):

                for chan in didv_channels:
                    self._instruments_inst.relock(
                        detector_channel=chan
                    )
                    
                step_num += 1
                
            # ------------------
            # loop didv channel
            # sub-lists
            # ------------------
            for channels in runlist_channels:

                # get list of channels that shouldn't have
                # signal gen connected
                other_channels = list()
                for chan in self._channels_dict['detector_channels']:
                    if chan not in channels:
                        other_channels.append(chan)

                # Set signal generator
                for chan in channels:
                    
                    voltage = 1e3*signal_gen_config[chan]['voltage']
                    frequency = signal_gen_config[chan]['frequency']
                                                 
                    # set signal gen
                    self._instruments_inst.set_signal_gen_params(
                        detector_channel=chan,
                        voltage=voltage, voltage_unit='mV',
                        frequency=frequency,
                        shape='square')
                
                    # turn output on
                    self._instruments_inst.set_signal_gen_onoff(
                        'on',
                        detector_channel=chan
                    )

                    # connect to TES
                    self._instruments_inst.connect_signal_gen_to_tes(
                        True, detector_channel=chan
                    )
             
                # Disconnect "other"
                # channels
                for other_chan in  other_channels:

                    # disconnect to TES
                    self._instruments_inst.connect_signal_gen_to_tes(
                        False, detector_channel=other_chan)

                # Take data

                # configure ADC
                adc_config = copy.deepcopy(self._adc_config['didv'])
                daq_inst.set_adc_config_from_dict(adc_config)

                # set detector config
                detector_config = self._read_detector_settings(adc_config)
                daq_inst.set_detector_config(detector_config)
                time.sleep(2)
            
                # run
                success = daq_inst.run(
                    run_time=run_time,
                    run_type=self._data_purpose,
                    run_comment=run_comment,
                    group_name=group_name,
                    group_comment=group_comment,
                    group_time=group_time,
                    data_prefix=data_prefix,
                    data_path=data_path)

                if not success:
                    daq_inst.clear()
                    print('ERROR: Problem with data taking. Exiting!')
                    return

                # -----------------------
                # Disconnect signal
                # generator
                # -----------------------
                for chan in channels:

                    # disconnect to TES
                    self._instruments_inst.connect_signal_gen_to_tes(
                        False, detector_channel=chan)
                    
        # all done -> turn off signal gen
        for chan in didv_channels:

            # disconnect to TES
            self._instruments_inst.connect_signal_gen_to_tes(
                False, detector_channel=chan)

            # turn output off
            if not self._instruments_inst.is_tes_signal_gen_inst_common():
                self._instruments_inst.set_signal_gen_onoff(
                    'off',
                    detector_channel=chan
                )

            # set TES
            if modify_tes:
                tes_bias_input = self._current_tes_bias[chan]
                self._instruments_inst.set_tes_bias(
                    tes_bias_input, unit='uA',
                    detector_channel=chan
                )

                # relock
                if didv_config['relock_all_steps']:
                    self._instruments_inst.relock(
                        detector_channel=chan
                    )
                
        time.sleep(2)

        
    def _run_iv(self, daq_inst,
                run_time=None,
                run_comment=None,
                group_name=None,
                group_comment=None,
                group_time=None,
                data_prefix=None,
                data_path=None):
        """
        Function to run IV
        """

        if self._verbose:
                print('\n-------------------------------------')
                print(f'INFO: Starting IV\n'
                      f'({run_comment})')
                print('-------------------------------------')
  
        if run_time is None:
            daq_inst.clear()
            raise ValueError('DAQControl: didv run time missing!')

        # didv config
        iv_config = self._iv_didv_config['iv']
        tes_bias_list = iv_config['tes_bias_list']
        iv_channels = iv_config['channels']
        
        # ------------------
        # Loop tes bias
        # ------------------
        step_num = 0
        for tes_bias in tes_bias_list:

            # set tes bias
            for chan in  iv_channels:

                tes_bias_input = tes_bias
                if tes_bias == 'current':
                    tes_bias_input = self._current_tes_bias[chan]

                self._instruments_inst.set_tes_bias(
                    tes_bias_input, unit='uA',
                    detector_channel=chan
                )

            # relock
            if ((step_num == 0
                 and iv_config['relock_first_step'])
                or iv_config['relock_all_steps']):

                for chan in iv_channels:
                    self._instruments_inst.relock(
                        detector_channel=chan
                    )
                
                step_num += 1
                
            # Take data
            
            # configure ADC
            adc_config = copy.deepcopy(self._adc_config['iv'])
            daq_inst.set_adc_config_from_dict(adc_config)
            
            # set detector config
            detector_config = self._read_detector_settings(adc_config)
            daq_inst.set_detector_config(detector_config)
            time.sleep(2)
            
            # run
            success = daq_inst.run(
                run_time=run_time,
                run_type=self._data_purpose,
                run_comment=run_comment,
                group_name=group_name,
                group_comment=group_comment,
                group_time=group_time,
                data_prefix=data_prefix,
                data_path=data_path)

            if not success:
                daq_inst.clear()
                print('ERROR: Problem with data taking. Exiting!')
                return


        for chan in  iv_channels:
            
            tes_bias_input = self._current_tes_bias[chan]

            self._instruments_inst.set_tes_bias(
                tes_bias_input, unit='uA',
                detector_channel=chan
            )

            # relock
            if iv_config['relock_all_steps']:
                self._instruments_inst.relock(
                    detector_channel=chan
                )
             
        time.sleep(2)

        
    def _run_accel_freq_sweep(self, daq_inst,
                              run_comment=None,
                              group_name=None,
                              group_comment=None,
                              group_time=None,
                              data_prefix=None,
                              data_path=None):
        """
        Function to run accel frequency/amplitude sweep acquisition.

        Parameters
        ----
        daq_inst : DAQ
            DAQ instance to execute data taking.
        run_comment : str
            Comment for the sweep acquisition.
        group_name : str
            Data group name.
        group_comment : str
            Group comment stored in metadata.
        group_time : str
            Group timestamp string.
        data_prefix : str
            Prefix for raw data files.
        data_path : str
            Output path for raw data files.

        Return
        ---
        None
        """

        if self._verbose:
            print('\n-------------------------------------')
            print(f'INFO: Starting accel_freq_sweep\n'
                  f'({run_comment})')
            print('-------------------------------------')

        daq_config = copy.deepcopy(
            self._daq_config['accel_freq_sweep']
        )

        if daq_config is None:
            daq_inst.clear()
            raise ValueError('DAQControl: accel_freq_sweep config missing!')

        if 'sweep_run_time' not in daq_config:
            daq_inst.clear()
            raise ValueError('DAQControl: "sweep_run_time" required for '
                             'accel_freq_sweep!')

        run_time_default = arg_utils.convert_to_seconds(
            daq_config['sweep_run_time']
        )

        freq_config = self._get_accel_freq_sweep_frequency_config(
            daq_config=daq_config,
            run_time_default=run_time_default
        )
        amp_config = self._get_accel_freq_sweep_amplitude_config(
            daq_config=daq_config,
            run_time_default=run_time_default
        )

        if (not freq_config['enabled']
            and not amp_config['enabled']):
            daq_inst.clear()
            raise ValueError('DAQControl: accel_freq_sweep requires at least '
                             'one of frequency or amplitude sweep to be enabled!')

        detector_channels = (
            self._channels_dict['detector_channels'].copy()
        )

        # Turn on signal generator for all detector channels.
        for chan in detector_channels:
            self._instruments_inst.set_signal_gen_onoff(
                'on',
                detector_channel=chan
            )

        # ------------------
        # Frequency sweep
        # ------------------
        if freq_config['enabled']:
            frequency_list = freq_config['frequencies_hz']
            amplitude_vpp = freq_config['amplitude_vpp']
            hold_time_s = freq_config['hold_time_s']
            run_time_s = freq_config['run_time_s']

            # Loop over frequency sweep points and take data at each setting.
            for frequency_hz in frequency_list:
                self._set_signal_generator_for_sweep(
                    detector_channels=detector_channels,
                    amplitude_vpp=amplitude_vpp,
                    frequency_hz=frequency_hz
                )

                if hold_time_s > 0:
                    time.sleep(hold_time_s)

                self._run_sweep_step(
                    daq_inst=daq_inst,
                    daq_config=daq_config,
                    frequency_hz=frequency_hz,
                    amplitude_vpp=amplitude_vpp,
                    run_time_s=run_time_s,
                    run_comment=run_comment,
                    group_name=group_name,
                    group_comment=group_comment,
                    group_time=group_time,
                    data_prefix=data_prefix,
                    data_path=data_path
                )

        # ------------------
        # Amplitude sweep
        # ------------------
        if amp_config['enabled']:
            amplitude_list = amp_config['amplitudes_vpp']
            frequency_hz = amp_config['frequency_hz']
            hold_time_s = amp_config['hold_time_s']
            run_time_s = amp_config['run_time_s']

            # Loop over amplitude sweep points and take data at each setting.
            for amplitude_vpp in amplitude_list:
                self._set_signal_generator_for_sweep(
                    detector_channels=detector_channels,
                    amplitude_vpp=amplitude_vpp,
                    frequency_hz=frequency_hz
                )

                if hold_time_s > 0:
                    time.sleep(hold_time_s)

                self._run_sweep_step(
                    daq_inst=daq_inst,
                    daq_config=daq_config,
                    frequency_hz=frequency_hz,
                    amplitude_vpp=amplitude_vpp,
                    run_time_s=run_time_s,
                    run_comment=run_comment,
                    group_name=group_name,
                    group_comment=group_comment,
                    group_time=group_time,
                    data_prefix=data_prefix,
                    data_path=data_path
                )

        # Turn off signal generator when finished.
        if not self._instruments_inst.is_tes_signal_gen_inst_common():
            # Loop over detector channels to disable outputs.
            for chan in detector_channels:
                self._instruments_inst.set_signal_gen_onoff(
                    'off',
                    detector_channel=chan
                )

        time.sleep(2)

    def _run_sweep_step(self, daq_inst,
                        daq_config=None,
                        frequency_hz=None,
                        amplitude_vpp=None,
                        run_time_s=None,
                        run_comment=None,
                        group_name=None,
                        group_comment=None,
                        group_time=None,
                        data_prefix=None,
                        data_path=None):
        """
        Take a single accel_freq_sweep data step.

        Parameters
        ----
        daq_inst : DAQ
            DAQ instance to execute data taking.
        daq_config : dict
            DAQ configuration dictionary for accel_freq_sweep.
        frequency_hz : float
            Signal generator frequency in Hz.
        amplitude_vpp : float
            Signal generator amplitude in Vpp.
        run_time_s : float
            Run time for the sweep step in seconds.
        run_comment : str
            Comment for the sweep acquisition.
        group_name : str
            Data group name.
        group_comment : str
            Group comment stored in metadata.
        group_time : str
            Group timestamp string.
        data_prefix : str
            Prefix for raw data files.
        data_path : str
            Output path for raw data files.

        Return
        ---
        None
        """

        if run_time_s is None:
            daq_inst.clear()
            raise ValueError('DAQControl: accel_freq_sweep step run time missing!')

        adc_config = self._get_accel_freq_sweep_adc_config(
            daq_config=daq_config,
            frequency_hz=frequency_hz
        )

        # configure ADC
        daq_inst.set_adc_config_from_dict(adc_config)

        # set detector config
        detector_config = self._read_detector_settings(adc_config)
        daq_inst.set_detector_config(detector_config)
        time.sleep(2)

        comment_parts = list()
        if run_comment:
            comment_parts.append(run_comment)
        comment_parts.append(
            f'freq={float(frequency_hz):.6g} Hz'
        )
        comment_parts.append(
            f'amp={float(amplitude_vpp):.6g} Vpp'
        )
        step_comment = ' | '.join(comment_parts)

        success = daq_inst.run(
            run_time=run_time_s,
            run_type=self._data_purpose,
            run_comment=step_comment,
            group_name=group_name,
            group_comment=group_comment,
            group_time=group_time,
            data_prefix=data_prefix,
            data_path=data_path
        )

        if not success:
            daq_inst.clear()
            print('ERROR: Problem with data taking. Exiting!')
            return

    def _set_signal_generator_for_sweep(self, detector_channels=None,
                                        amplitude_vpp=None,
                                        frequency_hz=None):
        """
        Configure the signal generator for accel_freq_sweep.

        Parameters
        ----
        detector_channels : list
            List of detector channels to configure.
        amplitude_vpp : float
            Signal generator amplitude in Vpp.
        frequency_hz : float
            Signal generator frequency in Hz.

        Return
        ---
        None
        """

        # Loop over detector channels to set the same generator settings.
        for chan in detector_channels:
            self._instruments_inst.set_signal_gen_params(
                detector_channel=chan,
                voltage=amplitude_vpp,
                voltage_unit='Vpp',
                frequency=frequency_hz,
                frequency_unit='Hz',
                shape='sine',
                offset=0.0,
                offset_unit='V',
                phase=0.0
            )

    def _get_accel_freq_sweep_adc_config(self, daq_config=None,
                                         frequency_hz=None):
        """
        Build the ADC configuration for accel_freq_sweep steps.

        Parameters
        ----
        daq_config : dict
            DAQ configuration dictionary for accel_freq_sweep.
        frequency_hz : float
            Current sweep frequency in Hz.

        Return
        ---
        adc_config : dict
            ADC configuration updated for the sweep step.
        """

        adc_config = copy.deepcopy(
            self._adc_config['accel_freq_sweep']
        )

        if 'nb_cycles' in daq_config.keys():
            if frequency_hz is None or frequency_hz <= 0:
                raise ValueError('DAQControl: "nb_cycles" requires a positive '
                                 'frequency_hz value for accel_freq_sweep!')

            sample_rate = None
            # Read sample rate from the first ADC entry.
            for adc_id in adc_config.keys():
                sample_rate = adc_config[adc_id]['sample_rate']
                break

            nb_cycles = float(daq_config['nb_cycles'])
            nb_samples = int(
                round(nb_cycles * sample_rate / float(frequency_hz))
            )

            # Loop over ADC configs to update nb_samples.
            for adc_id in adc_config.keys():
                adc_config[adc_id]['nb_samples'] = nb_samples

        return adc_config

    def _get_accel_freq_sweep_frequency_config(self, daq_config=None,
                                               run_time_default=None):
        """
        Parse the frequency sweep configuration.

        Parameters
        ----
        daq_config : dict
            DAQ configuration dictionary for accel_freq_sweep.
        run_time_default : float
            Default run time in seconds for each sweep step.

        Return
        ---
        freq_config : dict
            Parsed frequency sweep configuration.
        """

        output_config = {'enabled': True}

        if 'do_frequency_sweep' in daq_config:
            output_config['enabled'] = bool(
                daq_config['do_frequency_sweep']
            )

        if not output_config['enabled']:
            return output_config

        if 'amplitude_vpp' not in daq_config:
            raise ValueError('DAQControl: "amplitude_vpp" required for '
                             'accel_freq_sweep frequency sweep!')
        if 'start_frequency_hz' not in daq_config:
            raise ValueError('DAQControl: "start_frequency_hz" required for '
                             'accel_freq_sweep frequency sweep!')
        if 'stop_frequency_hz' not in daq_config:
            raise ValueError('DAQControl: "stop_frequency_hz" required for '
                             'accel_freq_sweep frequency sweep!')

        points = None
        if 'frequency_points' in daq_config:
            points = daq_config['frequency_points']
        elif 'points' in daq_config:
            points = daq_config['points']

        if points is None:
            raise ValueError('DAQControl: "frequency_points" required for '
                             'accel_freq_sweep frequency sweep!')

        spacing = 'linear'
        if 'frequency_spacing' in daq_config:
            spacing = daq_config['frequency_spacing']

        hold_time_s = 0.0
        if 'frequency_hold_time_s' in daq_config:
            hold_time_s = arg_utils.convert_to_seconds(
                daq_config['frequency_hold_time_s']
            )

        focus_frequencies_hz = None
        if 'focus_frequencies_hz' in daq_config:
            focus_frequencies_hz = daq_config['focus_frequencies_hz']

        focus_freqs_width_hz = 2.0
        if 'focus_freqs_width_hz' in daq_config:
            focus_freqs_width_hz = float(daq_config['focus_freqs_width_hz'])

        focus_freqs_spacing_hz = 0.2
        if 'focus_freqs_spacing_hz' in daq_config:
            focus_freqs_spacing_hz = float(
                daq_config['focus_freqs_spacing_hz']
            )

        sweep_config = {
            'amplitude_vpp': float(daq_config['amplitude_vpp']),
            'start_frequency_hz': float(daq_config['start_frequency_hz']),
            'stop_frequency_hz': float(daq_config['stop_frequency_hz']),
            'points': int(points),
            'spacing': str(spacing).lower().strip(),
            'focus_frequencies_hz': focus_frequencies_hz,
            'focus_freqs_width_hz': focus_freqs_width_hz,
            'focus_freqs_spacing_hz': focus_freqs_spacing_hz
        }

        frequencies_hz = self._build_sweep_frequencies(
            sweep_config=sweep_config
        )

        run_time_s = run_time_default
        if 'frequency_run_time' in daq_config:
            run_time_s = arg_utils.convert_to_seconds(
                daq_config['frequency_run_time']
            )

        output_config['frequencies_hz'] = frequencies_hz
        output_config['amplitude_vpp'] = sweep_config['amplitude_vpp']
        output_config['hold_time_s'] = hold_time_s
        output_config['run_time_s'] = run_time_s

        return output_config

    def _get_accel_freq_sweep_amplitude_config(self, daq_config=None,
                                               run_time_default=None):
        """
        Parse the amplitude sweep configuration.

        Parameters
        ----
        daq_config : dict
            DAQ configuration dictionary for accel_freq_sweep.
        run_time_default : float
            Default run time in seconds for each sweep step.

        Return
        ---
        amp_config : dict
            Parsed amplitude sweep configuration.
        """

        output_config = {'enabled': True}

        if 'do_amplitude_sweep' in daq_config:
            output_config['enabled'] = bool(
                daq_config['do_amplitude_sweep']
            )

        if not output_config['enabled']:
            return output_config

        if 'frequency_hz' not in daq_config:
            raise ValueError('DAQControl: "frequency_hz" required for '
                             'accel_freq_sweep amplitude sweep!')
        if 'start_amplitude_vpp' not in daq_config:
            raise ValueError('DAQControl: "start_amplitude_vpp" required for '
                             'accel_freq_sweep amplitude sweep!')
        if 'stop_amplitude_vpp' not in daq_config:
            raise ValueError('DAQControl: "stop_amplitude_vpp" required for '
                             'accel_freq_sweep amplitude sweep!')

        points = None
        if 'amplitude_points' in daq_config:
            points = daq_config['amplitude_points']
        elif 'points' in daq_config:
            points = daq_config['points']

        if points is None:
            raise ValueError('DAQControl: "amplitude_points" required for '
                             'accel_freq_sweep amplitude sweep!')

        spacing = 'linear'
        if 'amplitude_spacing' in daq_config:
            spacing = daq_config['amplitude_spacing']

        hold_time_s = 0.0
        if 'amplitude_hold_time_s' in daq_config:
            hold_time_s = arg_utils.convert_to_seconds(
                daq_config['amplitude_hold_time_s']
            )

        sweep_config = {
            'frequency_hz': float(daq_config['frequency_hz']),
            'start_amplitude_vpp': float(daq_config['start_amplitude_vpp']),
            'stop_amplitude_vpp': float(daq_config['stop_amplitude_vpp']),
            'points': int(points),
            'spacing': str(spacing).lower().strip()
        }

        amplitudes_vpp = self._build_sweep_amplitudes(
            sweep_config=sweep_config
        )

        run_time_s = run_time_default
        if 'amplitude_run_time' in daq_config:
            run_time_s = arg_utils.convert_to_seconds(
                daq_config['amplitude_run_time']
            )

        output_config['amplitudes_vpp'] = amplitudes_vpp
        output_config['frequency_hz'] = sweep_config['frequency_hz']
        output_config['hold_time_s'] = hold_time_s
        output_config['run_time_s'] = run_time_s

        return output_config

    def _build_sweep_frequencies(self, sweep_config=None):
        """
        Build the frequency sweep list, including focus frequencies.

        Parameters
        ----
        sweep_config : dict
            Frequency sweep configuration dictionary.

        Return
        ---
        frequencies_hz : list
            List of sweep frequencies in Hz.
        """

        spacing = str(sweep_config['spacing']).lower().strip()
        if spacing not in ['linear', 'log']:
            raise ValueError('DAQControl: "spacing" must be "linear" or "log"!')

        start_frequency_hz = float(sweep_config['start_frequency_hz'])
        stop_frequency_hz = float(sweep_config['stop_frequency_hz'])
        points = int(sweep_config['points'])

        if points < 1:
            raise ValueError('DAQControl: "points" must be >= 1!')

        base_frequencies = list()
        if spacing == 'linear':
            if points == 1:
                base_frequencies = [float(start_frequency_hz)]
            else:
                step = (
                    (stop_frequency_hz - start_frequency_hz)
                    / (points - 1)
                )
                # Loop over indices to build linear spacing.
                for idx in range(points):
                    base_frequencies.append(
                        start_frequency_hz + (idx * step)
                    )
        else:
            if start_frequency_hz <= 0 or stop_frequency_hz <= 0:
                raise ValueError('DAQControl: log spacing requires '
                                 'start/stop > 0!')
            if points == 1:
                base_frequencies = [float(start_frequency_hz)]
            else:
                log_start = np.log10(start_frequency_hz)
                log_stop = np.log10(stop_frequency_hz)
                step = (log_stop - log_start) / (points - 1)
                # Loop over indices to build log spacing.
                for idx in range(points):
                    base_frequencies.append(
                        10 ** (log_start + (idx * step))
                    )

        focus_frequencies_hz = self._parse_focus_frequencies(
            sweep_config.get('focus_frequencies_hz', None)
        )

        focus_frequency_list = list()
        if focus_frequencies_hz:
            focus_freqs_width_hz = float(
                sweep_config.get('focus_freqs_width_hz', 2.0)
            )
            focus_freqs_spacing_hz = float(
                sweep_config.get('focus_freqs_spacing_hz', 0.2)
            )

            if focus_freqs_width_hz <= 0:
                raise ValueError('DAQControl: "focus_freqs_width_hz" must be > 0!')
            if focus_freqs_spacing_hz <= 0:
                raise ValueError('DAQControl: "focus_freqs_spacing_hz" must be > 0!')

            # Loop over focus frequencies to add dense points.
            for focus_frequency in focus_frequencies_hz:
                half_width = focus_freqs_width_hz / 2.0
                focus_start = float(focus_frequency) - half_width
                focus_stop = float(focus_frequency) + half_width
                focus_points = np.arange(
                    focus_start,
                    focus_stop + (0.5 * focus_freqs_spacing_hz),
                    focus_freqs_spacing_hz
                )
                # Loop over focus points to append them.
                for focus_point in focus_points:
                    focus_frequency_list.append(float(focus_point))

        combined_frequencies = (
            base_frequencies + focus_frequency_list
        )

        unique_frequency_set = set()
        # Loop over combined frequencies to ensure uniqueness.
        for freq in combined_frequencies:
            unique_frequency_set.add(float(freq))

        unique_frequencies = sorted(unique_frequency_set)

        return unique_frequencies

    def _build_sweep_amplitudes(self, sweep_config=None):
        """
        Build the amplitude sweep list.

        Parameters
        ----
        sweep_config : dict
            Amplitude sweep configuration dictionary.

        Return
        ---
        amplitudes_vpp : list
            List of sweep amplitudes in Vpp.
        """

        spacing = str(sweep_config['spacing']).lower().strip()
        if spacing not in ['linear', 'log']:
            raise ValueError('DAQControl: "spacing" must be "linear" or "log"!')

        start_amplitude_vpp = float(sweep_config['start_amplitude_vpp'])
        stop_amplitude_vpp = float(sweep_config['stop_amplitude_vpp'])
        points = int(sweep_config['points'])

        if points < 1:
            raise ValueError('DAQControl: "points" must be >= 1!')

        amplitudes_vpp = list()
        if spacing == 'linear':
            if points == 1:
                amplitudes_vpp = [float(start_amplitude_vpp)]
            else:
                step = (
                    (stop_amplitude_vpp - start_amplitude_vpp)
                    / (points - 1)
                )
                # Loop over indices to build linear spacing.
                for idx in range(points):
                    amplitudes_vpp.append(
                        start_amplitude_vpp + (idx * step)
                    )
        else:
            if start_amplitude_vpp <= 0 or stop_amplitude_vpp <= 0:
                raise ValueError('DAQControl: log spacing requires '
                                 'start/stop > 0!')
            if points == 1:
                amplitudes_vpp = [float(start_amplitude_vpp)]
            else:
                log_start = np.log10(start_amplitude_vpp)
                log_stop = np.log10(stop_amplitude_vpp)
                step = (log_stop - log_start) / (points - 1)
                # Loop over indices to build log spacing.
                for idx in range(points):
                    amplitudes_vpp.append(
                        10 ** (log_start + (idx * step))
                    )

        return amplitudes_vpp

    def _parse_focus_frequencies(self, focus_frequencies=None):
        """
        Parse focus frequency inputs into a list of floats.

        Parameters
        ----
        focus_frequencies : Any
            None, a numeric value, a comma-separated string, or an iterable
            of values representing focus frequencies in Hz.

        Return
        ---
        focus_frequencies_hz : list
            Parsed focus frequencies in Hz.
        """

        if focus_frequencies is None:
            return list()

        if isinstance(focus_frequencies, str):
            focus_text = focus_frequencies.strip()
            if not focus_text:
                return list()
            focus_parts = list()
            # Loop over comma-separated values to capture valid entries.
            for item in focus_text.split(','):
                item_value = item.strip()
                if item_value:
                    focus_parts.append(item_value)
            focus_values = list()
            # Loop over focus parts to cast them as floats.
            for item in focus_parts:
                focus_values.append(float(item))
            return focus_values

        if isinstance(focus_frequencies, (list, tuple, set)):
            focus_values = list()
            # Loop over focus frequency values to cast them as floats.
            for item in focus_frequencies:
                focus_values.append(float(item))
            return focus_values

        return [float(focus_frequencies)]

    def _run_calib(self, daq_inst,
                   run_time=None,
                   run_comment=None,
                   group_name=None,
                   group_comment=None,
                   group_time=None,
                   data_prefix=None,
                   data_path=None):
        """
        Function to run laser calibration
        """

        if self._verbose:
                print('\n-------------------------------------')
                print(f'INFO: Starting Laser Calibration\n'
                      f'({run_comment})')
                print('-------------------------------------')
  
        if run_time is None:
            daq_inst.clear()
            raise ValueError('DAQControl: didv run time missing!')

        # ------------------
        # Set laser
        # ------------------

        # control
        control_channel = self._calibration_config['control_channel']
        voltage_high = self._calibration_config['control_voltage_high']
        voltage_low = self._calibration_config['control_voltage_low']
        frequency = self._calibration_config['control_frequency']
        offset = self._calibration_config['control_offset']
        pulse_width = self._calibration_config['control_pulse_width']

        # add noise
        add_calib_noise = self._calibration_config['add_calib_noise']
        calib_noise_runtime = self._calibration_config['calib_noise_runtime']
        

        self._instruments_inst.set_laser_signal_gen_params(
            signal_gen_num=control_channel,
            shape='pulse',
            voltage_high=voltage_high, voltage_low=voltage_low,
            voltage_unit='V',
            frequency=frequency,
            offset=offset, offset_unit='V',
            phase=0,
            pulse_width=pulse_width)
        
        # TTL channel
        ttl_channel = self._calibration_config['ttl_channel']
        
        if ttl_channel is not None:
            
              voltage_high = self._calibration_config['ttl_voltage_high']
              voltage_low = self._calibration_config['ttl_voltage_low']
              offset = self._calibration_config['ttl_offset']
              pulse_width = self._calibration_config['ttl_pulse_width']
              
              self._instruments_inst.set_laser_signal_gen_params(
                  signal_gen_num=ttl_channel,
                  shape='pulse',
                  voltage_high=voltage_high, voltage_low=voltage_low,
                  voltage_unit='V',
                  frequency=frequency,
                  offset=offset,
                  phase=0,  offset_unit='V',
                  pulse_width=pulse_width,
                  align_phase_channel=control_channel)
                  
        
        # ------------------
        # Enable Laser
        # signal generator
        # ------------------
        self._instruments_inst.set_laser_signal_gen_onoff(
            'on',
            load=50,
            signal_gen_num=control_channel
        )

        if ttl_channel is not None:
            self._instruments_inst.set_laser_signal_gen_onoff(
                'on',
                load=50,
                signal_gen_num=ttl_channel
            )
                
        # ------------------
        # Take data
        # ------------------

        # configure ADC
        ttl_adc_channel = self._calibration_config['ttl_adc_channel']
        ttl_adc_id = self._calibration_config['ttl_adc_id']
        
        adc_setup_default = dict()
        for adc_id in self._channels_dict['adc_ids']:
            adc_setup_default[adc_id] = self._config.get_adc_setup(adc_id)
            
        adc_config =self._get_adc_configuration(
            'calibration',
            adc_setup_default,
            ttl_adc_channel=ttl_adc_channel,
            ttl_adc_id=ttl_adc_id
        )

        daq_inst.set_adc_config_from_dict(adc_config)
            
        # set detector config
        detector_config = self._read_detector_settings(
            adc_config,
            laser_control_channel=control_channel,
            laser_ttl_channel=ttl_channel
        )
      
        daq_inst.set_detector_config(detector_config)
                
        # run
        time.sleep(1)
        success = daq_inst.run(
            run_time=run_time,
            run_type=self._data_purpose,
            run_comment=run_comment,
            group_name=group_name,
            group_comment=group_comment,
            group_time=group_time,
            data_prefix=data_prefix,
            data_path=data_path
        )
        
        if not success:
            daq_inst.clear()
            print('ERROR: Problem with data taking. Exiting!')
            return

        # ------------------
        # Disable Laser
        # signal generator
        # ------------------
        self._instruments_inst.set_laser_signal_gen_onoff(
            'off',
            signal_gen_num=control_channel
        )

        if ttl_channel is not None:
            self._instruments_inst.set_laser_signal_gen_onoff(
                'off',
                signal_gen_num=ttl_channel
            )

        time.sleep(2)

        # ------------------
        # Noise
        # ------------------
            
        if add_calib_noise:

            print(f'INFO: Taking Laser Calibration Noise\n')
                  
            
            # configurating ADC
            daq_inst.set_adc_config_from_dict(adc_config)
            
            # set detector config
            detector_config = self._read_detector_settings(
                adc_config,
                laser_control_channel=control_channel,
                laser_ttl_channel=ttl_channel
            )
            
            daq_inst.set_detector_config(detector_config)
                
            # run
            success = daq_inst.run(
                run_time=int(calib_noise_runtime),
                run_type=self._data_purpose,
                run_comment=run_comment,
                group_name=group_name,
                group_comment=group_comment,
                group_time=group_time,
                data_prefix=f'{data_prefix}_noise',
                data_path=data_path
            )
        
        if not success:
            daq_inst.clear()
            print('ERROR: Problem with data taking. Exiting!')
            return
        
                  

    def _create_output_path(self):
        """
        Create output path and make directory
        """

        # facility
        facility = str(self._config.get_facility_num())
        data_path = self._config.get_data_path()
        fridge_run  = 'run' + str(self._config.get_fridge_run())
        
        if data_path.find(fridge_run) == -1:
            data_path = data_path + '/' + fridge_run
        if 'raw' not in os.path.basename(os.path.normpath(data_path)):
            data_path += '/raw'
            
        # make base directory
        arg_utils.make_directories(data_path)
                   
        # make output group directory
        now = datetime.now()
        series_day = now.strftime('%Y') +  now.strftime('%m') + now.strftime('%d') 
        series_time = now.strftime('%H') + now.strftime('%M') +  now.strftime('%S')
        group_name = self._acquisition_type + '_I' + facility + '_D' + series_day + '_T' + series_time

        group_path = data_path + '/' + group_name
        arg_utils.make_directories(group_path)

        # time stamp
        group_timestamp = int(round(now.timestamp()))
        
        return group_name, group_path, group_timestamp
        
            
    def _get_channels_dict(self, channels=None, adc_channels=None):
        """
        Get a dictionary of channels that will
        be used for data taking
        """

        # check
        if (channels is not None
            and  adc_channels is not None):
            raise ValueError('DAQControl: both "channels" '
                             'and "adc channels" have been provided. '
                             'Choose between the two arguments!')

        
        # initialize
        channels_dict = {'detector_channels': list(),
                         'adc_channels': list(),
                         'adc_ids': list()}
        
        # 1. Find  ADC channels and ids
        if adc_channels is not None:

            # check single ADC
            if len(list(set(self._connection_dict['adc_id']))) != 1:
                raise ValueError('DAQControl: Multiple ADCs connected. '
                                 'Unable to use "adc_channel" arguments. '
                                 'Switch to detector channels "channels"!')

            for chan in adc_channels:

                if str(chan) not in self._connection_dict['adc_channel']:
                    raise ValueError(f'DAQControl: adc channel "{chan}" '
                                     f'not found in connection map!')

                # append
                channels_dict['adc_channels'].append(chan)

                # ADC ID/name:
                chan_str = str(chan)
                adc_id = self._connection_dataframe.query(
                    'adc_channel == @chan_str'
                )['adc_id'].values
                if len(adc_id) != 1:
                    raise ValueError(f'DAQControl: multiple adc channel '
                                     f'{chan} found in connection map!')
                else:
                    channels_dict['adc_ids'].append(adc_id[0])
        else:
                    
            # loop channels
            for chan in channels:

                # get channel name type
                # (detector name or readout name)
                channel_type = None
                if chan in self._connection_dict['detector_channel']:
                    channel_type = 'detector_channel'
                elif chan in self._connection_dict['tes_channel']:
                    channel_type = 'tes_channel'
                else:
                    raise ValueError(f'DAQControl: Unable  to identify '
                                     f'channel "{chan}"!')
                # convert to ADC
                adc_channel = self._connection_dataframe.query(
                    channel_type + ' == @chan'
                )['adc_channel'].values

                if len(adc_channel) != 1:
                    raise ValueError(f'DAQControl: multiple channel '
                                     f'{chan} found in connection map!')
                else:
                    channels_dict['adc_channels'].append(int(adc_channel[0]))

                adc_id = self._connection_dataframe.query(
                    channel_type + ' == @chan'
                )['adc_id'].values

                if len(adc_id) != 1:
                    raise ValueError(f'DAQControl: multiple channel '
                                     f'{chan} found in connection map!')
                else:
                    channels_dict['adc_ids'].append(adc_id[0])

        # detector channels
        for ichan, adc_chan in enumerate(channels_dict['adc_channels']):
            adc_id = channels_dict['adc_ids'][ichan]
            adc_chan = str(adc_chan)
            detector_chan = self._connection_dataframe.query(
                'adc_channel == @adc_chan and adc_id == @adc_id'
            )['detector_channel'].values
            channels_dict['detector_channels'].append(detector_chan[0])


        return channels_dict
        
    
    def _get_adc_configuration(self,
                               acquisition_type,
                               adc_config_default,
                               ttl_adc_channel=None,
                               ttl_adc_id=None):
        """
        Get ADC setup from configuration files
        """

        # initialize based on default
        adc_config = copy.deepcopy(adc_config_default)
        daq_config = copy.deepcopy(self._daq_config[acquisition_type])
               
        # available trigger types
        trigger_types = {'continuous':1,
                         'didv':2, 'iv':3,
                         'accel_freq_sweep':2,
                         'exttrig':2,
                         'randoms':3,
                         'threshold':4,
                         'calibration':1}
        
    
        # read voltage min/max and sample_rate
        parameters = ['voltage_min', 'voltage_max',
                      'sample_rate']
        
        for param in parameters:

            if param not in daq_config.keys():
                raise ValueError(
                    f'ERROR: ADC parameter {param} missing in '
                    f'data acquisition "ini" file, section '
                    f'{acquisition_type}')

            for adc_id in list(adc_config.keys()):
                adc_config[adc_id][param] = (
                    float(daq_config[param])
                )

        # get sample rate (should be same for every ADCs)
        sample_rate = None
        for adc_id in  adc_config.keys():
            sample_rate = adc_config[adc_id]['sample_rate']
            break

        # number of samples
        nb_samples = None
        if 'trace_length' in daq_config.keys():
            trace_length_sec = (
                arg_utils.convert_to_seconds(
                    daq_config['trace_length']
                )
            )
            
            nb_samples = convert_length_msec_to_samples(
                trace_length_sec*1000, sample_rate
            )
   
        elif 'nb_samples' in  daq_config.keys():
            nb_samples = int(daq_config['nb_samples'])

        elif 'nb_cycles' in  daq_config.keys():

            # to calculate number of samples, we need
            # the signal gen frequency
            # let's check if it is in daq_config
            signal_gen_freq = None
            for chan, chan_dict in self._current_signal_gen.items():
                if 'frequency' in  chan_dict:
                    if (signal_gen_freq  is None
                        or  chan_dict['frequency'] < signal_gen_freq):
                        signal_gen_freq =  float(chan_dict['frequency'])

            if acquisition_type != 'exttrig':
                sig_gen_config = self._iv_didv_config['didv']['signal_gen']
                for chan, chan_dict in sig_gen_config.items():
                    if 'frequency' in  chan_dict:
                        if (signal_gen_freq  is None
                            or  chan_dict['frequency'] < signal_gen_freq):
                            signal_gen_freq =  float(chan_dict['frequency'])

            if signal_gen_freq is None:
                raise ValueError('DAQControl: unable to calculate number of '
                                 'samples from "nb_cycles". No signal gen '
                                 'frequency found!')
            
            nb_cycles = float(daq_config['nb_cycles'])

            # FIX ME
            nb_samples = int(
                round(nb_cycles*sample_rate/ signal_gen_freq)
            )
        
        else:
            raise ValueError(f'ERROR: "trace_length" or "nb_samples" or '
                             f'"nb_cycles" required!')

        # channel list
        adc_channels_dict = dict()
        adc_ids = self._channels_dict['adc_ids']
        adc_channels = self._channels_dict['adc_channels']

        # add TTL channel
        if ttl_adc_channel is not None:
            
            if  ttl_adc_id is None:
                raise ValueError('ERROR: "ttl_adc_id" '
                                 'is missing!')

            is_recorded = False
            for ichan in range(len(adc_channels)):
                chan = adc_channels[ichan]
                chan_adc = adc_ids[ichan]
                if (chan == ttl_adc_channel
                    and  chan_adc == ttl_adc_id):
                    is_recorded = True
                    break
            if not is_recorded:
                adc_channels.append(ttl_adc_channel)
                adc_ids.append(ttl_adc_id)
                            
        
        for iadc, adc_id in enumerate(adc_ids):
            if adc_id not in adc_channels_dict:
                adc_channels_dict[adc_id] = {'channel_list':[]}
            adc_channels_dict[adc_id]['channel_list'].append(
                int(adc_channels[iadc])
            )
                
        # Add parameters
        for adc_id in adc_config.keys():
            adc_config[adc_id]['nb_samples'] = nb_samples
            adc_config[adc_id]['trigger_type'] = int(
                trigger_types[acquisition_type]
            )
            adc_channels_dict[adc_id]['channel_list'].sort()
            adc_config[adc_id]['channel_list'] = (
                adc_channels_dict[adc_id]['channel_list']
            )

        return adc_config

    def _get_iv_didv_configuration(self):
        """
        Get IV and dIdV configuration
        """
        
        config = {'iv': dict(),
                  'didv':dict()}
        
        # beg/end of series IV / dIdV
        series_config = self._get_series_iv_div_configuration()
        config['iv']['series'] = series_config['iv']
        config['didv']['series'] = series_config['didv']

        
        # dIdV detector channels
        didv_channels = None
        if self._acquisition_type == 'didv':
            didv_channels = (
                self._channels_dict['detector_channels'].copy()
            )
        elif (series_config['didv']['do_beginning_series']
              or series_config['didv']['do_end_series']):
            didv_channels = (
                series_config['didv']['detector_channels']
            )
            
        config['didv']['channels'] = didv_channels
        
            
        # IV detector channels
        iv_channels = None
        if self._acquisition_type == 'iv':
            iv_channels = (
                self._channels_dict['detector_channels'].copy()
            )
        elif (series_config['iv']['do_beginning_series']
              or series_config['iv']['do_end_series']):
            iv_channels = (
                series_config['iv']['detector_channels']
            )

        config['iv']['channels'] = iv_channels

        
        # dIdV signal generator config
        if  didv_channels is not None:
            
            didv_signal_gen_config = (
                self._get_didv_signal_gen_configuration(
                    didv_channels
                )
            )
            config['didv']['signal_gen'] = (
                didv_signal_gen_config
            )
            
        # IV and dIdV tes bias list
        iv_didv_tes_bias = self._get_iv_didv_tes_bias_list(
            iv_channels, didv_channels
        )

        if iv_didv_tes_bias['didv'] is not None:
            config['didv']['tes_bias_list'] = (
                iv_didv_tes_bias['didv']['tes_bias_list']
            )
        if iv_didv_tes_bias['iv'] is not None:
            config['iv']['tes_bias_list'] = (
                iv_didv_tes_bias['iv']['tes_bias_list']
            )
        

        # IV relock
        config['iv']['relock_first_step'] = False
        config['iv']['relock_all_steps'] = False

        if self._daq_config['iv'] is not None:
            if 'relock_first_step' in self._daq_config['iv']:
                config['iv']['relock_first_step'] = (
                    self._daq_config['iv']['relock_first_step']
                )
            if 'relock_all_steps' in self._daq_config['iv']:
                config['iv']['relock_all_steps'] = (
                    self._daq_config['iv']['relock_all_steps']
                )
   
        config['didv']['relock_first_step'] = False
        config['didv']['relock_all_steps'] = False
        
        if self._daq_config['didv'] is not None:
            
            if 'relock_first_step' in self._daq_config['didv']:
                config['didv']['relock_first_step'] = (
                    self._daq_config['didv']['relock_first_step']
                )
            if 'relock_all_steps' in self._daq_config['didv']:
                config['didv']['relock_all_steps'] = (
                    self._daq_config['didv']['relock_all_steps']
                )


        return config
                
    def _get_iv_didv_tes_bias_list(self,
                                   iv_channels,
                                   didv_channels):
        """
        Get TES bias list for config file
        """
        
        # IV
        tes_bias_dict = {'iv': None, 'didv':None}
        
        if   (iv_channels is not None
              and 'iv' in self._daq_config
              and self._daq_config['iv'] is not None):
         
            if 'tes_bias_list' not in self._daq_config['iv']:
                raise ValueError('DAQControl: "tes_bias_list" parameter required '
                                 'for iv data taking!')
            
            tes_bias_dict['iv'] = dict()
            
            bias_list  = self._daq_config['iv']['tes_bias_list']
            if not isinstance(bias_list, list):
                bias_list  = [bias_list]
                
            tes_bias_dict['iv']['tes_bias_list'] = bias_list
            tes_bias_dict['iv']['detector_channels'] = iv_channels
                

        if  (didv_channels is not None
             and 'didv' in self._daq_config
             and self._daq_config['didv'] is not None):

            tes_bias_dict['didv'] = dict()
            
            bias_list = ['current']
            if 'tes_bias_list' in self._daq_config['didv']:
                bias_list =  self._daq_config['didv']['tes_bias_list']
                if not isinstance(bias_list, list):
                    bias_list  = [bias_list]
               
            tes_bias_dict['didv']['tes_bias_list'] = bias_list
            tes_bias_dict['didv']['detector_channels'] = didv_channels
                
                                
        return tes_bias_dict

    

    def _get_didv_signal_gen_configuration(self, detector_channels):
        """
        Signal generator configuration
        for dIdV data taking
        """
        
        # initialize
        signal_gen_config  = dict()

        # find info from daq config
        if  self._daq_config['didv'] is None:
            return signal_gen_config

        daq_config = copy.deepcopy(self._daq_config['didv'])
        
        # signal generator voltage
        input_voltage_config = dict()
        if 'signal_gen_voltage_mv' in daq_config.keys():
            input_voltage_config =  arg_utils.extract_didv_signal_gen_config(
                daq_config['signal_gen_voltage_mv']
            )
        input_voltage_chans = list(input_voltage_config.keys())
        input_voltage_chans.sort()

        # signal generator frequency
        input_frequency_config = dict()
        if 'signal_gen_frequency_hz' in daq_config.keys():
            input_frequency_config = arg_utils.extract_didv_signal_gen_config(
                daq_config['signal_gen_frequency_hz']
            )

        input_frequency_chans = list(input_frequency_config.keys())
        input_frequency_chans.sort()
      
        # check
        if input_frequency_chans  != input_voltage_chans:
            raise ValueError('DAQControl: Input dIdV frequency and voltage '
                             'need to have same format in [didv] field!')

        # check that all channels are configured
        runlist_channels = [detector_channels]
        if (input_frequency_chans
            and (input_frequency_chans[0] != 'all')):

            runlist_channels = list()
            runlist_channels_all = [item.strip().split(',')
                                    for item in input_frequency_chans]

            list_of_all_channels = list()
            for runchans in runlist_channels_all:
                channels = list()
                for chan in runchans:
                    if chan in detector_channels:
                        channels.append(chan)
                        list_of_all_channels.append(chan)
                if channels:
                    runlist_channels.append(channels)
                    
            for chan in detector_channels:
                if chan not in list_of_all_channels :
                    raise ValueError(
                        f'DAQControl: Missing voltage/frequency '
                        f'parameters in didv config for channel '
                        f'"{chan}"!'
                    )
            
        signal_gen_config['runlist_channels'] =  runlist_channels
        
        # loop detector channels and fill dictionary with either
        # value from config or current values
        for chan in detector_channels:

            signal_gen_config[chan] = dict()

            voltage = None
            frequency = None
            for user_chans, user_voltage in input_voltage_config.items():
                if user_chans == 'all' or chan in user_chans:
                    voltage = user_voltage*1e-3
                    
            for user_chans, user_frequency in input_frequency_config.items():
                if user_chans == 'all' or chan in user_chans:
                    frequency = user_frequency
            
            if voltage is None:
                voltage = self._current_signal_gen[chan]['voltage']
            if frequency is None:
                frequency = self._current_signal_gen[chan]['frequency']

            signal_gen_config[chan] = {'voltage': voltage,
                                       'frequency': frequency}
            
        return  signal_gen_config

    def _get_series_iv_div_configuration(self):
        """
        Function to configure IV / dIdV
        """

        didv_config = {'do_beginning_series': False,
                       'do_end_series': False}
        iv_config = {'do_beginning_series': False,
                     'do_end_series': False}

        series_iv_didv_config = {
            'iv': iv_config,
            'didv': didv_config
        }
        
        if (self._acquisition_type == 'didv' 
            or self._acquisition_type == 'iv'):
            return {'iv': iv_config,
                    'didv': didv_config}
        
        # get config
        daq_config =  copy.deepcopy(
            self._daq_config[self._acquisition_type]
        )
        
        # check if IV/dIdV enable
        if ('add_series_start_didv' in daq_config.keys()
            and daq_config['add_series_start_didv']):
            didv_config['do_beginning_series'] = True
        if ('add_series_end_didv' in daq_config.keys()
            and daq_config['add_series_end_didv']):
            didv_config['do_end_series'] = True
        if ('add_series_start_iv' in daq_config.keys()
            and daq_config['add_series_start_iv']):
            iv_config['do_beginning_series'] = True
        if ('add_series_end_iv' in daq_config.keys()
            and daq_config['add_series_end_iv']):
            iv_config['do_end_series'] = True

        # didv configuration
        if (didv_config['do_beginning_series']
            or didv_config['do_end_series']):

            # run time
            if 'didv_run_time' not in  daq_config:
                raise ValueError('DAQControl: "didv_run_time" required '
                                 'for beg/end series didv!')
        
            didv_config['run_time'] =  (
                arg_utils.convert_to_seconds(
                    daq_config['didv_run_time'])
            )
            # detectors
            didv_config['detector_channels'] = (
                self._channels_dict['detector_channels'].copy()
            )

            if ('didv_detector_channels' in daq_config
                and daq_config['didv_detector_channels'] != 'all'):
                didv_chans =  daq_config['didv_detector_channels']
                if not isinstance(didv_chans, list):
                    didv_chans = [didv_chans]

                # check channels
                warning_on = False
                for chan in didv_chans:
                    if (chan not in self._channels_dict['detector_channels']):
                        print(f'WARNING: didv channel "{chan}" is not part '
                              f'of data taking channels. It will be ignored!')
                        warning_on = True
                if warning_on:
                    time.sleep(5)
                    
                didv_config['detector_channels'] = list()
                for chan in self._channels_dict['detector_channels']:
                    if chan in didv_chans:
                        didv_config['detector_channels'].append(chan)

                if not didv_config['detector_channels']:
                    raise ValueError('DAQControl: series dIdV enabled but '
                                     'no detector channels selected with '
                                     'run_daq.py found in '
                                     '"didv_detector_channels" list!')
                
        # iv configuration
        if (iv_config['do_beginning_series']
            or iv_config['do_end_series']):

            # run time
            if 'iv_run_time' not in  daq_config:
                raise ValueError('DAQControl: "iv_run_time" required '
                                 'for beg/end series iv!')
   
            iv_config['run_time'] =  (
                arg_utils.convert_to_seconds(
                    daq_config['iv_run_time'])
            )
            
            # detectors
            iv_config['detector_channels'] = (
                self._channels_dict['detector_channels'].copy()
            )

            if ('iv_detector_channels' in daq_config
                and daq_config['iv_detector_channels'] != 'all'):
                iv_chans =  daq_config['iv_detector_channels']
                if not isinstance(iv_chans, list):
                    iv_chans = [iv_chans]
                iv_config['detector_channels'] = list()
                for chan in self._channels_dict['detector_channels']:
                    if chan in iv_chans:
                        iv_config['detector_channels'].append(chan)

                if not iv_config['detector_channels']:
                    raise ValueError('DAQControl: series IV enabled but '
                                     'no detector channels selected with '
                                     'run_daq.py found in '
                                     '"iv_detector_channels" list!')

        # save
        series_iv_didv_config = {
            'iv': iv_config,
            'didv': didv_config
        }
        
            
        return series_iv_didv_config

    def _read_signal_gen(self):
        """
        Read signal generator frequency
        """

        signal_gen_settings = dict()
        for chan in self._channels_dict['detector_channels']:
            signal_gen_settings[chan] = (
                self._instruments_inst.get_signal_gen_params(
                    detector_channel=chan)
            )
            
        return signal_gen_settings

    def _read_tes_bias(self):
        """
        Read TES bias 
        """
        
        tes_bias_setting = dict()
        for chan in self._channels_dict['detector_channels']:

            tes_bias = (
                self._instruments_inst.get_tes_bias(
                    detector_channel=chan,
                    unit='uA')
            )

            if tes_bias != np.nan:
                tes_bias_setting[chan] = tes_bias 
                    
        return tes_bias_setting

    
    def _read_detector_settings(self, adc_config,
                                laser_control_channel=None,
                                laser_ttl_channel=None):
        """ 
        Read detector settings
        """
    
        det_config = dict()
            
        for adc_id, adc_dict in adc_config.items():
            channels = adc_dict['channel_list']
            det_config[adc_id] = copy.deepcopy(
                self._instruments_inst.read_all(
                    adc_id=adc_id,
                    adc_channel_list=channels,
                    laser_control_channel=laser_control_channel,
                    laser_ttl_channel=laser_ttl_channel
                )
            )
        
        return det_config


    def _get_calibration_configuration(self):
        """
        Get bor calibration information
        """

        # initialize
        output_config = {'do_beginning_series': False,
                         'do_end_series': False}


        # get config
        daq_config =  copy.deepcopy(
            self._daq_config[self._acquisition_type]
        )
    
        # check if calibration enabled
        if ('add_series_start_calib' in daq_config.keys()
            and daq_config['add_series_start_calib']):
            output_config['do_beginning_series'] = True
        if ('add_series_end_calib' in daq_config.keys()
            and daq_config['add_series_end_calib']):
            output_config['do_end_series'] = True


            
        # get more parameters if beginning of run calib
        if (output_config['do_beginning_series']
            or output_config['do_end_series']):

            # run time
            if 'calib_run_time' not in  daq_config:
                raise ValueError('DAQControl: "calib_run_ime" required '
                                 'for beg/end series calibration!')
        
            output_config['run_time'] =  (
                arg_utils.convert_to_seconds(
                    daq_config['calib_run_time'])
            )

        # laser configuration, initialize
        output_config['control_channel'] = None
        output_config['control_offset'] = None
        output_config['control_voltage_pp'] = None
        output_config['control_voltage_high'] = None
        output_config['control_voltage_low'] = None
        output_config['control_pulse_width'] = None
        output_config['control_frequency'] = None
        output_config['ttl_channel'] = None
        output_config['ttl_offset'] = None
        output_config['ttl_voltage_pp'] = None
        output_config['ttl_voltage_high'] = None
        output_config['ttl_voltage_low'] = None
        output_config['ttl_pulse_with'] = None
        output_config['ttl_adc_channel'] = None
        output_config['ttl_adc_id'] = None
        output_config['add_calib_noise']= False
        output_config['calib_noise_runtime'] = 60
            
        if self._daq_config['calibration'] is None:
            return output_config
                
        config = self._daq_config['calibration']
            
        # parameters
        if ('control_channel' in config
            and config['control_channel'] != 'None'):
            output_config['control_channel'] = int(
                config['control_channel']
            )

        if ('control_offset' in config
            and config['control_offset'] != 'None'):
            output_config['control_offset'] = config['control_offset']
                
        if ('control_voltage_pp' in config
            and config['control_voltage_pp'] != 'None'):
            output_config['control_voltage_pp'] = (
                config['control_voltage_pp']
            )
            
        if ('control_voltage_high' in config
            and config['control_voltage_high'] != 'None'):
            output_config['control_voltage_high'] = (
                config['control_voltage_high']
            )
                
        if ('control_voltage_low' in config
            and config['control_voltage_low'] != 'None'):
            output_config['control_voltage_low'] = (
                config['control_voltage_low']
            )   
            
        if ('control_pulse_width' in config
            and config['control_pulse_width'] != 'None'):
            output_config['control_pulse_width'] = (
                config['control_pulse_width']
            )
                    
        if ('control_frequency' in config
            and config['control_frequency'] != 'None'):
            output_config['control_frequency'] = (
                config['control_frequency']
            )   

        # TTL parameters
        if ('ttl_channel' in config
            and config['ttl_channel'] != 'None'):
            output_config['ttl_channel'] = int(
                config['ttl_channel']
            )

        if ('ttl_offset' in config
            and config['ttl_offset'] != 'None'):
            output_config['ttl_offset'] = (
                config['ttl_offset']
            )

        if ('ttl_voltage_pp' in config
            and config['ttl_voltage_pp'] != 'None'):
            output_config['ttl_voltage_pp'] = (
                config['ttl_voltage_pp']
            )

        if ('ttl_voltage_high' in config
            and config['ttl_voltage_high'] != 'None'):
            output_config['ttl_voltage_high'] = (
                config['ttl_voltage_high']
            )
                
        if ('ttl_voltage_low' in config
            and config['ttl_voltage_low'] != 'None'):
            output_config['ttl_voltage_low'] = (
                config['ttl_voltage_low']
            )   

        if ('ttl_pulse_width' in config
            and config['ttl_pulse_width'] != 'None'):
            output_config['ttl_pulse_width'] = (
                config['ttl_pulse_width']
            )

        if ('ttl_adc_channel' in config
            and config['ttl_adc_channel'] != 'None'):
            output_config['ttl_adc_channel'] = (
                config['ttl_adc_channel']
            )

        if ('ttl_adc_id' in config
            and config['ttl_adc_id'] != 'None'):
            output_config['ttl_adc_id'] = (
                config['ttl_adc_id']
            )
   

        # noise
        if 'add_calib_noise' in config:
            output_config['add_calib_noise']  = (
                config['add_calib_noise']
            )
        if 'calib_noise_run_time' in config:
            noise_run_time = config[ 'calib_noise_run_time']
            output_config['calib_noise_runtime'] = (
                arg_utils.convert_to_seconds(noise_run_time)
            )
                
                
        return  output_config 
            
