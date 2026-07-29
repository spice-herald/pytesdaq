"""
Gta sweep sequencer.

Automates the clean thermal conductance (Gta) measurement: sweep the MC
stage temperature downward and take a full IV sweep on one TES at each
temperature. Offline, each IV curve is interpolated to a common R0,
giving I0 and so P0 = I0^2 R0 at the same TES resistance for every bath
temperature, which is fitted for Gta. See
Gta_planning/Gta_sweep_design.md for the full design.

The temperature loop is shared with the Gab measurement. The IV sweep is
performed by the existing IV_dIdV sequencer, configured with dIdV off,
so the data taking is identical to run_iv_didv.py with only IV enabled.
"""

import copy
import csv
import pickle
import shutil
import time
from datetime import datetime

from pytesdaq.sequencer.iv_didv import IV_dIdV
from pytesdaq.sequencer.sequencer import Sequencer
from pytesdaq.sequencer.temperature_sweep import (
    TemperatureSweep,
    config_get,
    config_has,
)
from pytesdaq.utils import arg_utils
from pytesdaq.utils import connection_utils


class GtaSweep(Sequencer):

    # columns of the science dataset CSV, the join table pairing each
    # raw IV series with the temperature it was taken at
    CSV_COLUMNS = ['step', 'timestamp_start', 'timestamp_end',
                   'temperature_setpoint_mk',
                   'mc_temperature_before_mk',
                   'mc_temperature_before_err_mk',
                   'mc_temperature_after_mk',
                   'mc_temperature_after_err_mk',
                   'temperature_drift_mk', 'temperature_ok',
                   'tes_channel', 'iv_group_name', 'iv_raw_data_path',
                   'iv_success']

    def __init__(self, sequencer_file=None, setup_file=None,
                 comment='No comment',
                 dry_run=False, dummy_mode=False,
                 verbose=True):
        """
        Gta thermal conductance sweep measurement.

        Parameters
        ----------
        sequencer_file : str or None
            Path to gta_sweep.ini config file.
        setup_file : str or None
            Path to setup.ini config file.
        comment : str
            Comment string for the measurement.
        dry_run : bool
            If True, only print the sweep plan without any hardware
            interaction.
        dummy_mode : bool
            If True, no actual instrument I/O.
        verbose : bool
            If True, print status messages.

        Returns
        -------
        None
        """

        self._dry_run = dry_run

        super().__init__(
            'gta_sweep',
            comment=comment,
            detector_channels=None,
            sequencer_file=sequencer_file,
            setup_file=setup_file,
            dummy_mode=dummy_mode,
            save_raw_data=False,
            verbose=verbose
        )

        self._parse_gta_config()

        # runtime state
        self._iv_sequencer = None
        self._initial_biases_ua = dict()
        self._biases_captured = False
        self._csv_path = None
        self._output_path = None
        self._diagnostics = {'config': None, 'steps': list()}

    def _read_measurement_config(self):
        """
        Override the base class to read the gta_sweep section and skip
        directory creation in dry-run mode.

        The base class would build an ADC configuration from the
        detector channels. This sequencer reads no traces of its own,
        the composed IV_dIdV does all the data taking, so it keeps
        detector_channels unset and never instantiates a DAQ.

        Returns
        -------
        None
        """

        self._measurement_config = self._config.get_sequencer_setup(
            self._measurement_name,
            self._measurement_list
        )

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

    def _parse_gta_config(self):
        """
        Cast the gta_sweep config section into typed attributes and
        classify the channels.

        Returns
        -------
        None
        """

        config_dict = self._measurement_config[self._measurement_name]

        def require(key):
            if not config_has(config_dict, key):
                raise ValueError(f'GtaSweep: "{key}" required in config!')
            return config_get(config_dict, key)

        # MC temperature sweep, shared with the Gab measurement
        self._temperature_sweep = TemperatureSweep(
            config_dict=config_dict,
            verbose=self._verbose
        )

        self._post_settle_wait_s = 0.0
        if config_has(config_dict, 'post_temperature_settle_wait_s'):
            self._post_settle_wait_s = float(
                config_get(config_dict, 'post_temperature_settle_wait_s')
            )

        if self._post_settle_wait_s < 0:
            raise ValueError(
                'GtaSweep: "post_temperature_settle_wait_s" must not '
                'be negative!'
            )

        # the single TES channel to sweep
        self._detector_connection_table = (
            self._config.get_adc_connections()
        )

        requested_channel = str(require('tes_channel'))
        channels = self._extract_detector_channels([requested_channel])
        self._tes_channel = channels[0]

        tes_channels, non_tes_channels = self.classify_tes_channels()

        if self._tes_channel not in tes_channels:
            raise ValueError(
                f'GtaSweep: "tes_channel" = "{requested_channel}" '
                f'resolves to detector channel "{self._tes_channel}", '
                'which is not marked as a TES channel in the setup '
                'file. Real TES channels are the connection lines with '
                'a "tes:" field. Channels without one, such as the TTL '
                'input and the accelerometer readouts, cannot be '
                'biased!'
            )

        # every other real TES channel is zeroed for the duration of
        # the sweep, so no other device dissipates power into the
        # absorber
        self._zero_channels = list()
        for channel in tes_channels:
            if channel != self._tes_channel:
                self._zero_channels.append(channel)

        self._non_tes_channels = non_tes_channels

    def classify_tes_channels(self):
        """
        Split the ADC connection map into real TES channels and
        everything else.

        Real TES channels are the connection lines that declare a
        "tes:" field in the setup file. Lines without one, such as the
        TTL input and the accelerometer readouts, are readout channels
        that must never be biased.

        Returns
        -------
        tes_channels : list of str
            Detector channel names of the real TES channels.
        non_tes_channels : list of str
            Detector channel names of everything else.
        """

        items = connection_utils.get_items(
            self._detector_connection_table
        )

        tes_channels = list()
        non_tes_channels = list()

        for index, channel in enumerate(items['detector_channel']):
            if items['is_tes_channel'][index]:
                tes_channels.append(channel)
            else:
                non_tes_channels.append(channel)

        return tes_channels, non_tes_channels

    def capture_initial_biases(self):
        """
        Read and remember the pre-run TES bias of every real TES
        channel, so they can all be restored when the sweep ends.

        Calling this again after the biases have been changed would
        record the changed values, silently discarding the user's
        bias points, so the first capture wins. Completeness is
        tracked with a dedicated flag rather than inferred from the
        dict being non-empty, because a read failure partway through
        would otherwise leave a partial dict that looks "captured"
        and can never be corrected by a retry. A capture that raises
        partway through leaves no partial state behind: it reads into
        a local dict first and only commits it, and sets the flag,
        once every channel has been read successfully.

        Parameters
        ----------
        None

        Returns
        -------
        initial_biases_ua : dict
            Detector channel name to TES bias [uA].
        """

        if self._biases_captured:
            return self._initial_biases_ua

        channels = [self._tes_channel] + self._zero_channels

        captured_biases_ua = dict()
        for channel in channels:
            bias_ua = float(self._instrument.get_tes_bias(
                detector_channel=channel,
                unit='uA'
            ))
            captured_biases_ua[channel] = bias_ua

        self._initial_biases_ua = captured_biases_ua
        self._biases_captured = True

        if self._verbose:
            print('INFO: Pre-run TES biases [uA]: '
                  + ', '.join(
                      f'{channel} = {bias:.6g}'
                      for channel, bias in self._initial_biases_ua.items()
                  ))

        return self._initial_biases_ua

    def zero_other_channels(self):
        """
        Set every real TES channel except the swept one to zero bias,
        so that no other device dissipates power into the absorber.

        Channels that are not TESs are never written to.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        if len(self._zero_channels) == 0:
            if self._verbose:
                print('INFO: No other TES channels to zero')
            return

        if self._verbose:
            print('INFO: Setting TES bias to 0 uA on '
                  f'{", ".join(self._zero_channels)}')

        for channel in self._zero_channels:
            self._instrument.set_tes_bias(
                bias=0,
                unit='uA',
                detector_channel=channel
            )

    def restore_initial_biases(self):
        """
        Put every real TES channel back to its pre-run bias.

        A channel that fails to restore is reported and the rest are
        still attempted, because a channel left biased keeps heating
        the absorber.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        if len(self._initial_biases_ua) == 0:
            print('INFO: Pre-run TES biases unknown, leaving TES '
                  'biases untouched')
            return

        for channel, bias_ua in self._initial_biases_ua.items():
            try:
                self._instrument.set_tes_bias(
                    bias=bias_ua,
                    unit='uA',
                    detector_channel=channel
                )
                print(f'INFO: TES bias on {channel} set back to its '
                      f'original pre-run value of {bias_ua:.6g} uA')
            except Exception as err:
                print(f'ERROR restoring TES bias on {channel}: {err}')

    def _print_dry_run(self):
        """
        Print the sweep plan without any hardware interaction.

        Returns
        -------
        None
        """

        config_dict = self._measurement_config[self._measurement_name]

        print('\n=====================================')
        print('DRY RUN - no hardware interaction')
        print('=====================================')

        print(f'\nTES channel to sweep: {self._tes_channel}')
        print('TES channels to be zeroed for the sweep and restored '
              f'afterwards: {", ".join(self._zero_channels)}')
        if len(self._non_tes_channels) > 0:
            print('Not TES channels, never touched: '
                  f'{", ".join(self._non_tes_channels)}')

        print(f'\nMC thermometer: '
              f'{self._temperature_sweep.thermometer_name} '
              f'({self._temperature_sweep.thermometer_instrument}), '
              f'heater: {self._temperature_sweep.heater_name}')

        temperatures = self._temperature_sweep.temperature_list_mk
        nb_points = len(temperatures)
        print(f'\nTemperature setpoints [mK] ({nb_points} points):')
        for index, temperature_mk in enumerate(temperatures):
            print(f'  Step {index + 1:>{len(str(nb_points))}}'
                  f'/{nb_points}: {temperature_mk:.6g} mK')

        print(f'\nMC temperature settling: polled every '
              f'{self._temperature_sweep.poll_interval_s:.6g} s, must '
              f'hold within '
              f'{self._temperature_sweep.tolerance_frac * 100.0:.3g} '
              f'percent for '
              f'{self._temperature_sweep.stable_time_s:.6g} s, up to '
              f'{self._temperature_sweep.max_wait_time_s:.6g} s')

        print(f'MC temperature sampling: '
              f'{self._temperature_sweep.sampling_time_s:.6g} s window, '
              'measured before and after each IV sweep')

        iv_config = self._config.get_sequencer_setup('iv_didv', ['iv'])
        bias_vect = iv_config['iv_didv'].get('tes_bias_vect')
        print(f'\nTES bias sweep [uA]: {bias_vect}')
        print(f'IV run time per bias point: '
              f'{iv_config["iv"].get("run_time")} s')

        print('\nOne IV sweep is taken per temperature setpoint. Raw '
              'data is saved as a normal series group per step, and '
              'gta_sweep_data.csv pairs each series with its '
              'temperature.')

    def _build_iv_sequencer(self):
        """
        Build the IV_dIdV sequencer that performs the IV sweep at each
        temperature.

        It reads the [iv_didv] and [iv] sections of the same config
        file. Its own temperature sweep is disabled: this class owns
        temperature. Its instrument control object is supplied here so
        that only one is built for the whole sweep.

        Parameters
        ----------
        None

        Returns
        -------
        iv_sequencer : IV_dIdV
            Configured IV sequencer.
        """

        iv_sequencer = IV_dIdV(
            iv=True,
            didv=False,
            rp=False,
            rn=False,
            temperature_sweep=False,
            tes_bias_sweep=True,
            online_iv=True,
            comment=self._comment,
            sweep_channels=[self._tes_channel],
            saved_channels=None,
            sequencer_file=self._sequencer_file,
            setup_file=self._setup_file,
            dummy_mode=self._dummy_mode,
            verbose=self._verbose
        )

        iv_sequencer.instrument_control = self._instrument

        return iv_sequencer

    def run(self):
        """
        Run the full Gta sweep. All exit paths funnel to shutdown().

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        if self._dry_run:
            self._print_dry_run()
            return

        try:

            self._instantiate_drivers()
            self._temperature_sweep.instrument = self._instrument

            # every bias is remembered before anything is changed
            self.capture_initial_biases()

            if self._verbose:
                print('\n=====================================')
                print('INFO: Starting Gta sweep')
                if self._comment and self._comment != 'No comment':
                    print(f'  ({self._comment})')
                print('=====================================')
                print('REMINDER: the TES must be biased in transition '
                      'and stay in transition across the whole '
                      'temperature range, and the PID must be pre-set. '
                      'Every other TES channel is set to 0 uA now and '
                      'restored at shutdown.')

            self.zero_other_channels()

            self._iv_sequencer = self._build_iv_sequencer()

            self._create_output_directory()
            self._diagnostics['config'] = copy.deepcopy(
                self._measurement_config[self._measurement_name]
            )

            temperatures = self._temperature_sweep.temperature_list_mk
            for step_index, temperature_mk in enumerate(temperatures):
                self.run_single_step(
                    temperature_mk=temperature_mk,
                    step_index=step_index
                )

            if self._verbose:
                print('\nINFO: Gta sweep complete!')

        except KeyboardInterrupt:
            print('\nWARNING: Sweep interrupted by user!')

        except Exception as err:
            print(f'\nERROR during sweep: {err}')
            raise

        finally:
            self.shutdown()

    def run_single_step(self, temperature_mk=None, step_index=None):
        """
        Run one temperature point: set the MC temperature, wait for it,
        measure it, take a full IV sweep, measure the temperature
        again, and record the datapoint.

        The temperature is measured on both sides of the IV sweep
        because an IV sweep is long enough that the bath can drift over
        its duration.

        Parameters
        ----------
        temperature_mk : float
            MC temperature setpoint [mK].
        step_index : int
            Zero-based index of this point in the sweep.

        Returns
        -------
        row_dict : dict
            The recorded datapoint, keyed by CSV_COLUMNS.
        """

        if self._verbose:
            print(f'\nINFO: Step {step_index}: setting MC temperature '
                  f'to {temperature_mk:.6g} mK')

        timestamp_start = datetime.now().isoformat()

        self._temperature_sweep.set_setpoint(
            temperature_mk=temperature_mk
        )
        temperature_ok, temperature_history = (
            self._temperature_sweep.wait_for_temperature(
                temperature_mk=temperature_mk
            )
        )

        if self._post_settle_wait_s > 0:
            time.sleep(self._post_settle_wait_s)

        before = self._temperature_sweep.measure_temperature()
        before_mk = before['temperature_k'] * 1000.0
        before_err_mk = before['temperature_err_k'] * 1000.0

        if self._verbose:
            print(f'INFO: Step {step_index}: MC = {before_mk:.6g} '
                  f'+- {before_err_mk:.3g} mK, starting IV sweep')

        # tag the IV series with the condition it was taken at
        self._iv_sequencer.run_comment_suffix = (
            f', Gta step {step_index}, T_set = {temperature_mk:.6g} mK'
        )

        iv_success = self._iv_sequencer._run_iv_didv()
        if iv_success is None:
            iv_success = True

        after = self._temperature_sweep.measure_temperature()
        after_mk = after['temperature_k'] * 1000.0
        after_err_mk = after['temperature_err_k'] * 1000.0

        row_dict = {
            'step': step_index,
            'timestamp_start': timestamp_start,
            'timestamp_end': datetime.now().isoformat(),
            'temperature_setpoint_mk': temperature_mk,
            'mc_temperature_before_mk': before_mk,
            'mc_temperature_before_err_mk': before_err_mk,
            'mc_temperature_after_mk': after_mk,
            'mc_temperature_after_err_mk': after_err_mk,
            'temperature_drift_mk': after_mk - before_mk,
            'temperature_ok': temperature_ok,
            'tes_channel': self._tes_channel,
            'iv_group_name': self._iv_sequencer.group_name,
            'iv_raw_data_path': self._iv_sequencer.raw_data_path,
            'iv_success': bool(iv_success),
        }

        self._append_datapoint(row_dict=row_dict)

        step_diagnostics = {
            'step': step_index,
            'temperature_history': temperature_history,
            'temperature_before': before,
            'temperature_after': after,
            'row': row_dict,
        }
        self._diagnostics['steps'].append(step_diagnostics)

        if self._verbose:
            print(f'INFO: Step {step_index} recorded: MC = '
                  f'{before_mk:.6g} mK before, {after_mk:.6g} mK after '
                  f'({after_mk - before_mk:+.3g} mK drift), '
                  f'temperature_ok = {temperature_ok}, IV series = '
                  f'{self._iv_sequencer.group_name}')

        return row_dict

    def shutdown(self):
        """
        Safe shutdown: MC heater setpoint to 0, every TES bias restored
        to its pre-run value, diagnostics flushed.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        print('INFO: Safe shutdown, setting the heater setpoint to 0 '
              'and restoring the TES biases')

        if self._instrument is not None:

            try:
                self._temperature_sweep.heater_to_zero()
            except Exception as err:
                print(f'ERROR setting heater setpoint to 0: {err}')

            self.restore_initial_biases()

        try:
            self._save_diagnostics()
        except Exception as err:
            print(f'ERROR saving diagnostics: {err}')

    def _create_output_directory(self):
        """
        Create the timestamped output directory, copy the config file
        into it, and write the CSV header.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        now = datetime.now()
        timestamp = now.strftime('%Y%m%d_%H%M%S')
        self._output_path = (self._base_automation_data_path
                             + '/gta_sweep_' + timestamp)
        arg_utils.make_directories(self._output_path)

        # copy config for reproducibility
        shutil.copy(self._sequencer_file,
                    self._output_path + '/gta_sweep.ini')

        if self._comment and self._comment != 'No comment':
            with open(self._output_path + '/comment.txt', 'w') as f:
                f.write(self._comment + '\n')

        # science dataset CSV with header
        self._csv_path = self._output_path + '/gta_sweep_data.csv'
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

        Returns
        -------
        None
        """

        if self._csv_path is None:
            return

        with open(self._csv_path, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.CSV_COLUMNS)
            writer.writerow(row_dict)

    def _save_diagnostics(self):
        """
        Save the diagnostics dictionary as a pickle.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        if self._output_path is None:
            return

        diagnostics_path = self._output_path + '/gta_sweep_diagnostics.p'
        with open(diagnostics_path, 'wb') as f:
            pickle.dump(self._diagnostics, f)
