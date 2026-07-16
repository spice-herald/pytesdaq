"""
Gab sweep sequencer.

Automates the thermal conductance (Gab) measurement: sweep the MC stage
temperature downward while adjusting the heater TES bias so that the
thermometer TES stays at a fixed bias point. The heater TES bias is
never taken below bias_min so it stays normal. No raw TES data is
saved. See Gab_planning/Gab_sweep_design.md for the full design.
"""

import copy
import csv
import pickle
import shutil
import time
from datetime import datetime

import numpy as np
import qetpy as qp

from pytesdaq.sequencer.sequencer import Sequencer
from pytesdaq.utils import arg_utils
from pytesdaq.utils import connection_utils


def build_temperature_list(config_dict=None):
    """
    Build the MC temperature setpoint list in mK from the config,
    using "temperature_vect" or start/stop/step.

    Parameters
    ----------
    config_dict : dict
        Measurement configuration dictionary.

    Returns
    -------
    temperature_list : list of float
        Strictly decreasing MC temperature setpoints in mK.
    """

    use_vect = False
    if 'use_temperature_vect' in config_dict:
        use_vect = bool(config_dict['use_temperature_vect'])

    temperature_list = list()

    if use_vect:

        if 'temperature_vect' not in config_dict:
            raise ValueError(
                'GabSweep: "temperature_vect" required when '
                '"use_temperature_vect" is true!'
            )

        vect = config_dict['temperature_vect']
        if not isinstance(vect, (list, tuple)):
            vect = [vect]
        for value in vect:
            temperature_list.append(float(value))

    else:

        required_keys = ['temperature_start',
                         'temperature_stop',
                         'temperature_step']
        for key in required_keys:
            if key not in config_dict:
                raise ValueError(
                    f'GabSweep: "{key}" required when '
                    '"use_temperature_vect" is false!'
                )

        start = float(config_dict['temperature_start'])
        stop = float(config_dict['temperature_stop'])
        step = abs(float(config_dict['temperature_step']))

        if step == 0:
            raise ValueError('GabSweep: "temperature_step" must be nonzero!')
        if stop >= start:
            raise ValueError(
                'GabSweep: "temperature_stop" must be below '
                '"temperature_start" (descending sweep)!'
            )

        nb_steps = int(np.floor((start - stop) / step + 1e-9))
        for idx in range(nb_steps + 1):
            temperature_list.append(start - (idx * step))

    if len(temperature_list) == 0:
        raise ValueError('GabSweep: empty temperature list!')

    for idx in range(1, len(temperature_list)):
        if temperature_list[idx] >= temperature_list[idx - 1]:
            raise ValueError(
                'GabSweep: temperature list must be strictly decreasing!'
            )

    return temperature_list


def compute_next_bias(bias_history=None,
                      baseline_history=None,
                      baseline_ref=None,
                      bias_step_start=None,
                      bias_min=0.0):
    """
    Compute the next heater TES bias from the feedback history.

    First move: fixed step up by bias_step_start. Later moves: secant
    update toward baseline_ref, clamped to 2x bias_step_start.

    Parameters
    ----------
    bias_history : list of float
        Heater TES biases applied so far at this temperature [uA].
    baseline_history : list of float
        Thermometer TES baseline after each bias [ADC units].
    baseline_ref : float
        Reference baseline to return to [ADC units].
    bias_step_start : float
        Initial and fallback bias step [uA].
    bias_min : float
        Minimum bias keeping the heater TES normal [uA].

    Returns
    -------
    next_bias : float
        Next heater TES bias [uA], never below bias_min.
    """

    if (bias_history is None or baseline_history is None
            or len(bias_history) == 0
            or len(bias_history) != len(baseline_history)):
        raise ValueError(
            'GabSweep: bias and baseline histories must be non-empty '
            'and the same length!'
        )

    last_bias = float(bias_history[-1])
    fixed_step = float(bias_step_start)
    max_step = 2.0 * fixed_step
    min_bias = float(bias_min)

    if len(bias_history) < 2:
        step = fixed_step
    else:
        delta_bias = float(bias_history[-1]) - float(bias_history[-2])
        delta_baseline = (float(baseline_history[-1])
                          - float(baseline_history[-2]))
        if delta_bias == 0 or delta_baseline == 0:
            step = fixed_step
        else:
            slope = delta_baseline / delta_bias
            step = ((float(baseline_ref) - float(baseline_history[-1]))
                    / slope)
            if step > max_step:
                step = max_step
            if step < -max_step:
                step = -max_step

    next_bias = last_bias + step
    if next_bias < min_bias:
        next_bias = min_bias

    return next_bias


class GabSweep(Sequencer):

    # columns of the science dataset CSV
    CSV_COLUMNS = ['step', 'timestamp',
                   'temperature_setpoint_mk', 'mc_temperature_mk',
                   'heater_tes_bias_ua', 'thermometer_baseline',
                   'baseline_offset_percent', 'converged', 'stability_ok']

    def __init__(self, sequencer_file=None, setup_file=None,
                 comment='No comment',
                 dry_run=False, dummy_mode=False,
                 verbose=True):
        """
        Gab thermal conductance sweep measurement.

        Parameters
        ----------
        sequencer_file : str or None
            Path to gab_sweep.ini config file.
        setup_file : str or None
            Path to setup.ini config file.
        comment : str
            Comment string for the measurement.
        dry_run : bool
            If True, only print the sweep plan without
            any hardware interaction.
        dummy_mode : bool
            If True, no actual instrument I/O.
        verbose : bool
            If True, print status messages.
        """

        self._dry_run = dry_run

        super().__init__(
            'gab_sweep',
            comment=comment,
            detector_channels=None,
            sequencer_file=sequencer_file,
            setup_file=setup_file,
            dummy_mode=dummy_mode,
            save_raw_data=False,
            verbose=verbose
        )

        self._parse_gab_config()
        self._configure_adc()

        # runtime state
        self._baseline_ref = None
        self._heater_initial_bias_ua = None
        self._csv_path = None
        self._output_path = None
        self._diagnostics = {'config': None, 'steps': list()}

    def _read_measurement_config(self):
        """
        Override base class to read the gab_sweep section and skip
        directory creation in dry-run mode.
        """

        self._measurement_config = self._config.get_sequencer_setup(
            self._measurement_name,
            self._measurement_list
        )

        config_dict = self._measurement_config[self._measurement_name]
        if 'daq_driver' in config_dict:
            self._daq_driver = config_dict['daq_driver']

        self._facility = self._config.get_facility_num()

        data_path = self._config.get_data_path()
        self._fridge_run = self._config.get_fridge_run()
        fridge_run_name = 'run' + str(self._fridge_run)
        if data_path.find(fridge_run_name) == -1:
            data_path = data_path + '/' + fridge_run_name
        self._base_raw_data_path = data_path + '/raw'
        self._base_automation_data_path = data_path + '/automation'

        if not self._dry_run:
            arg_utils.make_directories(
                [data_path, self._base_automation_data_path]
            )

    def _parse_gab_config(self):
        """
        Cast the gab_sweep config section into typed attributes.
        """

        config_dict = self._measurement_config[self._measurement_name]

        def require(key):
            if key not in config_dict:
                raise ValueError(f'GabSweep: "{key}" required in config!')
            return config_dict[key]

        # thermometry
        self._thermometer_name = str(require('thermometer_name'))
        self._thermometer_instrument = str(
            require('thermometer_instrument')
        )
        self._heater_name = str(require('heater_name'))

        # TES channels
        self._thermometer_tes_channel = str(
            require('thermometer_tes_channel')
        )
        self._heater_tes_channel = str(require('heater_tes_channel'))

        if self._thermometer_tes_channel == self._heater_tes_channel:
            raise ValueError(
                'GabSweep: "thermometer_tes_channel" and '
                '"heater_tes_channel" must be different channels, '
                f'both are "{self._heater_tes_channel}"!'
            )

        # temperature setpoints [mK]
        self._temperature_list_mk = build_temperature_list(
            config_dict=config_dict
        )

        # set_temperature wait parameters
        self._temperature_wait_cycle_time = float(
            require('temperature_wait_cycle_time')
        )
        self._temperature_wait_stable_time = float(
            require('temperature_wait_stable_time')
        )
        self._temperature_max_wait_time = float(
            require('temperature_max_wait_time')
        )
        self._temperature_tolerance = float(
            require('temperature_tolerance')
        )

        # baseline measurement
        self._sample_rate = int(float(require('sample_rate')))
        self._trace_length_ms = float(require('trace_length_ms'))
        self._nb_events_baseline = int(float(require('nb_events_baseline')))
        self._baseline_tolerance_percent = float(
            require('baseline_tolerance_percent')
        )

        # baseline settling: stability check or fixed timer, only the
        # parameters of the selected method are required
        self._use_stability_check = False
        if 'use_stability_check' in config_dict:
            self._use_stability_check = bool(
                config_dict['use_stability_check']
            )

        self._nb_events_stability = None
        self._stability_timeout = None
        self._settle_wait_time = None

        if self._use_stability_check:
            self._nb_events_stability = int(
                float(require('nb_events_stability'))
            )
            self._stability_timeout = float(require('stability_timeout'))
        else:
            self._settle_wait_time = float(require('settle_wait_time'))

        # heater TES feedback
        self._bias_min = float(require('bias_min'))
        self._bias_step_start = float(require('bias_step_start'))
        self._bias_max = float(require('bias_max'))
        self._feedback_timeout = float(require('feedback_timeout'))
        self._post_bias_wait = float(require('post_bias_wait'))

        if self._bias_step_start <= 0:
            raise ValueError(
                'GabSweep: "bias_step_start" must be positive!'
            )
        if self._bias_min < 0:
            raise ValueError(
                'GabSweep: "bias_min" must not be negative!'
            )
        if self._bias_min >= self._bias_max:
            raise ValueError(
                'GabSweep: "bias_min" must be less than "bias_max"!'
            )
        if self._nb_events_baseline < 1:
            raise ValueError(
                'GabSweep: "nb_events_baseline" must be at least 1!'
            )
        if self._use_stability_check and self._nb_events_stability < 1:
            raise ValueError(
                'GabSweep: "nb_events_stability" must be at least 1!'
            )
        if not self._use_stability_check and self._settle_wait_time < 0:
            raise ValueError(
                'GabSweep: "settle_wait_time" must not be negative!'
            )

    def _configure_adc(self):
        """
        Build the ADC configuration for the thermometer TES channel.
        Skipped in dry-run mode.
        """

        self._adc_config = None

        if self._dry_run:
            return

        self._detector_connection_table = (
            self._config.get_adc_connections()
        )

        # normalize the two channel names (accepts detector or TES
        # readout names); the DAQ only reads the thermometer TES
        channels = self._extract_detector_channels(
            [self._thermometer_tes_channel, self._heater_tes_channel]
        )
        self._thermometer_tes_channel = channels[0]
        self._heater_tes_channel = channels[1]

        # two different config names can still resolve to one channel
        if self._thermometer_tes_channel == self._heater_tes_channel:
            raise ValueError(
                'GabSweep: "thermometer_tes_channel" and '
                '"heater_tes_channel" resolve to the same detector '
                f'channel "{self._heater_tes_channel}"!'
            )

        # DAQ is instantiated by the base class only if
        # detector_channels is set
        self._detector_channels = [self._thermometer_tes_channel]

        adc_id, adc_chan = connection_utils.get_adc_channel_info(
            self._detector_connection_table,
            detector_channel=self._thermometer_tes_channel
        )

        adc_setup = self._config.get_adc_setup(adc_id).copy()
        adc_setup['channel_list'] = [int(adc_chan)]
        adc_setup['sample_rate'] = self._sample_rate
        adc_setup['nb_samples'] = int(
            round(self._trace_length_ms / 1000.0 * self._sample_rate)
        )

        # randoms (type 3): no external trigger to wait on, the
        # baseline traces are taken whenever they are requested
        adc_setup['trigger_type'] = 3

        config_dict = self._measurement_config[self._measurement_name]
        if 'voltage_min' in config_dict:
            adc_setup['voltage_min'] = float(config_dict['voltage_min'])
        if 'voltage_max' in config_dict:
            adc_setup['voltage_max'] = float(config_dict['voltage_max'])

        self._adc_config = {adc_id: adc_setup}

    def measure_baseline_quality(self, nb_events=None):
        """
        Measure the thermometer TES baseline: read traces, apply
        qetpy autocuts, return the mean of the per-trace medians
        together with its data quality metrics.

        Parameters
        ----------
        nb_events : int or None
            Number of traces to read. Defaults to nb_events_baseline.

        Returns
        -------
        quality : dict
            Keys: baseline [ADC units], spread [ADC units],
            nb_traces, nb_traces_kept.
        """

        if nb_events is None:
            nb_events = self._nb_events_baseline

        traces = self._daq.read_many_events(nb_events, adctovolt=False)

        # single readout channel: (nb_events, 1, nb_samples)
        traces = traces[:, 0, :]

        cut = qp.autocuts(traces, fs=self._sample_rate)

        if np.sum(cut) == 0:
            print('WARNING: autocuts removed all traces, '
                  'using all traces instead!')
            cut = np.ones(traces.shape[0], dtype=bool)

        trace_medians = np.median(traces[cut, :], axis=1)

        quality = {
            'baseline': float(np.mean(trace_medians)),
            'spread': float(np.std(trace_medians)),
            'nb_traces': int(traces.shape[0]),
            'nb_traces_kept': int(np.sum(cut)),
        }

        return quality

    def measure_baseline(self, nb_events=None):
        """
        Measure the thermometer TES baseline.

        Parameters
        ----------
        nb_events : int or None
            Number of traces to read. Defaults to nb_events_baseline.

        Returns
        -------
        baseline : float
            Thermometer TES baseline [ADC units].
        """

        quality = self.measure_baseline_quality(nb_events=nb_events)

        return quality['baseline']

    def _set_heater_bias_min(self):
        """
        Set the heater TES bias to bias_min, its lowest normal state,
        and wait post_bias_wait for it to settle.
        """

        if self._verbose:
            print('INFO: Setting heater TES bias to bias_min = '
                  f'{self._bias_min:.6g} uA')

        self._instrument.set_tes_bias(
            self._bias_min,
            unit='uA',
            detector_channel=self._heater_tes_channel
        )

        if self._post_bias_wait > 0:
            time.sleep(self._post_bias_wait)

    def _print_baseline_quality(self, quality=None, label=None):
        """
        Print one baseline measurement with its quality metrics.

        Parameters
        ----------
        quality : dict
            Output of measure_baseline_quality.
        label : str
            Short label describing the measurement.
        """

        message = (f'INFO: {label}: baseline = '
                   f'{quality["baseline"]:.6g} [ADC units], '
                   f'spread = {quality["spread"]:.3g}, '
                   f'{quality["nb_traces_kept"]}/{quality["nb_traces"]} '
                   'traces kept by autocuts')

        if self._baseline_ref is not None and self._baseline_ref != 0:
            offset = (quality['baseline'] - self._baseline_ref)
            offset = offset / abs(self._baseline_ref) * 100.0
            message = message + (f', {offset:+.3g} percent from '
                                 'reference')

        print(message)

    def wait_for_settled_baseline(self):
        """
        Wait for the thermometer TES baseline to settle, by the method
        selected with use_stability_check.

        Returns
        -------
        settle_ok : bool
            True if the baseline settled, False on a stability check
            timeout. Always True for the fixed timer.
        history : list of float
            Quick baseline measurements taken [ADC units], empty for
            the fixed timer.
        """

        if self._use_stability_check:
            return self.wait_for_stable_baseline()

        if self._verbose:
            print(f'INFO: Waiting {self._settle_wait_time:.6g} s for '
                  'the thermometer TES baseline to settle')

        if self._settle_wait_time > 0:
            time.sleep(self._settle_wait_time)

        return True, list()

    def wait_for_stable_baseline(self):
        """
        Wait until the last 5 quick baseline measurements agree within
        baseline_tolerance_percent, or stability_timeout is reached.

        Returns
        -------
        stability_ok : bool
            True if stability was reached, False on timeout.
        history : list of float
            All quick baseline measurements taken [ADC units].
        """

        history = list()
        start_time = time.time()

        if self._verbose:
            print('INFO: Waiting for stable thermometer TES baseline')

        while True:

            baseline = self.measure_baseline(
                nb_events=self._nb_events_stability
            )
            history.append(baseline)

            if len(history) >= 5:
                recent = history[-5:]
                reference = recent[-1]
                all_within = True
                if reference == 0:
                    # relative comparison is meaningless at zero,
                    # keep waiting for a nonzero stable baseline
                    all_within = False
                else:
                    for value in recent:
                        offset = abs(value - reference) / abs(reference)
                        if offset * 100.0 > self._baseline_tolerance_percent:
                            all_within = False
                if all_within:
                    return True, history

            if (time.time() - start_time) > self._stability_timeout:
                print('WARNING: Baseline stability timeout '
                      f'({self._stability_timeout:.6g} s), continuing!')
                return False, history

            time.sleep(10)

    def _print_dry_run(self):
        """
        Print the sweep plan without any hardware interaction.
        """

        print('\n=====================================')
        print('DRY RUN - no hardware interaction')
        print('=====================================')
        print(f'\nThermometer TES channel: '
              f'{self._thermometer_tes_channel}')
        print(f'Heater TES channel: {self._heater_tes_channel}')
        print(f'Heater TES bias range: {self._bias_min:.6g} uA '
              f'(bias_min, keeps the heater normal) to '
              f'{self._bias_max:.6g} uA (bias_max)')
        print(f'MC thermometer: {self._thermometer_name} '
              f'({self._thermometer_instrument}), '
              f'heater: {self._heater_name}')

        nb_points = len(self._temperature_list_mk)
        print(f'\nTemperature setpoints [mK] ({nb_points} points):')
        for idx, temperature_mk in enumerate(self._temperature_list_mk):
            print(f'  Step {idx + 1:>{len(str(nb_points))}}/{nb_points}: '
                  f'{temperature_mk:.6g} mK')

        if self._use_stability_check:
            settle_s = self._stability_timeout / 3.0
            print(f'\nBaseline settling: stability check, up to '
                  f'{self._stability_timeout:.6g} s per measurement')
        else:
            settle_s = self._settle_wait_time
            print(f'\nBaseline settling: fixed timer, '
                  f'{self._settle_wait_time:.6g} s per measurement')

        # rough duration estimate: temperature settling plus a few
        # feedback iterations per point
        per_point_s = (self._temperature_wait_stable_time * 60.0
                       + 3.0 * (self._post_bias_wait + settle_s))
        total_min = nb_points * per_point_s / 60.0
        print(f'\nRough estimated duration: {total_min:.4g} min '
              f'(temperature settling dominates)')

    def run(self):
        """
        Run the full Gab sweep. All exit paths funnel to shutdown().
        """

        if self._dry_run:
            self._print_dry_run()
            return

        try:

            # instantiate DAQ and instrument drivers
            self._instantiate_drivers()

            # preflight sanity read of thermometry and TES biases
            mc_temperature_k = self._instrument.get_temperature(
                channel_name=self._thermometer_name,
                instrument_name=self._thermometer_instrument
            )
            thermometer_bias_ua = self._instrument.get_tes_bias(
                detector_channel=self._thermometer_tes_channel,
                unit='uA'
            )
            heater_bias_ua = self._instrument.get_tes_bias(
                detector_channel=self._heater_tes_channel,
                unit='uA'
            )
            # remembered so shutdown can restore the user's bias point
            self._heater_initial_bias_ua = float(heater_bias_ua)

            if self._verbose:
                print(f'INFO: Preflight: MC temperature = '
                      f'{float(mc_temperature_k) * 1000.0:.6g} mK, '
                      f'thermometer TES bias = '
                      f'{float(thermometer_bias_ua):.6g} uA, '
                      f'heater TES bias = '
                      f'{float(heater_bias_ua):.6g} uA')

            self._daq.lock_daq = True
            self._daq.set_adc_config_from_dict(self._adc_config)

            self._create_output_directory()
            self._diagnostics['config'] = copy.deepcopy(
                self._measurement_config[self._measurement_name]
            )

            if self._verbose:
                print('\n=====================================')
                print('INFO: Starting Gab sweep')
                if self._comment and self._comment != 'No comment':
                    print(f'  ({self._comment})')
                print('=====================================')
                print('REMINDER: thermometer TES must be biased in '
                      'transition, PID pre-set. The heater TES bias '
                      f'will be set to bias_min = {self._bias_min:.6g} '
                      'uA (must keep it normal) and set back to its '
                      'original value at shutdown.')

            # the heater TES goes to its lowest normal state before any
            # baseline is measured, so the startup check is taken with
            # the same heater state as every sweep datapoint and cannot
            # bias them
            self._set_heater_bias_min()

            # sanity check the thermometer TES readout before
            # committing to the sweep
            startup_quality = self.measure_baseline_quality()
            self._diagnostics['startup_baseline'] = startup_quality
            self._print_baseline_quality(
                quality=startup_quality,
                label='Startup check'
            )

            for step_index, temperature_mk in (
                    enumerate(self._temperature_list_mk)):

                end_sweep = self.run_single_step(
                    temperature_mk=temperature_mk,
                    step_index=step_index
                )

                if end_sweep:
                    print('INFO: Ending sweep early, heater TES can no '
                          'longer restore the absorber temperature.')
                    break

            if self._verbose:
                print('\nINFO: Gab sweep complete!')

        except KeyboardInterrupt:
            print('\nWARNING: Sweep interrupted by user!')

        except Exception as err:
            print(f'\nERROR during sweep: {err}')
            raise

        finally:
            self.shutdown()

    def shutdown(self):
        """
        Safe shutdown: MC heater setpoint to 0, heater TES bias
        restored to its pre-run value (left untouched if unknown),
        diagnostics flushed. The thermometer TES bias is never touched.
        """

        print('INFO: Safe shutdown, setting heater setpoint to 0 '
              'and restoring the heater TES bias')

        if self._instrument is not None:

            try:
                self._instrument.set_temperature(
                    0,
                    channel_name=self._thermometer_name,
                    heater_channel_name=self._heater_name,
                    instrument_name=self._thermometer_instrument,
                    wait_temperature_reached=False
                )
            except Exception as err:
                print(f'ERROR setting heater setpoint to 0: {err}')

            if self._heater_initial_bias_ua is None:
                print('INFO: Pre-run heater TES bias unknown, '
                      'leaving heater TES bias untouched')
            else:
                try:
                    self._instrument.set_tes_bias(
                        self._heater_initial_bias_ua,
                        unit='uA',
                        detector_channel=self._heater_tes_channel
                    )
                    print('INFO: Heater TES bias set back to its '
                          'original pre-run value')
                except Exception as err:
                    print(f'ERROR restoring heater TES bias: {err}')

        try:
            self._save_diagnostics()
        except Exception as err:
            print(f'ERROR saving diagnostics: {err}')

        if self._daq is not None:
            try:
                self._daq.lock_daq = False
                self._daq.clear()
            except Exception as err:
                print(f'ERROR clearing DAQ: {err}')

    def _create_output_directory(self):
        """
        Create the timestamped output directory, copy the config file
        into it, and write the CSV header.
        """

        now = datetime.now()
        timestamp = now.strftime('%Y%m%d_%H%M%S')
        self._output_path = (self._base_automation_data_path
                             + '/gab_sweep_' + timestamp)
        arg_utils.make_directories(self._output_path)

        # copy config for reproducibility
        shutil.copy(self._sequencer_file,
                    self._output_path + '/gab_sweep.ini')

        # comment saved alongside
        if self._comment and self._comment != 'No comment':
            with open(self._output_path + '/comment.txt', 'w') as f:
                f.write(self._comment + '\n')

        # science dataset CSV with header
        self._csv_path = self._output_path + '/gab_sweep_data.csv'
        with open(self._csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.CSV_COLUMNS)
            writer.writeheader()

        if self._verbose:
            print(f'INFO: Output directory: {self._output_path}')

    def _append_datapoint(self, row_dict=None):
        """
        Append one datapoint to the science dataset CSV.

        Parameters
        ----------
        row_dict : dict
            One row keyed by CSV_COLUMNS.
        """

        with open(self._csv_path, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.CSV_COLUMNS)
            writer.writerow(row_dict)

    def _run_feedback(self):
        """
        Adjust the heater TES bias (between bias_min and bias_max)
        until the thermometer TES baseline returns to the reference.

        Returns
        -------
        result : dict
            Keys: bias_history, baseline_history, converged,
            cap_reached, stability_ok.
        """

        if self._baseline_ref is None:
            raise ValueError(
                'GabSweep: reference baseline not set, '
                'run the first sweep step first!'
            )

        current_bias = float(self._instrument.get_tes_bias(
            detector_channel=self._heater_tes_channel,
            unit='uA'
        ))

        if current_bias < self._bias_min:
            print('WARNING: Heater TES bias below bias_min '
                  f'({self._bias_min:.6g} uA), raising it to keep '
                  'the heater TES normal!')
            self._instrument.set_tes_bias(
                self._bias_min,
                unit='uA',
                detector_channel=self._heater_tes_channel
            )
            if self._post_bias_wait > 0:
                time.sleep(self._post_bias_wait)
            current_bias = self._bias_min

        bias_history = [current_bias]
        baseline_history = [self.measure_baseline()]
        stability_ok = True
        cap_reached = False

        def is_converged(baseline):
            if self._baseline_ref == 0:
                # relative comparison is meaningless at zero
                return False
            offset = abs(baseline - self._baseline_ref)
            offset = offset / abs(self._baseline_ref)
            return (offset * 100.0) <= self._baseline_tolerance_percent

        converged = is_converged(baseline_history[-1])
        start_time = time.time()

        while not converged and not cap_reached:

            if (time.time() - start_time) > self._feedback_timeout:
                print('WARNING: Feedback timeout '
                      f'({self._feedback_timeout:.6g} s), '
                      'recording point as not converged!')
                break

            next_bias = compute_next_bias(
                bias_history=bias_history,
                baseline_history=baseline_history,
                baseline_ref=self._baseline_ref,
                bias_step_start=self._bias_step_start,
                bias_min=self._bias_min
            )

            if next_bias >= self._bias_max:
                next_bias = self._bias_max
                cap_reached = True
                print('WARNING: Heater TES bias cap reached '
                      f'({self._bias_max:.6g} uA)!')

            self._instrument.set_tes_bias(
                next_bias,
                unit='uA',
                detector_channel=self._heater_tes_channel
            )

            if self._post_bias_wait > 0:
                time.sleep(self._post_bias_wait)

            step_settled, _ = self.wait_for_settled_baseline()
            if not step_settled:
                stability_ok = False

            baseline = self.measure_baseline()
            bias_history.append(next_bias)
            baseline_history.append(baseline)
            converged = is_converged(baseline)

            if self._verbose:
                if self._baseline_ref == 0:
                    print(f'INFO: bias = {next_bias:.6g} uA, '
                          f'baseline = {baseline:.6g} '
                          '(reference is 0, offset undefined)')
                else:
                    offset = (baseline - self._baseline_ref)
                    offset = offset / abs(self._baseline_ref) * 100.0
                    print(f'INFO: bias = {next_bias:.6g} uA, '
                          f'baseline offset = {offset:.3g} percent')

        result = {
            'bias_history': bias_history,
            'baseline_history': baseline_history,
            'converged': converged,
            'cap_reached': cap_reached,
            'stability_ok': stability_ok,
        }

        return result

    def run_single_step(self, temperature_mk=None, step_index=None):
        """
        Run one full temperature point of the Gab sweep: set the MC
        temperature, run the heater TES feedback (or measure the
        reference baseline on the first point), record the datapoint.

        Parameters
        ----------
        temperature_mk : float
            MC temperature setpoint in mK.
        step_index : int
            Zero-based index of this point in the sweep.

        Returns
        -------
        end_sweep : bool
            True if the sweep should end (bias cap reached).
        """

        if self._verbose:
            print(f'\nINFO: Step {step_index}: setting MC temperature '
                  f'to {temperature_mk:.6g} mK')

        self._instrument.set_temperature(
            temperature_mk / 1000.0,
            channel_name=self._thermometer_name,
            heater_channel_name=self._heater_name,
            instrument_name=self._thermometer_instrument,
            wait_temperature_reached=True,
            wait_cycle_time=self._temperature_wait_cycle_time,
            wait_stable_time=self._temperature_wait_stable_time,
            max_wait_time=self._temperature_max_wait_time,
            tolerance=self._temperature_tolerance
        )

        end_sweep = False
        step_diagnostics = {'step': step_index,
                            'temperature_setpoint_mk': temperature_mk}

        if step_index == 0:

            # re-assert the lowest normal state: run() already did this
            # before the startup check, but the step must not depend on
            # that when it is driven directly from a notebook
            self._set_heater_bias_min()

        # settled baseline at this temperature, before any feedback:
        # on later steps its offset from the reference is the bias
        # point shift the feedback has to undo
        stability_ok, stability_history = (
            self.wait_for_settled_baseline()
        )
        settled_quality = self.measure_baseline_quality()
        step_diagnostics['stability_history'] = stability_history
        step_diagnostics['settled_quality'] = settled_quality

        if self._verbose:
            self._print_baseline_quality(
                quality=settled_quality,
                label=f'Step {step_index} settled'
            )

        if step_index == 0:

            baseline = settled_quality['baseline']
            self._baseline_ref = baseline
            converged = True
            bias_history = list()
            baseline_history = [baseline]

            if self._verbose:
                print(f'INFO: Reference baseline: {baseline:.6g} '
                      '[ADC units]')

        else:

            result = self._run_feedback()
            baseline = result['baseline_history'][-1]
            converged = result['converged']
            if not result['stability_ok']:
                stability_ok = False
            end_sweep = result['cap_reached']
            bias_history = result['bias_history']
            baseline_history = result['baseline_history']

        # read back the final state
        heater_bias_ua = float(self._instrument.get_tes_bias(
            detector_channel=self._heater_tes_channel,
            unit='uA'
        ))
        mc_temperature_k = self._instrument.get_temperature(
            channel_name=self._thermometer_name,
            instrument_name=self._thermometer_instrument
        )

        offset_percent = 0.0
        if self._baseline_ref is not None and self._baseline_ref != 0:
            offset_percent = (baseline - self._baseline_ref)
            offset_percent = (offset_percent
                              / abs(self._baseline_ref) * 100.0)

        row_dict = {
            'step': step_index,
            'timestamp': datetime.now().isoformat(),
            'temperature_setpoint_mk': temperature_mk,
            'mc_temperature_mk': float(mc_temperature_k) * 1000.0,
            'heater_tes_bias_ua': heater_bias_ua,
            'thermometer_baseline': baseline,
            'baseline_offset_percent': offset_percent,
            'converged': converged,
            'stability_ok': stability_ok,
        }
        self._append_datapoint(row_dict=row_dict)

        step_diagnostics['bias_history'] = bias_history
        step_diagnostics['baseline_history'] = baseline_history
        step_diagnostics['row'] = row_dict
        self._diagnostics['steps'].append(step_diagnostics)

        if self._verbose:
            print(f'INFO: Step {step_index} recorded: MC = '
                  f'{row_dict["mc_temperature_mk"]:.6g} mK, '
                  f'heater TES bias = {heater_bias_ua:.6g} uA, '
                  f'baseline = {baseline:.6g} [ADC units] '
                  f'({offset_percent:+.3g} percent from reference), '
                  f'converged = {converged}, '
                  f'stability_ok = {stability_ok}')

        return end_sweep

    def _save_diagnostics(self):
        """
        Save the diagnostics dictionary as a pickle.
        """

        if self._output_path is None:
            return

        diagnostics_path = self._output_path + '/gab_sweep_diagnostics.p'
        with open(diagnostics_path, 'wb') as f:
            pickle.dump(self._diagnostics, f)
