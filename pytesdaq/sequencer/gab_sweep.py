"""
Gab sweep sequencer.

Automates the thermal conductance (Gab) measurement: sweep the MC stage
temperature downward while adjusting the heater TES bias so that the
thermometer TES stays at a fixed bias point. The bias point is measured
as the thermometer TES resistance R0, extracted online from a square
wave dIdV fit (3-pole fit, infinite loop gain approximation). The
heater TES bias is never taken below bias_min so it stays normal. No
raw TES data is saved. See Gab_planning/Gab_sweep_design.md for the
full design.
"""

import copy
import csv
import pickle
import shutil
import time
from datetime import datetime

import numpy as np
import qetpy as qp
from qetpy.core._biasparams import get_biasparams_ilg

from pytesdaq.sequencer.sequencer import Sequencer
from pytesdaq.sequencer.temperature_sweep import (
    TemperatureSweep,
    build_temperature_list,
    config_get,
    config_has,
    fit_temperature_gaussian,
)
from pytesdaq.utils import arg_utils
from pytesdaq.utils import connection_utils


def compute_next_bias(bias_history=None,
                      r0_history=None,
                      r0_ref=None,
                      bias_step_start=None,
                      bias_min=0.0,
                      noise_floor=0.0):
    """
    Compute the next heater TES bias from the feedback history.

    First move: fixed step up by bias_step_start. Later moves: least
    squares fit of R0 versus bias over the full history, then a step
    toward r0_ref along the fit, clamped to 2x bias_step_start and
    halved after overshooting the reference. Repeated biases in the
    history (confirmation readings) are averaged naturally by the fit.
    Only when the fit sees no R0 response above the noise floor across
    the whole history does the probe step double in the same direction
    instead, up to 4x bias_step_start.

    Parameters
    ----------
    bias_history : list of float
        Heater TES biases applied so far at this temperature [uA].
    r0_history : list of float
        Thermometer TES R0 after each bias [Ohms].
    r0_ref : float
        Reference R0 to return to [Ohms].
    bias_step_start : float
        Initial and fallback bias step [uA].
    bias_min : float
        Minimum bias keeping the heater TES normal [uA].
    noise_floor : float
        R0 repeatability scatter at fixed conditions [Ohms]. A fitted
        R0 response across the history smaller than 2x this value is
        treated as unmeasurable.

    Returns
    -------
    next_bias : float
        Next heater TES bias [uA], never below bias_min.
    """

    if (bias_history is None or r0_history is None
            or len(bias_history) == 0
            or len(bias_history) != len(r0_history)):
        raise ValueError(
            'GabSweep: bias and R0 histories must be non-empty '
            'and the same length!'
        )

    last_bias = float(bias_history[-1])
    last_r0 = float(r0_history[-1])
    fixed_step = float(bias_step_start)
    max_step = 2.0 * fixed_step
    max_probe_step = 4.0 * fixed_step
    min_bias = float(bias_min)

    # most recent pair of consecutive points with distinct biases:
    # sets the probe direction and the overshoot cap, since repeated
    # biases (confirmation readings, clamping at the floor) carry no
    # slope information
    pair_index = None
    for index in range(len(bias_history) - 1, 0, -1):
        if float(bias_history[index]) != float(bias_history[index - 1]):
            pair_index = index
            break

    if pair_index is None:
        # no distinct pair yet, probe up (the heater can only add
        # power, and a colder bath always needs more of it)
        step = fixed_step

    else:

        delta_bias = (float(bias_history[pair_index])
                      - float(bias_history[pair_index - 1]))

        # least squares fit of R0 versus bias over the full history:
        # repeated biases are averaged, drift on single points is
        # diluted
        fit = np.polyfit(
            np.asarray(bias_history, dtype=float),
            np.asarray(r0_history, dtype=float),
            1
        )
        slope = float(fit[0])

        bias_span = (float(np.max(bias_history))
                     - float(np.min(bias_history)))
        predicted_response = abs(slope) * bias_span

        if predicted_response <= (2.0 * float(noise_floor)):

            # even across the full bias span the fitted response does
            # not rise above the noise: no slope can be trusted,
            # double the probe in the same direction until one appears
            step_magnitude = 2.0 * abs(delta_bias)
            if step_magnitude < fixed_step:
                step_magnitude = fixed_step
            if step_magnitude > max_probe_step:
                step_magnitude = max_probe_step
            step = float(np.sign(delta_bias)) * step_magnitude

        else:

            step = (float(r0_ref) - last_r0) / slope

            # halve the allowed step after overshooting the reference
            previous_side = (float(r0_history[-2]) - float(r0_ref))
            current_side = last_r0 - float(r0_ref)
            if (previous_side * current_side) < 0:
                overshoot_cap = abs(delta_bias) / 2.0
                if step > overshoot_cap:
                    step = overshoot_cap
                if step < -overshoot_cap:
                    step = -overshoot_cap

            if step > max_step:
                step = max_step
            if step < -max_step:
                step = -max_step

    next_bias = last_bias + step
    if next_bias < min_bias:
        next_bias = min_bias

    return next_bias


def fit_didv_r0(traces=None, sample_rate=None,
                sgfreq=None, sgamp=None,
                rsh=None, rp=None, ibias=None,
                r0_guess=0.15, fcutoff=50000.0):
    """
    Fit square wave dIdV traces and extract the TES bias point R0
    using the infinite loop gain approximation.

    The traces are averaged and fit with the qetpy 3-pole dIdV model
    (frequencies above fcutoff are excluded from the fit, acting as a
    lowpass filter), then R0 is computed from the zero frequency dVdI
    with the known shunt and parasitic resistances.

    Parameters
    ----------
    traces : ndarray
        dIdV traces in amps, shape (nb_traces, nb_samples), each
        trace triggered on the signal generator.
    sample_rate : float
        Sample rate [Hz].
    sgfreq : float
        Signal generator square wave frequency [Hz].
    sgamp : float
        Signal generator current amplitude, peak to peak [Amps].
    rsh : float
        Shunt resistance [Ohms].
    rp : float
        Parasitic resistance [Ohms].
    ibias : float
        Thermometer TES bias current [Amps], used for the derived
        bias parameters (i0, p0).
    r0_guess : float
        Initial guess of R0 for the fit [Ohms].
    fcutoff : float
        Lowpass cutoff frequency for the fit [Hz].

    Returns
    -------
    result : dict
        Keys: r0, r0_err, i0, p0 [SI units], fit_cost, fit_params.
    """

    didv = qp.DIDV(
        traces,
        sample_rate,
        sgfreq,
        sgamp,
        rsh,
        r0=r0_guess,
        rp=rp,
    )

    didv.dofit(poles=3, fcutoff=fcutoff)
    fit = didv.fitresult(poles=3)

    biasparams = get_biasparams_ilg(
        fit['params'],
        fit['cov'],
        ibias,
        0.0,
        rsh,
        rp
    )

    # propagate the R0 uncertainty from the fit covariance here: the
    # qetpy get_biasparams_ilg "r0_err" is the variance (jacobian
    # times covariance without the square root), not the uncertainty.
    # R0 = |dVdI(0)| + rl with dVdI(0) = A + B / (1 - C), so
    # var(R0) = J cov J^T with J the dVdI(0) gradient
    params = fit['params']
    cov = np.asarray(fit['cov'], dtype=float)
    jacobian = np.zeros(cov.shape[0])
    if cov.shape[0] == 5:
        # parameter order: A, B, tau1, tau2, dt
        jacobian[0] = 1.0
        jacobian[1] = 1.0
    else:
        # parameter order: A, B, C, tau1, tau2, tau3, dt
        c_param = float(params['C'])
        jacobian[0] = 1.0
        jacobian[1] = 1.0 / (1.0 - c_param)
        jacobian[2] = float(params['B']) / ((1.0 - c_param) ** 2)
    r0_variance = float(np.dot(jacobian, np.dot(cov, jacobian)))
    r0_err = float(np.sqrt(abs(r0_variance)))

    result = {
        'r0': float(biasparams['r0']),
        'r0_err': r0_err,
        'i0': float(biasparams['i0']),
        'p0': float(biasparams['p0']),
        'fit_cost': float(fit['cost']),
        'fit_params': copy.deepcopy(fit['params']),
    }

    return result


def propagate_r0_error_to_bias(r0=None, r0_err=None, heater_bias=None):
    """
    Propagate the fractional R0 uncertainty to the heater TES bias,
    assuming linearity: the fractional uncertainty in the heater bias
    is taken equal to the fractional uncertainty in R0 (a 10 percent
    R0 uncertainty gives a 10 percent bias uncertainty). This simple
    model may be refined later.

    Parameters
    ----------
    r0 : float
        Thermometer TES R0 [Ohms].
    r0_err : float
        Uncertainty in R0 [Ohms].
    heater_bias : float
        Heater TES bias [uA].

    Returns
    -------
    heater_bias_err : float
        Uncertainty in the heater TES bias [uA].
    """

    if r0 == 0:
        return 0.0

    r0_fractional_err = abs(float(r0_err) / float(r0))

    return r0_fractional_err * abs(float(heater_bias))


class GabSweep(Sequencer):

    # columns of the science dataset CSV
    CSV_COLUMNS = ['step', 'timestamp',
                   'temperature_setpoint_mk',
                   'mc_temperature_mk', 'mc_temperature_err_mk',
                   'heater_tes_bias_ua', 'heater_tes_bias_err_ua',
                   'thermometer_r0_ohms', 'thermometer_r0_err_ohms',
                   'r0_offset_percent', 'converged',
                   'pinned_at_floor', 'stability_ok',
                   'temperature_ok']

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
        self._r0_ref = None
        self._r0_noise_floor = 0.0
        self._heater_initial_bias_ua = None
        self._bias_min_actual = None
        self._sg_current_amps_pp = None
        self._close_loop_norm = None
        self._thermometer_bias_amps = None
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
        if config_has(config_dict, 'daq_driver'):
            self._daq_driver = config_get(config_dict, 'daq_driver')

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
            if not config_has(config_dict, key):
                raise ValueError(f'GabSweep: "{key}" required in config!')
            return config_get(config_dict, key)

        # MC temperature sweep, shared with the Gta measurement
        self._temperature_sweep = TemperatureSweep(
            config_dict=config_dict,
            verbose=self._verbose
        )

        # aliases, so the rest of this class reads unchanged
        self._thermometer_name = self._temperature_sweep.thermometer_name
        self._thermometer_instrument = (
            self._temperature_sweep.thermometer_instrument
        )
        self._heater_name = self._temperature_sweep.heater_name
        self._temperature_list_mk = (
            self._temperature_sweep.temperature_list_mk
        )

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

        # dIdV based R0 measurement of the thermometer TES
        self._sample_rate = int(float(require('sample_rate_Hz')))

        self._trace_length_ms = 50.0
        if config_has(config_dict, 'trace_length_ms'):
            self._trace_length_ms = float(config_get(config_dict, 'trace_length_ms'))

        self._nb_events_didv = 50
        if config_has(config_dict, 'nb_events_didv'):
            self._nb_events_didv = int(float(config_get(config_dict, 'nb_events_didv')))

        self._r0_tolerance_percent = float(
            require('r0_tolerance_percent')
        )

        # TES circuit resistances, required for the dIdV fit
        # (config in mOhms, kept in Ohms internally)
        self._rshunt = float(require('rshunt_mOhm')) / 1000.0
        self._rparasitic = float(require('rparasitic_mOhm')) / 1000.0

        if self._rshunt <= 0:
            raise ValueError('GabSweep: "rshunt_mOhm" must be positive!')
        if self._rparasitic < 0:
            raise ValueError(
                'GabSweep: "rparasitic_mOhm" must not be negative!'
            )

        # signal generator square wave settings (optional keys)
        self._signal_gen_frequency = 50.0
        if config_has(config_dict, 'signal_gen_frequency_Hz'):
            self._signal_gen_frequency = float(
                config_get(config_dict, 'signal_gen_frequency_Hz')
            )

        # amplitude: voltage [mVpp] for an external signal generator,
        # current [uApp] for magnicon, only one may be set
        self._signal_gen_voltage = None
        self._signal_gen_current = None
        if (config_has(config_dict, 'signal_gen_voltage_mVpp')
                and config_has(config_dict, 'signal_gen_current_uApp')):
            raise ValueError(
                'GabSweep: set the signal generator amplitude with '
                'either "signal_gen_voltage_mVpp" or '
                '"signal_gen_current_uApp", not both!'
            )
        if config_has(config_dict, 'signal_gen_current_uApp'):
            self._signal_gen_current = float(
                config_get(config_dict, 'signal_gen_current_uApp')
            )
        else:
            self._signal_gen_voltage = 20.0
            if config_has(config_dict, 'signal_gen_voltage_mVpp'):
                self._signal_gen_voltage = float(
                    config_get(config_dict, 'signal_gen_voltage_mVpp')
                )

        self._signal_gen_offset = 0.0
        if config_has(config_dict, 'signal_gen_offset_mV'):
            self._signal_gen_offset = float(
                config_get(config_dict, 'signal_gen_offset_mV')
            )

        self._signal_gen_phase = 0.0
        if config_has(config_dict, 'signal_gen_phase_deg'):
            self._signal_gen_phase = float(
                config_get(config_dict, 'signal_gen_phase_deg')
            )

        # dIdV fit parameters (optional keys)
        self._didv_fcutoff = 50000.0
        if config_has(config_dict, 'didv_fcutoff_Hz'):
            self._didv_fcutoff = float(config_get(config_dict, 'didv_fcutoff_Hz'))

        self._r0_guess = 0.15
        if config_has(config_dict, 'r0_guess_mOhm'):
            self._r0_guess = float(config_get(config_dict, 'r0_guess_mOhm')) / 1000.0

        if self._signal_gen_frequency <= 0:
            raise ValueError(
                'GabSweep: "signal_gen_frequency_Hz" must be positive!'
            )
        if self._didv_fcutoff <= 0:
            raise ValueError(
                'GabSweep: "didv_fcutoff_Hz" must be positive!'
            )
        if self._trace_length_ms <= 0:
            raise ValueError(
                'GabSweep: "trace_length_ms" must be positive!'
            )

        # R0 settling: stability check or fixed timer, only the
        # parameters of the selected method are required
        self._use_stability_check = False
        if config_has(config_dict, 'use_stability_check'):
            self._use_stability_check = bool(
                config_get(config_dict, 'use_stability_check')
            )

        self._nb_events_stability = None
        self._stability_timeout = None
        self._settle_wait_time = None

        if self._use_stability_check:
            self._nb_events_stability = int(
                float(require('nb_events_stability'))
            )
            self._stability_timeout = float(require('stability_timeout_s'))
        else:
            self._settle_wait_time = float(require('settle_wait_time_s'))

        # R0 drift characterization at startup (optional keys):
        # repeated R0 measurements at fixed conditions, their scatter
        # is the noise floor the feedback has to beat
        self._drift_check_nb_measurements = 5
        if config_has(config_dict, 'drift_check_nb_measurements'):
            self._drift_check_nb_measurements = int(
                float(config_get(config_dict, 'drift_check_nb_measurements'))
            )
        self._drift_check_wait_time = 60.0
        if config_has(config_dict, 'drift_check_wait_time_s'):
            self._drift_check_wait_time = float(
                config_get(config_dict, 'drift_check_wait_time_s')
            )

        if self._drift_check_nb_measurements < 0:
            raise ValueError(
                'GabSweep: "drift_check_nb_measurements" must not '
                'be negative!'
            )
        if self._drift_check_wait_time < 0:
            raise ValueError(
                'GabSweep: "drift_check_wait_time_s" must not be '
                'negative!'
            )

        # heater TES feedback
        self._bias_min = float(require('bias_min_uA'))
        self._bias_step_start = float(require('bias_step_start_uA'))
        self._bias_max = float(require('bias_max_uA'))
        self._feedback_timeout = float(require('feedback_timeout_s'))
        self._post_bias_wait = float(require('post_bias_wait_s'))

        if self._bias_step_start <= 0:
            raise ValueError(
                'GabSweep: "bias_step_start_uA" must be positive!'
            )
        if self._bias_min < 0:
            raise ValueError(
                'GabSweep: "bias_min_uA" must not be negative!'
            )
        if self._bias_min >= self._bias_max:
            raise ValueError(
                'GabSweep: "bias_min_uA" must be less than '
                '"bias_max_uA"!'
            )
        if self._nb_events_didv < 1:
            raise ValueError(
                'GabSweep: "nb_events_didv" must be at least 1!'
            )
        if self._use_stability_check and self._nb_events_stability < 1:
            raise ValueError(
                'GabSweep: "nb_events_stability" must be at least 1!'
            )
        if not self._use_stability_check and self._settle_wait_time < 0:
            raise ValueError(
                'GabSweep: "settle_wait_time_s" must not be negative!'
            )

    def _configure_adc(self):
        """
        Build the ADC configuration for the thermometer TES channel.
        Skipped in dry-run mode.

        The trace length is rounded to an integer number of signal
        generator periods so the square wave harmonics land on FFT
        bins, and the ADC is triggered on the signal generator so the
        traces can be averaged coherently.
        """

        # trace length as an integer number of signal generator
        # periods (needed in dry-run mode too, for the plan printout)
        nb_cycles = round(
            self._trace_length_ms / 1000.0 * self._signal_gen_frequency
        )
        if nb_cycles < 1:
            nb_cycles = 1
        self._nb_cycles = nb_cycles
        self._trace_length_ms_actual = (
            nb_cycles / self._signal_gen_frequency * 1000.0
        )

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
        adc_setup['nb_samples'] = int(round(
            self._nb_cycles * self._sample_rate
            / self._signal_gen_frequency
        ))

        # external trigger (type 2): each trace starts on the signal
        # generator sync edge so the square wave phase is the same in
        # every trace and the traces average coherently
        adc_setup['trigger_type'] = 2
        trigger_channel = '/Dev1/pfi0'
        if ('device_name' in adc_setup
                and 'trigger_channel' in adc_setup):
            trigger_channel = ('/' + adc_setup['device_name'] + '/'
                               + adc_setup['trigger_channel'])
        adc_setup['trigger_channel'] = trigger_channel

        config_dict = self._measurement_config[self._measurement_name]
        if config_has(config_dict, 'voltage_min_V'):
            adc_setup['voltage_min'] = float(config_get(config_dict, 'voltage_min_V'))
        if config_has(config_dict, 'voltage_max_V'):
            adc_setup['voltage_max'] = float(config_get(config_dict, 'voltage_max_V'))

        self._adc_config = {adc_id: adc_setup}

    def _instantiate_drivers(self):
        """
        Instantiate drivers and hand the instrument control object to
        the shared temperature sweep.

        Returns
        -------
        None
        """

        super()._instantiate_drivers()
        self._temperature_sweep.instrument = self._instrument

    def setup_signal_generator(self):
        """
        Turn on the signal generator on the thermometer TES channel,
        set the configured dIdV square wave, connect it to the TES
        line, and read back the actual current amplitude used as
        "sgamp" by the dIdV fit.
        """

        if self._verbose:
            amplitude = ''
            if self._signal_gen_current is not None:
                amplitude = f'{self._signal_gen_current:.6g} uApp'
            else:
                amplitude = f'{self._signal_gen_voltage:.6g} mVpp'
            print('INFO: Setting up dIdV square wave on the '
                  f'thermometer TES: {self._signal_gen_frequency:.6g} '
                  f'Hz, {amplitude}, offset = '
                  f'{self._signal_gen_offset:.6g} mV, phase = '
                  f'{self._signal_gen_phase:.6g} deg')

        # the signal generator must be on before its parameters can be
        # changed when the TES bias and signal generator controllers
        # are the same instrument
        self._instrument.set_signal_gen_onoff(
            'on',
            detector_channel=self._thermometer_tes_channel
        )

        self._instrument.set_signal_gen_params(
            detector_channel=self._thermometer_tes_channel,
            source='tes',
            voltage=self._signal_gen_voltage,
            voltage_unit='mV',
            current=self._signal_gen_current,
            current_unit='uA',
            offset=self._signal_gen_offset,
            offset_unit='mV',
            frequency=self._signal_gen_frequency,
            frequency_unit='Hz',
            shape='square',
            phase=self._signal_gen_phase
        )

        self._instrument.connect_signal_gen_to_tes(
            True,
            detector_channel=self._thermometer_tes_channel
        )

        time.sleep(5)

        # the fit needs the current the generator actually drives
        # through the TES line, which the controller derives from its
        # voltage and the line resistance
        sg_current = None
        sg_params = self._instrument.get_signal_gen_params(
            detector_channel=self._thermometer_tes_channel
        )
        if sg_params is not None and 'current' in sg_params:
            sg_current = sg_params['current']

        if sg_current is None or not np.isfinite(float(sg_current)):
            if self._signal_gen_current is not None:
                sg_current = self._signal_gen_current * 1.0e-6
                print('WARNING: Signal generator current could not be '
                      'read back, using the configured '
                      f'"signal_gen_current" ({sg_current:.6g} A)!')
            else:
                raise ValueError(
                    'GabSweep: unable to determine the signal '
                    'generator current amplitude (readback failed and '
                    'no "signal_gen_current" configured)!'
                )

        self._sg_current_amps_pp = float(sg_current)

        if self._verbose:
            print('INFO: Signal generator current amplitude = '
                  f'{self._sg_current_amps_pp * 1.0e6:.6g} uApp')

    def teardown_signal_generator(self):
        """
        Turn the signal generator off and disconnect it from the
        thermometer TES line. Errors are printed, not raised, so
        shutdown can continue.
        """

        if self._instrument is None:
            return

        try:
            self._instrument.set_signal_gen_onoff(
                'off',
                detector_channel=self._thermometer_tes_channel
            )
        except Exception as err:
            print(f'ERROR turning off the signal generator: {err}')

        try:
            self._instrument.connect_signal_gen_to_tes(
                False,
                detector_channel=self._thermometer_tes_channel
            )
        except Exception as err:
            print(f'ERROR disconnecting the signal generator: {err}')

    def _get_close_loop_norm(self):
        """
        Volts to amps close loop normalization of the thermometer TES
        readout, read from the instrument once and cached (the readout
        gains are not changed during the sweep).

        Returns
        -------
        norm : float
            Normalization such that current = volts / norm [Amps].
        """

        if self._close_loop_norm is None:
            self._close_loop_norm = float(
                self._instrument.get_volts_to_amps_close_loop_norm(
                    detector_channel=self._thermometer_tes_channel
                )
            )

        return self._close_loop_norm

    def _get_thermometer_bias_amps(self):
        """
        Thermometer TES bias current, read from the instrument once
        and cached (the script never changes it).

        Returns
        -------
        ibias : float
            Thermometer TES bias current [Amps].
        """

        if self._thermometer_bias_amps is None:
            bias_ua = float(self._instrument.get_tes_bias(
                detector_channel=self._thermometer_tes_channel,
                unit='uA'
            ))
            self._thermometer_bias_amps = bias_ua * 1.0e-6

        return self._thermometer_bias_amps

    def measure_mc_temperature(self):
        """
        Measure the MC temperature with its uncertainty.

        Returns
        -------
        measurement : dict
            Keys: temperature_k, temperature_err_k [Kelvin], fit_ok,
            nb_samples, samples (list of all readings [Kelvin]).
        """

        # keep the shared sweep's instrument current: self._instrument
        # can be reassigned after _instantiate_drivers() ran (as in
        # tests that inject a fake instrument directly)
        self._temperature_sweep.instrument = self._instrument

        return self._temperature_sweep.measure_temperature()

    def measure_r0_quality(self, nb_events=None):
        """
        Measure the thermometer TES bias point R0: read signal
        generator triggered dIdV traces, apply qetpy dIdV autocuts,
        fit the average with the 3-pole model, and extract R0 with
        the infinite loop gain approximation.

        Parameters
        ----------
        nb_events : int or None
            Number of traces to read. Defaults to nb_events_didv.

        Returns
        -------
        quality : dict
            Keys: r0, r0_err [Ohms], i0 [Amps], p0 [Watts],
            fit_cost, nb_traces, nb_traces_kept.
        """

        if self._sg_current_amps_pp is None:
            raise ValueError(
                'GabSweep: signal generator not set up, run '
                'setup_signal_generator() first!'
            )

        if nb_events is None:
            nb_events = self._nb_events_didv

        traces = self._daq.read_many_events(nb_events, adctovolt=True)

        # single readout channel: (nb_events, 1, nb_samples)
        traces = traces[:, 0, :]

        # volts to amps
        traces = traces / self._get_close_loop_norm()

        cut = qp.autocuts_didv(traces, fs=self._sample_rate)

        if np.sum(cut) == 0:
            print('WARNING: dIdV autocuts removed all traces, '
                  'using all traces instead!')
            cut = np.ones(traces.shape[0], dtype=bool)

        fit = fit_didv_r0(
            traces=traces[cut, :],
            sample_rate=self._sample_rate,
            sgfreq=self._signal_gen_frequency,
            sgamp=self._sg_current_amps_pp,
            rsh=self._rshunt,
            rp=self._rparasitic,
            ibias=self._get_thermometer_bias_amps(),
            r0_guess=self._r0_guess,
            fcutoff=self._didv_fcutoff
        )

        # a good fit seeds the next one
        if np.isfinite(fit['r0']) and fit['r0'] > 0:
            self._r0_guess = fit['r0']

        quality = {
            'r0': fit['r0'],
            'r0_err': fit['r0_err'],
            'i0': fit['i0'],
            'p0': fit['p0'],
            'fit_cost': fit['fit_cost'],
            'nb_traces': int(traces.shape[0]),
            'nb_traces_kept': int(np.sum(cut)),
        }

        return quality

    def measure_r0(self, nb_events=None):
        """
        Measure the thermometer TES bias point R0.

        Parameters
        ----------
        nb_events : int or None
            Number of traces to read. Defaults to nb_events_didv.

        Returns
        -------
        r0 : float
            Thermometer TES R0 [Ohms].
        """

        quality = self.measure_r0_quality(nb_events=nb_events)

        return quality['r0']

    def _set_heater_bias_min(self):
        """
        Set the heater TES bias to bias_min, its lowest normal state,
        and wait post_bias_wait for it to settle.

        The front end board supports a quantized set of bias currents
        and snaps any request to the nearest one, so the bias it lands
        on is read back and kept as the effective floor. Comparing
        against the requested bias_min instead would fail every time
        the request snapped downwards.
        """

        if self._verbose:
            print('INFO: Setting heater TES bias to bias_min_uA = '
                  f'{self._bias_min:.6g} uA')

        self._instrument.set_tes_bias(
            self._bias_min,
            unit='uA',
            detector_channel=self._heater_tes_channel
        )

        if self._post_bias_wait > 0:
            time.sleep(self._post_bias_wait)

        self._bias_min_actual = float(self._instrument.get_tes_bias(
            detector_channel=self._heater_tes_channel,
            unit='uA'
        ))

        if self._verbose:
            print('INFO: Heater TES bias read back at '
                  f'{self._bias_min_actual:.6g} uA, using it as the '
                  'effective bias floor')

    def _get_bias_floor(self):
        """
        Lowest heater TES bias the sweep may apply.

        Returns
        -------
        bias_floor : float
            The bias read back after setting bias_min [uA], or the
            requested bias_min if it has not been set yet.
        """

        if self._bias_min_actual is None:
            return self._bias_min

        return self._bias_min_actual

    def _print_r0_quality(self, quality=None, label=None):
        """
        Print one R0 measurement with its quality metrics.

        Parameters
        ----------
        quality : dict
            Output of measure_r0_quality.
        label : str
            Short label describing the measurement.
        """

        message = (f'INFO: {label}: R0 = '
                   f'{quality["r0"] * 1000.0:.6g} mOhms '
                   f'(err = {quality["r0_err"] * 1000.0:.3g} mOhms), '
                   f'{quality["nb_traces_kept"]}/{quality["nb_traces"]} '
                   'traces kept by autocuts')

        if self._r0_ref is not None and self._r0_ref != 0:
            offset = (quality['r0'] - self._r0_ref)
            offset = offset / abs(self._r0_ref) * 100.0
            message = message + (f', {offset:+.3g} percent from '
                                 'reference')

        print(message)

    def wait_for_temperature(self, temperature_mk=None):
        """
        Wait until the MC temperature reaches a setpoint and holds it.

        Parameters
        ----------
        temperature_mk : float
            MC temperature setpoint [mK].

        Returns
        -------
        temperature_ok : bool
            True if the setpoint was reached and held, False on
            timeout.
        history : list of float
            All temperature readings taken [mK].
        """

        # keep the shared sweep's instrument current: self._instrument
        # can be reassigned after _instantiate_drivers() ran (as in
        # tests that inject a fake instrument directly)
        self._temperature_sweep.instrument = self._instrument

        return self._temperature_sweep.wait_for_temperature(
            temperature_mk=temperature_mk
        )

    def wait_for_settled_r0(self):
        """
        Wait for the thermometer TES R0 to settle, by the method
        selected with use_stability_check.

        Returns
        -------
        settle_ok : bool
            True if R0 settled, False on a stability check timeout.
            Always True for the fixed timer.
        history : list of float
            Quick R0 measurements taken [Ohms], empty for the fixed
            timer.
        """

        if self._use_stability_check:
            return self.wait_for_stable_r0()

        if self._verbose:
            print(f'INFO: Waiting {self._settle_wait_time:.6g} s for '
                  'the thermometer TES R0 to settle')

        if self._settle_wait_time > 0:
            time.sleep(self._settle_wait_time)

        return True, list()

    def wait_for_stable_r0(self):
        """
        Wait until the last 5 quick R0 measurements agree within
        r0_tolerance_percent, or stability_timeout is reached.

        Returns
        -------
        stability_ok : bool
            True if stability was reached, False on timeout.
        history : list of float
            All quick R0 measurements taken [Ohms].
        """

        history = list()
        start_time = time.time()

        if self._verbose:
            print('INFO: Waiting for stable thermometer TES R0')

        while True:

            r0 = self.measure_r0(
                nb_events=self._nb_events_stability
            )
            history.append(r0)

            if len(history) >= 5:
                recent = history[-5:]
                reference = recent[-1]
                all_within = True
                if reference == 0:
                    # relative comparison is meaningless at zero,
                    # keep waiting for a nonzero stable R0
                    all_within = False
                else:
                    for value in recent:
                        offset = abs(value - reference) / abs(reference)
                        if offset * 100.0 > self._r0_tolerance_percent:
                            all_within = False
                if all_within:
                    return True, history

            if (time.time() - start_time) > self._stability_timeout:
                print('WARNING: R0 stability timeout '
                      f'({self._stability_timeout:.6g} s), continuing!')
                return False, history

            time.sleep(10)

    def run_drift_check(self):
        """
        Characterize the R0 drift: repeat the R0 measurement at fixed
        conditions, spaced drift_check_wait_time apart, and keep the
        scatter as the feedback noise floor. Warns when the scatter
        exceeds r0_tolerance_percent, since the feedback cannot
        reliably converge below the drift.

        Returns
        -------
        drift : dict or None
            Keys: r0_values, mean, scatter, scatter_percent. None
            when the check is disabled
            (drift_check_nb_measurements < 2).
        """

        if self._drift_check_nb_measurements < 2:
            if self._verbose:
                print('INFO: R0 drift check disabled '
                      '(drift_check_nb_measurements < 2)')
            return None

        if self._verbose:
            print('INFO: Characterizing R0 drift with '
                  f'{self._drift_check_nb_measurements} measurements, '
                  f'{self._drift_check_wait_time:.6g} s apart')

        r0_values = list()
        for index in range(self._drift_check_nb_measurements):

            if index > 0 and self._drift_check_wait_time > 0:
                time.sleep(self._drift_check_wait_time)

            quality = self.measure_r0_quality()
            r0_values.append(quality['r0'])

            if self._verbose:
                self._print_r0_quality(
                    quality=quality,
                    label=(f'Drift check {index + 1}/'
                           f'{self._drift_check_nb_measurements}')
                )

        mean = float(np.mean(r0_values))
        scatter = float(np.std(r0_values))
        self._r0_noise_floor = scatter

        scatter_percent = None
        if mean != 0:
            scatter_percent = scatter / abs(mean) * 100.0

        if self._verbose:
            message = ('INFO: R0 drift: scatter = '
                       f'{scatter * 1000.0:.6g} mOhms')
            if scatter_percent is not None:
                message = message + f' ({scatter_percent:.3g} percent)'
            print(message)

        if (scatter_percent is not None
                and scatter_percent > self._r0_tolerance_percent):
            print('WARNING: R0 drift '
                  f'({scatter_percent:.3g} percent) exceeds '
                  'r0_tolerance_percent '
                  f'({self._r0_tolerance_percent:.6g} percent), '
                  'the feedback cannot converge reliably! Consider a '
                  'longer settle, more events per measurement, or a '
                  'looser tolerance.')

        drift = {
            'r0_values': r0_values,
            'mean': mean,
            'scatter': scatter,
            'scatter_percent': scatter_percent,
        }
        self._diagnostics['drift_check'] = drift

        return drift

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
              f'(bias_min_uA, keeps the heater normal) to '
              f'{self._bias_max:.6g} uA (bias_max_uA)')
        print(f'MC thermometer: {self._thermometer_name} '
              f'({self._thermometer_instrument}), '
              f'heater: {self._heater_name}')

        amplitude = ''
        if self._signal_gen_current is not None:
            amplitude = f'{self._signal_gen_current:.6g} uApp'
        else:
            amplitude = f'{self._signal_gen_voltage:.6g} mVpp'
        print(f'\ndIdV square wave: {self._signal_gen_frequency:.6g} '
              f'Hz, {amplitude}, offset = '
              f'{self._signal_gen_offset:.6g} mV, phase = '
              f'{self._signal_gen_phase:.6g} deg')
        print(f'dIdV traces: {self._nb_events_didv} events of '
              f'{self._trace_length_ms_actual:.6g} ms '
              f'({self._nb_cycles} signal generator periods), fit '
              f'lowpass cutoff = {self._didv_fcutoff:.6g} Hz')
        print(f'TES circuit: rshunt = {self._rshunt * 1000.0:.6g} '
              f'mOhms, rparasitic = '
              f'{self._rparasitic * 1000.0:.6g} mOhms')

        nb_points = len(self._temperature_list_mk)
        print(f'\nTemperature setpoints [mK] ({nb_points} points):')
        for idx, temperature_mk in enumerate(self._temperature_list_mk):
            print(f'  Step {idx + 1:>{len(str(nb_points))}}/{nb_points}: '
                  f'{temperature_mk:.6g} mK')

        print(f'\nMC temperature sampling: '
              f'{self._temperature_sweep.sampling_time_s:.6g} s window '
              'per datapoint (Gaussian histogram fit for the '
              'uncertainty)')

        print(f'\nMC temperature settling: polled every '
              f'{self._temperature_sweep.poll_interval_s:.6g} s, must '
              f'hold within '
              f'{self._temperature_sweep.tolerance_frac * 100.0:.3g} '
              f'percent for '
              f'{self._temperature_sweep.stable_time_s:.6g} s, up to '
              f'{self._temperature_sweep.max_wait_time_s:.6g} s')

        if self._use_stability_check:
            settle_s = self._stability_timeout / 3.0
            print(f'\nR0 settling: stability check, up to '
                  f'{self._stability_timeout:.6g} s per measurement')
        else:
            settle_s = self._settle_wait_time
            print(f'\nR0 settling: fixed timer, '
                  f'{self._settle_wait_time:.6g} s per measurement')

        # rough duration estimate: temperature settling plus a few
        # feedback iterations per point. How long the fridge takes to
        # reach a setpoint is not knowable in advance, so this assumes
        # the hold time alone and will underestimate large steps.
        per_point_s = (self._temperature_sweep.stable_time_s
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
                      f'will be set to bias_min_uA = {self._bias_min:.6g} '
                      'uA (must keep it normal) and set back to its '
                      'original value at shutdown.')

            # dIdV square wave on the thermometer TES, on for the
            # whole sweep so every R0 measurement is taken under the
            # same conditions; turned off at shutdown
            self.setup_signal_generator()

            # the heater TES goes to its lowest normal state before
            # any R0 is measured, so the startup check is taken with
            # the same heater state as every sweep datapoint and
            # cannot bias them
            self._set_heater_bias_min()

            # sanity check the thermometer TES readout and the dIdV
            # fit before committing to the sweep
            startup_quality = self.measure_r0_quality()
            self._diagnostics['startup_r0'] = startup_quality
            self._print_r0_quality(
                quality=startup_quality,
                label='Startup check'
            )

            # measure the R0 repeatability the feedback is up
            # against; also sets the noise floor for the bias probing
            self.run_drift_check()

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
        Safe shutdown: signal generator off and disconnected, MC
        heater setpoint to 0, heater TES bias restored to its pre-run
        value (left untouched if unknown), diagnostics flushed. The
        thermometer TES bias is never touched.
        """

        print('INFO: Safe shutdown, turning off the signal generator, '
              'setting heater setpoint to 0 and restoring the heater '
              'TES bias')

        self.teardown_signal_generator()

        if self._instrument is not None:

            try:
                # keep the shared sweep's instrument current:
                # self._instrument can be reassigned after
                # _instantiate_drivers() ran (as in tests that inject
                # a fake instrument directly)
                self._temperature_sweep.instrument = self._instrument
                self._temperature_sweep.heater_to_zero()
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
                          'original pre-run value of '
                          f'{self._heater_initial_bias_ua:.6g} uA')
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

    def _run_feedback(self, initial_r0=None):
        """
        Adjust the heater TES bias (between bias_min and bias_max)
        until the thermometer TES R0 returns to the reference.
        Convergence requires two consecutive readings at an unchanged
        bias: both in tolerance, or a near miss on the second (within
        2x tolerance) whose mean with the first is in tolerance. A
        single lucky reading in a drifting environment is not
        accepted, but a hair's-width confirmation miss does not
        restart the feedback either.

        Parameters
        ----------
        initial_r0 : float or None
            Settled R0 already measured at the current bias [Ohms].
            Measured here if None.

        Returns
        -------
        result : dict
            Keys: bias_history, r0_history, converged, cap_reached,
            pinned_at_floor, stability_ok.
        """

        if self._r0_ref is None:
            raise ValueError(
                'GabSweep: reference R0 not set, '
                'run the first sweep step first!'
            )

        current_bias = float(self._instrument.get_tes_bias(
            detector_channel=self._heater_tes_channel,
            unit='uA'
        ))

        if current_bias < self._get_bias_floor():
            print(f'WARNING: Heater TES bias ({current_bias:.6g} uA) '
                  'below the bias floor '
                  f'({self._get_bias_floor():.6g} uA), raising it to '
                  'keep the heater TES normal!')
            self._set_heater_bias_min()
            current_bias = self._get_bias_floor()
            initial_r0 = None

        if initial_r0 is None:
            initial_r0 = self.measure_r0()

        bias_history = [current_bias]
        r0_history = [float(initial_r0)]
        stability_ok = True
        cap_reached = False
        pinned_at_floor = False

        # bias comparisons against the floor tolerate readback jitter
        floor_epsilon_ua = 1.0e-3

        def offset_from_ref_percent(r0):
            if self._r0_ref == 0:
                # relative comparison is meaningless at zero
                return None
            offset = abs(r0 - self._r0_ref)
            offset = offset / abs(self._r0_ref)
            return offset * 100.0

        def is_converged(r0):
            offset = offset_from_ref_percent(r0)
            if offset is None:
                return False
            return offset <= self._r0_tolerance_percent

        def print_reading(applied_bias, r0, label):
            message = (f'INFO: {label}: bias = {applied_bias:.6g} uA, '
                       f'R0 = {r0 * 1000.0:.6g} mOhms')
            if self._r0_ref == 0:
                message = message + (', reference is 0, offset '
                                     'undefined')
            else:
                offset = (r0 - self._r0_ref)
                offset = offset / abs(self._r0_ref) * 100.0
                message = message + (
                    f', reference = {self._r0_ref * 1000.0:.6g} '
                    f'mOhms, offset = {offset:+.3g} percent'
                )
            print(message)

        converged = False
        start_time = time.time()

        while not converged and not cap_reached and not pinned_at_floor:

            if (time.time() - start_time) > self._feedback_timeout:
                print('WARNING: Feedback timeout '
                      f'({self._feedback_timeout:.6g} s), '
                      'recording point as not converged!')
                break

            if is_converged(r0_history[-1]):

                # in-tolerance reading: confirm it with a second
                # reading at the same bias before accepting it
                step_settled, _ = self.wait_for_settled_r0()
                if not step_settled:
                    stability_ok = False

                previous_r0 = r0_history[-1]
                r0 = self.measure_r0()
                bias_history.append(bias_history[-1])
                r0_history.append(r0)

                label = None
                if is_converged(r0):
                    converged = True
                    label = 'Confirmation reading, converged'
                else:
                    # drift can push a single confirmation reading
                    # just outside tolerance; the mean of the two
                    # readings is the better estimate, accept it when
                    # the confirmation reading itself is not too far
                    # out (within 2x tolerance)
                    confirmation_offset = offset_from_ref_percent(r0)
                    mean_r0 = (previous_r0 + r0) / 2.0
                    mean_offset = offset_from_ref_percent(mean_r0)
                    tolerance = self._r0_tolerance_percent
                    if (confirmation_offset is not None
                            and confirmation_offset <= (2.0 * tolerance)
                            and mean_offset <= tolerance):
                        converged = True
                        label = ('Confirmation near miss, converged '
                                 'on the mean of both readings')
                    else:
                        label = ('Confirmation reading failed, '
                                 'continuing feedback')

                if self._verbose:
                    print_reading(bias_history[-1], r0, label)

                continue

            next_bias = compute_next_bias(
                bias_history=bias_history,
                r0_history=r0_history,
                r0_ref=self._r0_ref,
                bias_step_start=self._bias_step_start,
                bias_min=self._get_bias_floor(),
                noise_floor=self._r0_noise_floor
            )

            if (next_bias <= (self._get_bias_floor() + floor_epsilon_ua)
                    and bias_history[-1] <= (self._get_bias_floor()
                                             + floor_epsilon_ua)):
                # the feedback wants a bias below the floor while
                # already sitting at it: the reference cannot be
                # reached (the heater cannot remove power), most
                # likely a drift artifact; flag it instead of looping
                pinned_at_floor = True
                print('WARNING: Feedback pinned at the bias floor '
                      f'({self._get_bias_floor():.6g} uA), the '
                      'reference R0 cannot be reached from '
                      'here, recording point as not converged!')
                break

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

            step_settled, _ = self.wait_for_settled_r0()
            if not step_settled:
                stability_ok = False

            # the front end board snaps next_bias to the nearest bias
            # current it supports, and R0 responds to the bias it
            # actually applied, so the slope update must be fed the
            # read back value: pairing a requested bias with a
            # measured R0 would skew the slope
            applied_bias = float(self._instrument.get_tes_bias(
                detector_channel=self._heater_tes_channel,
                unit='uA'
            ))

            r0 = self.measure_r0()
            bias_history.append(applied_bias)
            r0_history.append(r0)

            if self._verbose:
                print_reading(
                    applied_bias,
                    r0,
                    f'Feedback (requested {next_bias:.6g} uA)'
                )

        result = {
            'bias_history': bias_history,
            'r0_history': r0_history,
            'converged': converged,
            'cap_reached': cap_reached,
            'pinned_at_floor': pinned_at_floor,
            'stability_ok': stability_ok,
        }

        return result

    def run_single_step(self, temperature_mk=None, step_index=None):
        """
        Run one full temperature point of the Gab sweep: set the MC
        temperature, run the heater TES feedback (or measure the
        reference R0 on the first point), record the datapoint.

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

        # keep the shared sweep's instrument current: self._instrument
        # can be reassigned after _instantiate_drivers() ran (as in
        # tests that inject a fake instrument directly)
        self._temperature_sweep.instrument = self._instrument

        # the setpoint is only applied here; the driver's own wait is
        # not used because it cannot report whether it reached the
        # setpoint or simply ran out of time
        self._temperature_sweep.set_setpoint(temperature_mk=temperature_mk)

        temperature_ok, temperature_history = self.wait_for_temperature(
            temperature_mk=temperature_mk
        )

        end_sweep = False
        step_diagnostics = {'step': step_index,
                            'temperature_setpoint_mk': temperature_mk,
                            'temperature_ok': temperature_ok,
                            'temperature_history': temperature_history}

        if step_index == 0:

            # re-assert the lowest normal state: run() already did this
            # before the startup check, but the step must not depend on
            # that when it is driven directly from a notebook
            self._set_heater_bias_min()

        # settled R0 at this temperature, before any feedback: on
        # later steps its offset from the reference is the bias point
        # shift the feedback has to undo
        stability_ok, stability_history = (
            self.wait_for_settled_r0()
        )
        settled_quality = self.measure_r0_quality()
        step_diagnostics['stability_history'] = stability_history
        step_diagnostics['settled_quality'] = settled_quality

        if self._verbose:
            self._print_r0_quality(
                quality=settled_quality,
                label=f'Step {step_index} settled'
            )

        if step_index == 0:

            r0 = settled_quality['r0']
            r0_err = settled_quality['r0_err']
            self._r0_ref = r0
            converged = True
            pinned_at_floor = False
            bias_history = list()
            r0_history = [r0]

            if self._verbose:
                print(f'INFO: Reference R0: {r0 * 1000.0:.6g} mOhms')

        else:

            result = self._run_feedback(
                initial_r0=settled_quality['r0']
            )
            converged = result['converged']
            pinned_at_floor = result['pinned_at_floor']
            if not result['stability_ok']:
                stability_ok = False
            end_sweep = result['cap_reached']
            bias_history = result['bias_history']
            r0_history = result['r0_history']

            # feedback drives with the R0 value alone; the recorded R0
            # and its error must come from one measurement, so take a
            # final quality measurement at the converged bias (the bias
            # is unchanged, so R0 is already settled)
            final_quality = self.measure_r0_quality()
            r0 = final_quality['r0']
            r0_err = final_quality['r0_err']
            step_diagnostics['final_quality'] = final_quality

        # read back the final state; the MC temperature is sampled
        # over a window and Gaussian fit for its uncertainty
        heater_bias_ua = float(self._instrument.get_tes_bias(
            detector_channel=self._heater_tes_channel,
            unit='uA'
        ))
        temperature_measurement = self.measure_mc_temperature()
        mc_temperature_mk = (
            temperature_measurement['temperature_k'] * 1000.0
        )
        mc_temperature_err_mk = (
            temperature_measurement['temperature_err_k'] * 1000.0
        )
        step_diagnostics['temperature_measurement'] = (
            temperature_measurement
        )

        # propagate the R0 fractional uncertainty to the heater TES
        # bias point (a colder bath needs more heater power to hold R0,
        # so an R0 uncertainty maps to a bias uncertainty)
        heater_bias_err_ua = propagate_r0_error_to_bias(
            r0=r0,
            r0_err=r0_err,
            heater_bias=heater_bias_ua
        )

        offset_percent = 0.0
        if self._r0_ref is not None and self._r0_ref != 0:
            offset_percent = (r0 - self._r0_ref)
            offset_percent = (offset_percent
                              / abs(self._r0_ref) * 100.0)

        row_dict = {
            'step': step_index,
            'timestamp': datetime.now().isoformat(),
            'temperature_setpoint_mk': temperature_mk,
            'mc_temperature_mk': mc_temperature_mk,
            'mc_temperature_err_mk': mc_temperature_err_mk,
            'heater_tes_bias_ua': heater_bias_ua,
            'heater_tes_bias_err_ua': heater_bias_err_ua,
            'thermometer_r0_ohms': r0,
            'thermometer_r0_err_ohms': r0_err,
            'r0_offset_percent': offset_percent,
            'converged': converged,
            'pinned_at_floor': pinned_at_floor,
            'stability_ok': stability_ok,
            'temperature_ok': temperature_ok,
        }
        self._append_datapoint(row_dict=row_dict)

        step_diagnostics['bias_history'] = bias_history
        step_diagnostics['r0_history'] = r0_history
        step_diagnostics['row'] = row_dict
        self._diagnostics['steps'].append(step_diagnostics)

        if self._verbose:
            print(f'INFO: Step {step_index} recorded: MC = '
                  f'{mc_temperature_mk:.6g} '
                  f'+- {mc_temperature_err_mk:.3g} mK '
                  f'({temperature_measurement["nb_samples"]} samples), '
                  f'heater TES bias = {heater_bias_ua:.6g} '
                  f'+- {heater_bias_err_ua:.3g} uA, '
                  f'R0 = {r0 * 1000.0:.6g} '
                  f'+- {r0_err * 1000.0:.3g} mOhms '
                  f'({offset_percent:+.3g} percent from reference), '
                  f'converged = {converged}, '
                  f'pinned_at_floor = {pinned_at_floor}, '
                  f'stability_ok = {stability_ok}, '
                  f'temperature_ok = {temperature_ok}')

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
