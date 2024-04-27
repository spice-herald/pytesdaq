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
                             'exttrig', 'randoms',
                             'threshold']
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
        # IV/dIdV specific
        # configuration
        # ------------------------

        self._iv_didv_config = self._get_iv_didv_configuration()
     
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
        if (self._iv_didv_config['didv']['channels']is not None
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
        elif self._acquisition_type == 'exttrig':
            data_prefix = 'exttrig'
        elif self._acquisition_type == 'threshold':
            data_prefix = 'thresh'
        elif self._acquisition_type == 'randoms':
            data_prefix = 'rand'

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

        # didv / iv config
        didv_config = self._iv_didv_config['didv']
        iv_config = self._iv_didv_config['iv']

            
        # loop sub-runs
        for irun in range(nb_runs):

            if self._verbose:
                print('\n===========================================')
                print(f'INFO: Starting series #{irun+1} '
                      f' (out of {nb_runs} total)')
                print('===========================================')
                

            # --------------------
            # dIdV (Beg. of series)
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
            # IV (Beg. of series)
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
                               adc_config_default):
        """
        Get ADC setup from configuration files
        """

        # initialize based on default
        adc_config = copy.deepcopy(adc_config_default)
        daq_config = copy.deepcopy(self._daq_config[acquisition_type])
               
        # available trigger types
        trigger_types = {'continuous':1,
                         'didv':2, 'iv':3,
                         'exttrig':2,
                         'randoms':3, 
                         'threshold':4}
        
    
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
        Read signal generator frequency
        """
        
        tes_bias_setting = dict()
        for chan in self._channels_dict['detector_channels']:
            tes_bias_setting[chan] = (
                self._instruments_inst.get_tes_bias(
                    detector_channel=chan,
                    unit='uA'
                )
            )
            
        return tes_bias_setting

    
    def _read_detector_settings(self, adc_config):
        """ 
        Read detector settings
        """
    
        det_config = dict()
            
        for adc_id, adc_dict in adc_config.items():
            channels = adc_dict['channel_list']
            det_config[adc_id] = copy.deepcopy(
                self._instruments_inst.read_all(
                    adc_id=adc_id,
                    adc_channel_list=channels
                )
            )
        
        return det_config
