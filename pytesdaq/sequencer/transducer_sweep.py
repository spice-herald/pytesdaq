import numpy as np
import time
import copy

from pytesdaq.daq import daq
import pytesdaq.config.settings as settings
import pytesdaq.instruments.control as instrument
from pytesdaq.sequencer.sequencer import Sequencer
from pytesdaq.utils import connection_utils
from pytesdaq.utils import arg_utils


class TransducerSweep(Sequencer):

    def __init__(self, detector_channels=None,
                 sequencer_file=None, setup_file=None,
                 comment='No comment',
                 data_purpose='test',
                 dry_run=False, verbose=True):
        """
        Transducer frequency/amplitude sweep measurement.

        Parameters
        ----------
        detector_channels : list or None
            List of detector channel names to sweep.
        sequencer_file : str or None
            Path to transducer_sweep.ini config file.
        setup_file : str or None
            Path to setup.ini config file.
        comment : str
            Comment string for the measurement.
        data_purpose : str
            Data purpose / run type string.
        dry_run : bool
            If True, only print the sweep plan without
            any hardware interaction or data taking.
        verbose : bool
            If True, print status messages.
        """

        # Store raw detector channels before base class init.
        # We pass detector_channels=None to the base class so
        # it skips its ADC setup logic (which requires dIdV-style
        # signal gen parameters that don't apply here).
        self._raw_detector_channels = detector_channels
        self._data_purpose = data_purpose
        self._dry_run = dry_run

        # Call the Sequencer class constructor.
        super().__init__(
            'transducer_sweep',
            comment=comment,
            detector_channels=None,
            sequencer_file=sequencer_file,
            setup_file=setup_file,
            verbose=verbose
        )

        self._configure()

    def run(self):
        """
        Run the transducer frequency/amplitude sweep measurement.
        """

        # get measurement config
        config_dict = self._measurement_config[self._measurement_name]

        if 'sweep_run_time' not in config_dict:
            raise ValueError(
                'TransducerSweep: "sweep_run_time" required!'
            )

        run_time_default = arg_utils.convert_to_seconds(
            config_dict['sweep_run_time']
        )

        # parse frequency and amplitude sweep configurations
        freq_config = self._get_frequency_config(
            config_dict=config_dict,
            run_time_default=run_time_default
        )
        amp_config = self._get_amplitude_config(
            config_dict=config_dict,
            run_time_default=run_time_default
        )

        if not freq_config['enabled'] and not amp_config['enabled']:
            raise ValueError(
                'TransducerSweep: at least one of frequency or '
                'amplitude sweep must be enabled!'
            )

        # ------------------
        # Dry run mode
        # ------------------
        if self._dry_run:
            self._print_dry_run(freq_config, amp_config)
            return

        # ------------------
        # Normal run
        # ------------------

        # instantiate DAQ and instrument drivers
        self._instantiate_drivers()

        # enable DAQ process lock
        self._daq.lock_daq = True

        if self._verbose:
            print('\n=====================================')
            print(f'INFO: Starting transducer sweep')
            if self._comment and self._comment != 'No comment':
                print(f'  ({self._comment})')
            print('=====================================')

        # turn on signal generator for all detector channels
        for chan in self._detector_channels:
            self._instrument.set_signal_gen_onoff(
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

            if self._verbose:
                print(f'\nINFO: Frequency sweep: '
                      f'{len(frequency_list)} points, '
                      f'{frequency_list[0]:.6g} - '
                      f'{frequency_list[-1]:.6g} Hz')

            for frequency_hz in frequency_list:
                self._set_signal_generator(
                    detector_channels=self._detector_channels,
                    amplitude_vpp=amplitude_vpp,
                    frequency_hz=frequency_hz
                )

                if hold_time_s > 0:
                    time.sleep(hold_time_s)

                self._run_sweep_step(
                    config_dict=config_dict,
                    frequency_hz=frequency_hz,
                    amplitude_vpp=amplitude_vpp,
                    run_time_s=run_time_s
                )

        # ------------------
        # Amplitude sweep
        # ------------------
        if amp_config['enabled']:
            amplitude_list = amp_config['amplitudes_vpp']
            frequency_hz = amp_config['frequency_hz']
            hold_time_s = amp_config['hold_time_s']
            run_time_s = amp_config['run_time_s']

            if self._verbose:
                print(f'\nINFO: Amplitude sweep: '
                      f'{len(amplitude_list)} points, '
                      f'{amplitude_list[0]:.6g} - '
                      f'{amplitude_list[-1]:.6g} Vpp')

            for amplitude_vpp in amplitude_list:
                self._set_signal_generator(
                    detector_channels=self._detector_channels,
                    amplitude_vpp=amplitude_vpp,
                    frequency_hz=frequency_hz
                )

                if hold_time_s > 0:
                    time.sleep(hold_time_s)

                self._run_sweep_step(
                    config_dict=config_dict,
                    frequency_hz=frequency_hz,
                    amplitude_vpp=amplitude_vpp,
                    run_time_s=run_time_s
                )

        # turn off signal generators when finished
        if not self._instrument.is_tes_signal_gen_inst_common():
            for chan in self._detector_channels:
                self._instrument.set_signal_gen_onoff(
                    'off',
                    detector_channel=chan
                )

        time.sleep(2)

        if self._verbose:
            print('\nINFO: Transducer sweep complete!')

    def _print_dry_run(self, freq_config, amp_config):
        """
        Print the sweep plan without any hardware interaction.
        """

        print('\n=====================================')
        print('DRY RUN - no hardware interaction')
        print('=====================================')

        total_steps = 0
        total_time_s = 0.0

        # frequency sweep summary
        if freq_config['enabled']:
            freq_list = freq_config['frequencies_hz']
            amp = freq_config['amplitude_vpp']
            hold = freq_config['hold_time_s']
            run_time = freq_config['run_time_s']
            n = len(freq_list)

            print(f'\nFrequency sweep: {n} points, '
                  f'{freq_list[0]:.6g} - {freq_list[-1]:.6g} Hz '
                  f'(amplitude: {amp:.6g} Vpp)')
            for i, freq in enumerate(freq_list):
                print(f'  Step {i+1:>{len(str(n))}}/{n}: '
                      f'freq={freq:.6g} Hz, '
                      f'amp={amp:.6g} Vpp, '
                      f'run_time={run_time:.6g} s')

            total_steps += n
            total_time_s += n * (run_time + hold)

        # amplitude sweep summary
        if amp_config['enabled']:
            amp_list = amp_config['amplitudes_vpp']
            freq = amp_config['frequency_hz']
            hold = amp_config['hold_time_s']
            run_time = amp_config['run_time_s']
            n = len(amp_list)

            print(f'\nAmplitude sweep: {n} points, '
                  f'{amp_list[0]:.6g} - {amp_list[-1]:.6g} Vpp '
                  f'(frequency: {freq:.6g} Hz)')
            for i, amp in enumerate(amp_list):
                print(f'  Step {i+1:>{len(str(n))}}/{n}: '
                      f'freq={freq:.6g} Hz, '
                      f'amp={amp:.6g} Vpp, '
                      f'run_time={run_time:.6g} s')

            total_steps += n
            total_time_s += n * (run_time + hold)

        # totals
        total_min = total_time_s / 60.0
        print(f'\nTotal steps: {total_steps}')
        print(f'Total estimated time: {total_time_s:.6g} s '
              f'({total_min:.4g} min)')

    def _read_measurement_config(self):
        """
        Override base class to skip directory creation in
        dry-run mode (the base class tries to create data
        directories which may not be writable or desired
        during a dry run).
        """

        from pytesdaq.utils import arg_utils as _arg_utils

        self._measurement_config = (
            self._config.get_sequencer_setup(
                self._measurement_name,
                self._measurement_list
            )
        )

        # save parameters from user settings
        config = self._measurement_config[self._measurement_name]
        for key, item in config.items():
            if key == 'online':
                self._online_analysis = item
            elif key == 'daq_driver':
                self._daq_driver = item
            elif key == 'enable_redis':
                self._enable_redis = item
            elif key == 'save_raw_data':
                self._save_raw_data = item

        # facility
        self._facility = self._config.get_facility_num()

        # data path
        data_path = self._config.get_data_path()
        self._fridge_run = self._config.get_fridge_run()
        fridge_run_name = 'run' + str(self._fridge_run)
        if data_path.find(fridge_run_name) == -1:
            data_path += ('/' + fridge_run_name)
        self._base_raw_data_path = data_path + '/raw'
        self._base_automation_data_path = data_path + '/automation'

        if not self._dry_run:
            _arg_utils.make_directories(
                [data_path, self._base_raw_data_path,
                 self._base_automation_data_path]
            )

        # channels — we handle channel resolution ourselves
        # in _configure(), so skip the base class channel logic

    def _configure(self):
        """
        Configure the transducer sweep measurement.

        Resolves detector channels, builds ADC configuration,
        and creates measurement directories.
        """

        config_dict = self._measurement_config[self._measurement_name]

        # in dry-run mode, skip channel resolution, ADC config,
        # and directory creation — only the config dict is needed
        # for computing sweep points
        if self._dry_run:
            return

        # resolve detector channels
        if self._raw_detector_channels is not None:
            self._detector_connection_table = (
                self._config.get_adc_connections()
            )
            self._detector_channels = self._extract_detector_channels(
                self._raw_detector_channels
            )
            self._saved_detector_channels = self._detector_channels
        elif 'detector_channels' in config_dict:
            self._detector_connection_table = (
                self._config.get_adc_connections()
            )
            channels = config_dict['detector_channels']
            if isinstance(channels, str):
                channels = [ch.strip() for ch in channels.split(',')]
            self._detector_channels = self._extract_detector_channels(
                channels
            )
            self._saved_detector_channels = self._detector_channels

        if self._detector_channels is None:
            raise ValueError(
                'TransducerSweep: detector_channels required! '
                'Provide via argument or config file.'
            )

        # build ADC config from detector channels
        adc_dict = dict()
        for channel in self._saved_detector_channels:
            adc_id, adc_chan = connection_utils.get_adc_channel_info(
                self._detector_connection_table,
                detector_channel=channel
            )
            if adc_id not in adc_dict:
                adc_dict[adc_id] = self._config.get_adc_setup(adc_id).copy()
                adc_dict[adc_id]['channel_list'] = list()
            adc_dict[adc_id]['channel_list'].append(int(adc_chan))

        # validate required ADC parameters
        required_parameters = ['sample_rate', 'voltage_min', 'voltage_max']
        for item in required_parameters:
            if item not in config_dict:
                raise ValueError(
                    f'TransducerSweep requires "{item}"! '
                    f'Please check configuration.'
                )

        # apply config overrides to each ADC
        for adc_id in adc_dict:
            for item in list(adc_dict[adc_id].keys()):
                if item in config_dict:
                    adc_dict[adc_id][item] = config_dict[item]

        # compute nb_samples from trace_length (static default)
        sample_rate = int(config_dict['sample_rate'])
        nb_samples = None

        if 'trace_length' in config_dict:
            trace_length_sec = arg_utils.convert_to_seconds(
                config_dict['trace_length']
            )
            nb_samples = round(trace_length_sec * sample_rate)
        elif 'nb_samples' in config_dict:
            nb_samples = int(config_dict['nb_samples'])
        elif 'nb_cycles' in config_dict:
            # nb_cycles will be recomputed dynamically per step;
            # set a placeholder of 1 second
            nb_samples = round(sample_rate)
        else:
            raise ValueError(
                'TransducerSweep: "trace_length", "nb_samples", '
                'or "nb_cycles" required!'
            )

        # set trigger type to external trigger (type 2)
        trigger_type = 2

        for adc_id in adc_dict:
            adc_dict[adc_id]['nb_samples'] = int(nb_samples)
            adc_dict[adc_id]['trigger_type'] = trigger_type

        # store ADC setup in measurement config
        self._measurement_config[self._measurement_name]['adc_setup'] = (
            adc_dict
        )

        # create measurement directories
        self._create_measurement_directories('transducer_sweep')

    def _run_sweep_step(self, config_dict=None,
                        frequency_hz=None,
                        amplitude_vpp=None,
                        run_time_s=None):
        """
        Take a single sweep data step.

        Parameters
        ----------
        config_dict : dict
            Measurement configuration dictionary.
        frequency_hz : float
            Signal generator frequency in Hz.
        amplitude_vpp : float
            Signal generator amplitude in Vpp.
        run_time_s : float
            Run time for the sweep step in seconds.
        """

        if run_time_s is None:
            self._daq.clear()
            raise ValueError(
                'TransducerSweep: sweep step run time missing!'
            )

        if self._verbose:
            print(f'  Step: freq={float(frequency_hz):.6g} Hz, '
                  f'amp={float(amplitude_vpp):.6g} Vpp, '
                  f'run_time={float(run_time_s):.6g} s')

        # build step-specific ADC config
        adc_config = self._get_adc_config_for_step(
            config_dict=config_dict,
            frequency_hz=frequency_hz
        )

        # configure ADC
        self._daq.set_adc_config_from_dict(adc_config)

        # build detector config from instrument state
        detector_config = dict()
        for adc_id, adc_dict in adc_config.items():
            detector_config[adc_id] = copy.deepcopy(
                self._instrument.read_all(
                    adc_id=adc_id,
                    adc_channel_list=adc_dict['channel_list']
                )
            )

        # apply accel_gain if configured
        if config_dict is not None and 'accel_gain' in config_dict:
            accel_gain = float(config_dict['accel_gain'])
            for adc_id, adc_dict in detector_config.items():
                channel_list = adc_dict.get('channel_list', [])
                if not isinstance(channel_list, (list, np.ndarray)):
                    channel_list = [channel_list]
                adc_dict['accel_gain'] = np.full(
                    len(channel_list),
                    accel_gain
                )

        self._daq.set_detector_config(detector_config)
        time.sleep(2)

        # build step comment
        comment_parts = list()
        if self._comment and self._comment != 'No comment':
            comment_parts.append(self._comment)
        comment_parts.append(
            f'freq={float(frequency_hz):.6g} Hz'
        )
        comment_parts.append(
            f'amp={float(amplitude_vpp):.6g} Vpp'
        )
        step_comment = ' | '.join(comment_parts)

        success = self._daq.run(
            run_time=run_time_s,
            run_type=self._data_purpose,
            run_comment=step_comment,
            group_name=self._group_name,
            group_comment=self._comment,
            data_prefix='transducer_sweep',
            data_path=self._raw_data_path
        )

        if not success:
            self._daq.clear()
            print('ERROR: Problem with data taking. Exiting!')
            return

    def _set_signal_generator(self, detector_channels=None,
                              amplitude_vpp=None,
                              frequency_hz=None):
        """
        Configure the signal generator for a sweep step.

        Parameters
        ----------
        detector_channels : list
            List of detector channels to configure.
        amplitude_vpp : float
            Signal generator amplitude in Vpp.
        frequency_hz : float
            Signal generator frequency in Hz.
        """

        # Enable auto-range before setting voltage so the generator
        # selects the appropriate range for the new amplitude, avoiding
        # silent failures when the current fixed range is too small.
        signal_gen_controller = self._instrument.get_signal_gen_controller()
        if signal_gen_controller is not None:
            signal_gen_controller.set_auto_range('on')

        for chan in detector_channels:
            self._instrument.set_signal_gen_params(
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

        # Disable auto-range after voltage is set to prevent unintended
        # range changes during the measurement.
        if signal_gen_controller is not None:
            signal_gen_controller.set_auto_range('off')

    def _get_adc_config_for_step(self, config_dict=None,
                                 frequency_hz=None):
        """
        Build ADC configuration for a sweep step.

        If nb_cycles is specified in config, dynamically
        recomputes nb_samples based on the current sweep frequency.

        Parameters
        ----------
        config_dict : dict
            Measurement configuration dictionary.
        frequency_hz : float
            Current sweep frequency in Hz.

        Returns
        -------
        adc_config : dict
            ADC configuration for this step.
        """

        adc_config = copy.deepcopy(
            self._measurement_config[self._measurement_name]['adc_setup']
        )

        if config_dict is not None and 'nb_cycles' in config_dict:
            if frequency_hz is None or frequency_hz <= 0:
                raise ValueError(
                    'TransducerSweep: "nb_cycles" requires a positive '
                    'frequency_hz value!'
                )

            sample_rate = None
            for adc_id in adc_config:
                sample_rate = adc_config[adc_id]['sample_rate']
                break

            nb_cycles = float(config_dict['nb_cycles'])
            nb_samples = int(
                round(nb_cycles * sample_rate / float(frequency_hz))
            )

            for adc_id in adc_config:
                adc_config[adc_id]['nb_samples'] = nb_samples

        return adc_config

    def _get_frequency_config(self, config_dict=None,
                              run_time_default=None):
        """
        Parse the frequency sweep configuration.

        Parameters
        ----------
        config_dict : dict
            Measurement configuration dictionary.
        run_time_default : float
            Default run time in seconds for each sweep step.

        Returns
        -------
        freq_config : dict
            Parsed frequency sweep configuration.
        """

        output_config = {'enabled': True}

        if 'do_frequency_sweep' in config_dict:
            output_config['enabled'] = bool(
                config_dict['do_frequency_sweep']
            )

        if not output_config['enabled']:
            return output_config

        if 'amplitude_vpp' not in config_dict:
            raise ValueError(
                'TransducerSweep: "amplitude_vpp" required for '
                'frequency sweep!'
            )
        if 'start_frequency_hz' not in config_dict:
            raise ValueError(
                'TransducerSweep: "start_frequency_hz" required for '
                'frequency sweep!'
            )
        if 'stop_frequency_hz' not in config_dict:
            raise ValueError(
                'TransducerSweep: "stop_frequency_hz" required for '
                'frequency sweep!'
            )

        points = None
        if 'frequency_points' in config_dict:
            points = config_dict['frequency_points']
        elif 'points' in config_dict:
            points = config_dict['points']

        if points is None:
            raise ValueError(
                'TransducerSweep: "frequency_points" required for '
                'frequency sweep!'
            )

        spacing = 'linear'
        if 'frequency_spacing' in config_dict:
            spacing = config_dict['frequency_spacing']

        hold_time_s = 0.0
        if 'frequency_hold_time' in config_dict:
            hold_time_s = arg_utils.convert_to_seconds(
                config_dict['frequency_hold_time']
            )

        focus_frequencies_hz = None
        if 'focus_frequencies_hz' in config_dict:
            focus_frequencies_hz = config_dict['focus_frequencies_hz']

        focus_freqs_width_hz = 2.0
        if 'focus_freqs_width_hz' in config_dict:
            focus_freqs_width_hz = float(
                config_dict['focus_freqs_width_hz']
            )

        focus_freqs_spacing_hz = 0.2
        if 'focus_freqs_spacing_hz' in config_dict:
            focus_freqs_spacing_hz = float(
                config_dict['focus_freqs_spacing_hz']
            )

        sweep_config = {
            'amplitude_vpp': float(config_dict['amplitude_vpp']),
            'start_frequency_hz': float(config_dict['start_frequency_hz']),
            'stop_frequency_hz': float(config_dict['stop_frequency_hz']),
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
        if 'frequency_run_time' in config_dict:
            run_time_s = arg_utils.convert_to_seconds(
                config_dict['frequency_run_time']
            )

        output_config['frequencies_hz'] = frequencies_hz
        output_config['amplitude_vpp'] = sweep_config['amplitude_vpp']
        output_config['hold_time_s'] = hold_time_s
        output_config['run_time_s'] = run_time_s

        return output_config

    def _get_amplitude_config(self, config_dict=None,
                              run_time_default=None):
        """
        Parse the amplitude sweep configuration.

        Parameters
        ----------
        config_dict : dict
            Measurement configuration dictionary.
        run_time_default : float
            Default run time in seconds for each sweep step.

        Returns
        -------
        amp_config : dict
            Parsed amplitude sweep configuration.
        """

        output_config = {'enabled': True}

        if 'do_amplitude_sweep' in config_dict:
            output_config['enabled'] = bool(
                config_dict['do_amplitude_sweep']
            )

        if not output_config['enabled']:
            return output_config

        if 'frequency_hz' not in config_dict:
            raise ValueError(
                'TransducerSweep: "frequency_hz" required for '
                'amplitude sweep!'
            )
        if 'start_amplitude_vpp' not in config_dict:
            raise ValueError(
                'TransducerSweep: "start_amplitude_vpp" required for '
                'amplitude sweep!'
            )
        if 'stop_amplitude_vpp' not in config_dict:
            raise ValueError(
                'TransducerSweep: "stop_amplitude_vpp" required for '
                'amplitude sweep!'
            )

        points = None
        if 'amplitude_points' in config_dict:
            points = config_dict['amplitude_points']
        elif 'points' in config_dict:
            points = config_dict['points']

        if points is None:
            raise ValueError(
                'TransducerSweep: "amplitude_points" required for '
                'amplitude sweep!'
            )

        spacing = 'linear'
        if 'amplitude_spacing' in config_dict:
            spacing = config_dict['amplitude_spacing']

        hold_time_s = 0.0
        if 'amplitude_hold_time' in config_dict:
            hold_time_s = arg_utils.convert_to_seconds(
                config_dict['amplitude_hold_time']
            )

        sweep_config = {
            'frequency_hz': float(config_dict['frequency_hz']),
            'start_amplitude_vpp': float(config_dict['start_amplitude_vpp']),
            'stop_amplitude_vpp': float(config_dict['stop_amplitude_vpp']),
            'points': int(points),
            'spacing': str(spacing).lower().strip()
        }

        amplitudes_vpp = self._build_sweep_amplitudes(
            sweep_config=sweep_config
        )

        run_time_s = run_time_default
        if 'amplitude_run_time' in config_dict:
            run_time_s = arg_utils.convert_to_seconds(
                config_dict['amplitude_run_time']
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
        ----------
        sweep_config : dict
            Frequency sweep configuration dictionary.

        Returns
        -------
        frequencies_hz : list
            Sorted list of unique sweep frequencies in Hz.
        """

        spacing = str(sweep_config['spacing']).lower().strip()
        if spacing not in ['linear', 'log']:
            raise ValueError(
                'TransducerSweep: "spacing" must be "linear" or "log"!'
            )

        start_frequency_hz = float(sweep_config['start_frequency_hz'])
        stop_frequency_hz = float(sweep_config['stop_frequency_hz'])
        points = int(sweep_config['points'])

        if points < 1:
            raise ValueError(
                'TransducerSweep: "points" must be >= 1!'
            )

        base_frequencies = list()
        if spacing == 'linear':
            if points == 1:
                base_frequencies = [float(start_frequency_hz)]
            else:
                step = (
                    (stop_frequency_hz - start_frequency_hz)
                    / (points - 1)
                )
                for idx in range(points):
                    base_frequencies.append(
                        start_frequency_hz + (idx * step)
                    )
        else:
            if start_frequency_hz <= 0 or stop_frequency_hz <= 0:
                raise ValueError(
                    'TransducerSweep: log spacing requires '
                    'start/stop > 0!'
                )
            if points == 1:
                base_frequencies = [float(start_frequency_hz)]
            else:
                log_start = np.log10(start_frequency_hz)
                log_stop = np.log10(stop_frequency_hz)
                step = (log_stop - log_start) / (points - 1)
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
                raise ValueError(
                    'TransducerSweep: "focus_freqs_width_hz" must be > 0!'
                )
            if focus_freqs_spacing_hz <= 0:
                raise ValueError(
                    'TransducerSweep: "focus_freqs_spacing_hz" must be > 0!'
                )

            for focus_frequency in focus_frequencies_hz:
                half_width = focus_freqs_width_hz / 2.0
                focus_start = float(focus_frequency) - half_width
                focus_stop = float(focus_frequency) + half_width
                focus_points = np.arange(
                    focus_start,
                    focus_stop + (0.5 * focus_freqs_spacing_hz),
                    focus_freqs_spacing_hz
                )
                for focus_point in focus_points:
                    focus_frequency_list.append(float(focus_point))

        combined_frequencies = (
            base_frequencies + focus_frequency_list
        )

        unique_frequency_set = set()
        for freq in combined_frequencies:
            unique_frequency_set.add(float(freq))

        unique_frequencies = sorted(unique_frequency_set)

        return unique_frequencies

    def _build_sweep_amplitudes(self, sweep_config=None):
        """
        Build the amplitude sweep list.

        Parameters
        ----------
        sweep_config : dict
            Amplitude sweep configuration dictionary.

        Returns
        -------
        amplitudes_vpp : list
            List of sweep amplitudes in Vpp.
        """

        spacing = str(sweep_config['spacing']).lower().strip()
        if spacing not in ['linear', 'log']:
            raise ValueError(
                'TransducerSweep: "spacing" must be "linear" or "log"!'
            )

        start_amplitude_vpp = float(sweep_config['start_amplitude_vpp'])
        stop_amplitude_vpp = float(sweep_config['stop_amplitude_vpp'])
        points = int(sweep_config['points'])

        if points < 1:
            raise ValueError(
                'TransducerSweep: "points" must be >= 1!'
            )

        amplitudes_vpp = list()
        if spacing == 'linear':
            if points == 1:
                amplitudes_vpp = [float(start_amplitude_vpp)]
            else:
                step = (
                    (stop_amplitude_vpp - start_amplitude_vpp)
                    / (points - 1)
                )
                for idx in range(points):
                    amplitudes_vpp.append(
                        start_amplitude_vpp + (idx * step)
                    )
        else:
            if start_amplitude_vpp <= 0 or stop_amplitude_vpp <= 0:
                raise ValueError(
                    'TransducerSweep: log spacing requires '
                    'start/stop > 0!'
                )
            if points == 1:
                amplitudes_vpp = [float(start_amplitude_vpp)]
            else:
                log_start = np.log10(start_amplitude_vpp)
                log_stop = np.log10(stop_amplitude_vpp)
                step = (log_stop - log_start) / (points - 1)
                for idx in range(points):
                    amplitudes_vpp.append(
                        10 ** (log_start + (idx * step))
                    )

        return amplitudes_vpp

    def _parse_focus_frequencies(self, focus_frequencies=None):
        """
        Parse focus frequency inputs into a list of floats.

        Parameters
        ----------
        focus_frequencies : Any
            None, a numeric value, a comma-separated string, or
            an iterable of values representing focus frequencies in Hz.

        Returns
        -------
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
            for item in focus_text.split(','):
                item_value = item.strip()
                if item_value:
                    focus_parts.append(item_value)
            focus_values = list()
            for item in focus_parts:
                focus_values.append(float(item))
            return focus_values

        if isinstance(focus_frequencies, (list, tuple, set)):
            focus_values = list()
            for item in focus_frequencies:
                focus_values.append(float(item))
            return focus_values

        return [float(focus_frequencies)]
