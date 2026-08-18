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
# build_temperature_list and fit_temperature_gaussian are not used in
# this module any more, they moved to temperature_sweep. They stay
# imported so that notebooks and scripts still doing
# "from pytesdaq.sequencer.gab_sweep import build_temperature_list"
# keep working
from pytesdaq.sequencer.temperature_sweep import (  # noqa: F401
    TemperatureSweep,
    build_temperature_list,
    config_get,
    config_has,
    fit_temperature_gaussian,
)
from pytesdaq.utils import arg_utils
from pytesdaq.utils import connection_utils


# two heater bias points closer together than this are the same point
BIAS_TOLERANCE_UA = 1.0e-6


def build_bias_list(config_dict=None):
    """
    Build the heater TES bias sweep vector in uA from the config,
    using "bias_vect_uA" or bias_min/bias_max/bias_step.

    The vector is returned in sweep order, which is descending, the
    same convention as build_tes_bias_vect in iv_didv. An explicit
    vector may be typed in either order and is sorted descending
    regardless, because its entries are a set of bias points rather
    than a sequence.

    Parameters
    ----------
    config_dict : dict
        Measurement configuration dictionary.

    Returns
    -------
    bias_list : list of float
        Heater TES bias points in sweep order [uA], starting at
        bias_max_uA and ending at bias_min_uA.
    """

    required_keys = ['bias_min_uA', 'bias_max_uA']
    for key in required_keys:
        if not config_has(config_dict, key):
            raise ValueError(f'GabSweep: "{key}" required in config!')

    bias_min = float(config_get(config_dict, 'bias_min_uA'))
    bias_max = float(config_get(config_dict, 'bias_max_uA'))

    if bias_min >= bias_max:
        raise ValueError(
            'GabSweep: "bias_min_uA" must be less than "bias_max_uA"!'
        )

    use_vect = False
    if config_has(config_dict, 'use_bias_vect'):
        use_vect = bool(config_get(config_dict, 'use_bias_vect'))

    bias_list = list()

    if use_vect:

        if not config_has(config_dict, 'bias_vect_uA'):
            raise ValueError(
                'GabSweep: "bias_vect_uA" required when '
                '"use_bias_vect" is true!'
            )

        vect = config_get(config_dict, 'bias_vect_uA')
        if not isinstance(vect, (list, tuple)):
            vect = [vect]
        for value in vect:
            bias_list.append(float(value))

    else:

        if not config_has(config_dict, 'bias_step_uA'):
            raise ValueError(
                'GabSweep: "bias_step_uA" required when '
                '"use_bias_vect" is false!'
            )

        step = abs(float(config_get(config_dict, 'bias_step_uA')))
        if step == 0:
            raise ValueError(
                'GabSweep: "bias_step_uA" must be nonzero!'
            )

        for value in np.arange(bias_min, bias_max, step):
            bias_list.append(float(value))
        bias_list.append(bias_max)

    if len(bias_list) == 0:
        raise ValueError('GabSweep: empty heater bias list!')

    # descending sweep order
    bias_list.sort(reverse=True)

    # a float arange can land a hair below bias_max, which would
    # survive next to the appended bias_max under exact comparison
    deduped = [bias_list[0]]
    for value in bias_list[1:]:
        if (deduped[-1] - value) > BIAS_TOLERANCE_UA:
            deduped.append(value)
        elif use_vect:
            raise ValueError(
                'GabSweep: "bias_vect_uA" contains duplicate bias '
                f'points near {value:.6g} uA!'
            )
    bias_list = deduped

    for value in bias_list:
        if (value < (bias_min - BIAS_TOLERANCE_UA)
                or value > (bias_max + BIAS_TOLERANCE_UA)):
            raise ValueError(
                f'GabSweep: heater bias point {value:.6g} uA is '
                f'outside ["bias_min_uA" = {bias_min:.6g}, '
                f'"bias_max_uA" = {bias_max:.6g}] uA!'
            )

    # the endpoints are enforced rather than inserted: bias_min_uA is
    # where the heater sits for minutes while the MC settles, so a
    # vector that never measures there would leave the state the
    # thermometer spends the most time in unrecorded
    if abs(bias_list[0] - bias_max) > BIAS_TOLERANCE_UA:
        raise ValueError(
            'GabSweep: the heater bias list must start at '
            f'"bias_max_uA" = {bias_max:.6g} uA, it starts at '
            f'{bias_list[0]:.6g} uA!'
        )
    if abs(bias_list[-1] - bias_min) > BIAS_TOLERANCE_UA:
        raise ValueError(
            'GabSweep: the heater bias list must end at '
            f'"bias_min_uA" = {bias_min:.6g} uA, it ends at '
            f'{bias_list[-1]:.6g} uA!'
        )

    return bias_list


def heater_power_watts(bias_ua=None, rshunt=None,
                       rparasitic=None, rnormal=None):
    """
    Joule power dissipated in the heater TES, held normal.

    The bias current divides between the shunt and the TES branch,
    so the current through the TES is
    I_tes = I_bias * Rsh / (Rsh + Rp + Rn), and the power it
    dissipates is I_tes squared times Rn.

    Parameters
    ----------
    bias_ua : float
        Heater TES bias current [uA].
    rshunt : float
        Heater shunt resistance [Ohms].
    rparasitic : float
        Heater parasitic resistance [Ohms].
    rnormal : float
        Heater TES normal resistance [Ohms].

    Returns
    -------
    power : float
        Power dissipated in the heater TES [Watts].
    """

    bias_amps = float(bias_ua) * 1.0e-6
    rload = float(rshunt) + float(rparasitic)
    tes_current = bias_amps * float(rshunt) / (rload + float(rnormal))

    return (tes_current ** 2) * float(rnormal)


def fit_didv_r0(traces=None, sample_rate=None,
                sgfreq=None, sgamp=None,
                rsh=None, rp=None, ibias=None,
                guess_params=None, fcutoff=50000.0):
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
    guess_params : tuple or None
        Starting parameters (A, B, C, tau1, tau2, tau3, dt) for the
        3-pole fit, normally the result of the last good fit at this
        bias point. None lets qetpy guess them from sgamp and rsh.
    fcutoff : float
        Lowpass cutoff frequency for the fit [Hz].

    Returns
    -------
    result : dict
        Keys: r0, r0_err, i0, p0 [SI units], fit_cost, fit_params,
        fit_params_tuple, cov.
    """

    didv = qp.DIDV(
        traces,
        sample_rate,
        sgfreq,
        sgamp,
        rsh,
        rp=rp,
    )

    didv.dofit(poles=3, fcutoff=fcutoff, guess_params=guess_params)
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

    # the parameter tuple in the order qetpy's dofit expects it back,
    # so a good fit at one bias point can seed the same point at the
    # next temperature
    fit_params_tuple = None
    param_order = ['A', 'B', 'C', 'tau1', 'tau2', 'tau3', 'dt']
    if all(name in fit['params'] for name in param_order):
        fit_params_tuple = tuple(
            float(fit['params'][name]) for name in param_order
        )

    result = {
        'r0': float(biasparams['r0']),
        'r0_err': r0_err,
        'i0': float(biasparams['i0']),
        'p0': float(biasparams['p0']),
        'fit_cost': float(fit['cost']),
        'fit_params': copy.deepcopy(fit['params']),
        'fit_params_tuple': fit_params_tuple,
        'cov': cov.tolist(),
    }

    return result


class GabSweep(Sequencer):

    # columns of the science dataset CSV, one row per (temperature,
    # heater bias) point
    CSV_COLUMNS = ['step', 'bias_index', 'timestamp',
                   'temperature_setpoint_mk',
                   'mc_temperature_mk', 'mc_temperature_err_mk',
                   'heater_tes_bias_requested_ua',
                   'heater_tes_bias_ua', 'heater_tes_power_w',
                   'thermometer_tes_bias_ua',
                   'thermometer_r0_ohms', 'thermometer_r0_err_ohms',
                   'thermometer_i0_amps', 'thermometer_p0_watts',
                   'didv_fit_cost', 'didv_fit_ok', 'autocuts_ok',
                   'nb_traces', 'nb_traces_kept',
                   'stability_ok', 'temperature_ok']

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
        self._heater_initial_bias_ua = None
        self._thermometer_initial_bias_ua = None
        self._sg_current_amps_pp = None
        self._close_loop_norm = None
        self._thermometer_bias_amps = None
        # one dIdV fit seed per heater bias point, carried across
        # temperatures so point k seeds point k at the next one
        self._guess_params = list()
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

        # only the settle agreement criterion: there is no target R0
        # anywhere in this sweep for a tolerance to be measured against
        self._r0_stability_tolerance_percent = float(
            require('r0_stability_tolerance_percent')
        )

        # TES circuit resistances for both channels, in mOhms in the
        # config and Ohms internally. The thermometer shunt and
        # parasitic feed the dIdV fit; the heater triplet turns its
        # bias current into a Joule power. The thermometer normal
        # resistance is recorded and used by the transition check.
        self._thermometer_rshunt = (
            float(require('thermometer_rshunt_mOhm')) / 1000.0
        )
        self._thermometer_rparasitic = (
            float(require('thermometer_rparasitic_mOhm')) / 1000.0
        )
        self._thermometer_rn = (
            float(require('thermometer_rn_mOhm')) / 1000.0
        )
        self._heater_rshunt = (
            float(require('heater_rshunt_mOhm')) / 1000.0
        )
        self._heater_rparasitic = (
            float(require('heater_rparasitic_mOhm')) / 1000.0
        )
        self._heater_rn = float(require('heater_rn_mOhm')) / 1000.0

        positive_resistances = [
            ('thermometer_rshunt_mOhm', self._thermometer_rshunt),
            ('thermometer_rn_mOhm', self._thermometer_rn),
            ('heater_rshunt_mOhm', self._heater_rshunt),
            ('heater_rn_mOhm', self._heater_rn),
        ]
        for key, value in positive_resistances:
            if value <= 0:
                raise ValueError(
                    f'GabSweep: "{key}" must be positive!'
                )

        non_negative_resistances = [
            ('thermometer_rparasitic_mOhm', self._thermometer_rparasitic),
            ('heater_rparasitic_mOhm', self._heater_rparasitic),
        ]
        for key, value in non_negative_resistances:
            if value < 0:
                raise ValueError(
                    f'GabSweep: "{key}" must not be negative!'
                )

        # thermometer TES relock, run with the heater at bias_max_uA
        self._relock_bias_ua = float(require('relock_bias_uA'))
        if self._relock_bias_ua <= 0:
            raise ValueError(
                'GabSweep: "relock_bias_uA" must be positive!'
            )

        self._relock_nb_cycles = 2
        if config_has(config_dict, 'relock_nb_cycles'):
            self._relock_nb_cycles = int(
                float(config_get(config_dict, 'relock_nb_cycles'))
            )

        self._relock_max_attempts = 3
        if config_has(config_dict, 'relock_max_attempts'):
            self._relock_max_attempts = int(
                float(config_get(config_dict, 'relock_max_attempts'))
            )

        if self._relock_nb_cycles < 1:
            raise ValueError(
                'GabSweep: "relock_nb_cycles" must be at least 1!'
            )
        if self._relock_max_attempts < 1:
            raise ValueError(
                'GabSweep: "relock_max_attempts" must be at least 1!'
            )

        # what counts as back in transition, as a fraction of the
        # thermometer normal resistance. This is a readout health
        # check on the lock, not an operating point: it never selects
        # a bias and never enters the science dataset
        self._transition_check_frac_rn_min = float(
            require('transition_check_frac_rn_min')
        )
        self._transition_check_frac_rn_max = float(
            require('transition_check_frac_rn_max')
        )

        if not (0.0 < self._transition_check_frac_rn_min
                < self._transition_check_frac_rn_max < 1.0):
            raise ValueError(
                'GabSweep: "transition_check_frac_rn_min" and '
                '"transition_check_frac_rn_max" must satisfy '
                '0 < min < max < 1!'
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

        # heater TES bias sweep
        self._bias_min = float(require('bias_min_uA'))
        self._bias_max = float(require('bias_max_uA'))
        self._post_bias_wait = float(require('post_bias_wait_s'))

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

        # the heater bias points, in sweep order (descending), and one
        # dIdV fit seed per point carried across temperatures
        self._bias_list = build_bias_list(config_dict=config_dict)
        self._guess_params = [None] * len(self._bias_list)

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

    @property
    def _thermometer_name(self):
        """
        Name of the MC thermometer channel.

        Read through to the shared temperature sweep rather than
        copied, so the two cannot drift apart.

        Parameters
        ----------
        None

        Returns
        -------
        thermometer_name : str
            The configured thermometer channel name.
        """
        return self._temperature_sweep.thermometer_name

    @property
    def _thermometer_instrument(self):
        """
        Name of the instrument the MC thermometer is read through.

        Parameters
        ----------
        None

        Returns
        -------
        thermometer_instrument : str
            The configured thermometer instrument name.
        """
        return self._temperature_sweep.thermometer_instrument

    @property
    def _heater_name(self):
        """
        Name of the MC heater channel.

        Parameters
        ----------
        None

        Returns
        -------
        heater_name : str
            The configured heater channel name.
        """
        return self._temperature_sweep.heater_name

    @property
    def _temperature_list_mk(self):
        """
        MC temperature setpoints for the sweep.

        Parameters
        ----------
        None

        Returns
        -------
        temperature_list_mk : list of float
            Strictly decreasing setpoints [mK].
        """
        return self._temperature_sweep.temperature_list_mk

    def _synced_temperature_sweep(self):
        """
        The shared temperature sweep, with its instrument and verbose
        flag refreshed from this object.

        Both can be reassigned after the drivers are instantiated, so
        they are refreshed before every use rather than captured once.

        Parameters
        ----------
        None

        Returns
        -------
        temperature_sweep : TemperatureSweep
            The shared temperature sweep, ready to use.
        """

        self._temperature_sweep.instrument = self._instrument
        self._temperature_sweep.verbose = self._verbose

        return self._temperature_sweep

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

    def relock_thermometer(self):
        """
        Relock the thermometer SQUID through a hard normal bias.

        Drives the thermometer TES well above its critical current so
        the SQUID has a well behaved state to lock against, relocks,
        returns the bias to the value captured at preflight, and
        relocks again. The second relock is what lands the lock with
        the thermometer back in its transition; the first only gives
        it a clean starting point.

        The applied bias is read back afterwards and the cached value
        refreshed, because the front end board snaps the request to
        the nearest bias it supports and that value is the ibias every
        R0 is derived from.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        if self._thermometer_initial_bias_ua is None:
            raise ValueError(
                'GabSweep: the pre-run thermometer TES bias is '
                'unknown, so the relock cannot put it back! Run the '
                'preflight first.'
            )

        if self._verbose:
            print('INFO: Relocking the thermometer through '
                  f'{self._relock_bias_ua:.6g} uA, back to '
                  f'{self._thermometer_initial_bias_ua:.6g} uA')

        relock_sequence = [
            self._relock_bias_ua,
            self._thermometer_initial_bias_ua,
        ]

        for bias_ua in relock_sequence:

            success = self._instrument.set_tes_bias(
                bias=bias_ua,
                unit='uA',
                detector_channel=self._thermometer_tes_channel
            )

            if not success:
                print('ERROR: the instrument refused to set the '
                      f'thermometer TES bias to {bias_ua:.6g} uA '
                      'during the relock!')

            if self._post_bias_wait > 0:
                time.sleep(self._post_bias_wait)

            self._instrument.relock(
                detector_channel=self._thermometer_tes_channel,
                num_relock=self._relock_nb_cycles
            )

        # the board quantizes, so re-read rather than assuming the
        # bias came back to exactly the requested value
        self._thermometer_bias_amps = None
        self._get_thermometer_bias_amps()

    def check_thermometer_in_transition(self):
        """
        Check that the thermometer came back locked in its transition.

        A readout health check, not a measurement: it decides only
        whether the relock worked. R0 is required to be a usable fit
        and to sit between transition_check_frac_rn_min and
        transition_check_frac_rn_max of the thermometer normal
        resistance.

        Parameters
        ----------
        None

        Returns
        -------
        in_transition : bool
            True when the thermometer is usably in its transition.
        quality : dict
            The R0 measurement the decision was taken on.
        """

        quality = self.measure_r0_quality()

        if not quality['didv_fit_ok']:
            return False, quality

        fraction = quality['r0'] / self._thermometer_rn

        in_transition = (
            self._transition_check_frac_rn_min
            < fraction
            < self._transition_check_frac_rn_max
        )

        if self._verbose:
            print(f'INFO: Transition check: R0 = '
                  f'{quality["r0"] * 1000.0:.6g} mOhms, '
                  f'{fraction * 100.0:.3g} percent of Rn, '
                  f'in transition = {in_transition}')

        return in_transition, quality

    def relock_and_verify(self):
        """
        Relock the thermometer until it verifies back in transition.

        Repeats relock_thermometer and the transition check up to
        relock_max_attempts times. Exhausting the attempts warns
        loudly and returns rather than raising, so that one bad
        temperature does not throw away every colder one; the failure
        is recorded in the diagnostics for offline analysis to drop.

        Parameters
        ----------
        None

        Returns
        -------
        result : dict
            Keys: relock_ok, nb_attempts, r0.
        """

        in_transition = False
        quality = None
        attempt = 0

        while (not in_transition
               and attempt < self._relock_max_attempts):

            attempt = attempt + 1
            self.relock_thermometer()
            in_transition, quality = (
                self.check_thermometer_in_transition()
            )

        if not in_transition:
            print('WARNING: the thermometer TES did not verify back '
                  f'in transition after {attempt} relock attempts! '
                  'This temperature is recorded but its R0 values '
                  'cannot be trusted. Check that the thermometer is '
                  'still biased in transition and that the heater '
                  'TES has not gone superconducting.')

        r0 = float('nan')
        if quality is not None:
            r0 = quality['r0']

        result = {
            'relock_ok': in_transition,
            'nb_attempts': attempt,
            'r0': r0,
        }

        return result

    def measure_mc_temperature(self):
        """
        Measure the MC temperature with its uncertainty.

        Returns
        -------
        measurement : dict
            Keys: temperature_k, temperature_err_k [Kelvin], fit_ok,
            nb_samples, samples (list of all readings [Kelvin]).
        """

        return self._synced_temperature_sweep().measure_temperature()

    def measure_r0_quality(self, nb_events=None, bias_index=None):
        """
        Measure the thermometer TES bias point R0: read signal
        generator triggered dIdV traces, apply qetpy dIdV autocuts,
        fit the average with the 3-pole model, and extract R0 with
        the infinite loop gain approximation.

        A failed fit is normal at the ends of the heater bias vector,
        where the thermometer is fully normal or fully
        superconducting. It is recorded with didv_fit_ok False and NaN
        R0 rather than raised.

        Parameters
        ----------
        nb_events : int or None
            Number of traces to read. Defaults to nb_events_didv.
        bias_index : int or None
            Position in the heater bias vector, used to pick and
            update the per bias point dIdV fit seed. None skips the
            seeding entirely.

        Returns
        -------
        quality : dict
            Keys: r0, r0_err [Ohms], i0 [Amps], p0 [Watts],
            fit_cost, fit_params, cov, nb_traces, nb_traces_kept,
            autocuts_ok, didv_fit_ok.
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

        autocuts_ok = True
        if np.sum(cut) == 0:
            # every trace rejected: fall back to all of them, but say
            # so, because the kept count alone cannot distinguish this
            # from autocuts having kept everything
            autocuts_ok = False
            print('WARNING: dIdV autocuts removed all traces, '
                  'using all traces instead!')
            cut = np.ones(traces.shape[0], dtype=bool)

        guess_params = None
        if (bias_index is not None
                and bias_index < len(self._guess_params)):
            guess_params = self._guess_params[bias_index]

        fit = None
        didv_fit_ok = True

        try:
            fit = fit_didv_r0(
                traces=traces[cut, :],
                sample_rate=self._sample_rate,
                sgfreq=self._signal_gen_frequency,
                sgamp=self._sg_current_amps_pp,
                rsh=self._thermometer_rshunt,
                rp=self._thermometer_rparasitic,
                ibias=self._get_thermometer_bias_amps(),
                guess_params=guess_params,
                fcutoff=self._didv_fcutoff
            )
        except Exception as err:
            # at the ends of the bias vector the thermometer is fully
            # normal or fully superconducting and the 3-pole fit has
            # nothing to fit. That is expected data, not a run ending
            # error, so it is recorded and the sweep continues
            didv_fit_ok = False
            print('WARNING: dIdV fit failed at bias index '
                  f'{bias_index}: {err}')

        if fit is not None and not (np.isfinite(fit['r0'])
                                    and fit['r0'] > 0):
            didv_fit_ok = False

        if not didv_fit_ok:
            quality = {
                'r0': float('nan'),
                'r0_err': float('nan'),
                'i0': float('nan'),
                'p0': float('nan'),
                'fit_cost': float('nan'),
                'fit_params': None,
                'cov': None,
                'nb_traces': int(traces.shape[0]),
                'nb_traces_kept': int(np.sum(cut)),
                'autocuts_ok': autocuts_ok,
                'didv_fit_ok': False,
            }
            return quality

        # a good fit seeds the next sweep at this same bias point
        if (bias_index is not None
                and bias_index < len(self._guess_params)
                and fit['fit_params_tuple'] is not None):
            self._guess_params[bias_index] = fit['fit_params_tuple']

        quality = {
            'r0': fit['r0'],
            'r0_err': fit['r0_err'],
            'i0': fit['i0'],
            'p0': fit['p0'],
            'fit_cost': fit['fit_cost'],
            'fit_params': fit['fit_params'],
            'cov': fit['cov'],
            'nb_traces': int(traces.shape[0]),
            'nb_traces_kept': int(np.sum(cut)),
            'autocuts_ok': autocuts_ok,
            'didv_fit_ok': True,
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

        if not quality['didv_fit_ok']:
            print(f'INFO: {label}: no usable dIdV fit')
            return

        print(f'INFO: {label}: R0 = '
              f'{quality["r0"] * 1000.0:.6g} mOhms '
              f'(err = {quality["r0_err"] * 1000.0:.3g} mOhms), '
              f'{quality["nb_traces_kept"]}/{quality["nb_traces"]} '
              'traces kept by autocuts')

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

        return self._synced_temperature_sweep().wait_for_temperature(
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
        r0_stability_tolerance_percent, or stability_timeout is reached.

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

        # a run this long of unusable readings means the thermometer
        # is not in a state the fit can describe; waiting longer will
        # not change that
        max_consecutive_nonfinite = 10
        consecutive_nonfinite = 0

        while True:

            r0 = self.measure_r0(
                nb_events=self._nb_events_stability
            )
            history.append(r0)

            if not (np.isfinite(r0) and r0 > 0):
                consecutive_nonfinite = consecutive_nonfinite + 1
                if consecutive_nonfinite >= max_consecutive_nonfinite:
                    print('WARNING: R0 settle saw '
                          f'{consecutive_nonfinite} consecutive '
                          'unusable readings, giving up on this '
                          'point!')
                    return False, history
            else:
                consecutive_nonfinite = 0

            if len(history) >= 5:
                recent = history[-5:]
                reference = recent[-1]
                all_within = True

                # every reading has to be usable before any of them
                # can agree: a NaN comparison is False, so without
                # this the loop would call garbage stable
                for value in recent:
                    if not (np.isfinite(value) and value > 0):
                        all_within = False

                if reference == 0:
                    # relative comparison is meaningless at zero,
                    # keep waiting for a nonzero stable R0
                    all_within = False
                elif all_within:
                    for value in recent:
                        offset = abs(value - reference) / abs(reference)
                        tolerance = (
                            self._r0_stability_tolerance_percent
                        )
                        if (offset * 100.0) > tolerance:
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
        exceeds r0_stability_tolerance_percent, since the feedback cannot
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
                and scatter_percent > self._r0_stability_tolerance_percent):
            print('WARNING: R0 drift '
                  f'({scatter_percent:.3g} percent) exceeds '
                  'r0_stability_tolerance_percent '
                  f'({self._r0_stability_tolerance_percent:.6g} percent), '
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
        print(f'\nThermometer TES circuit: rshunt = '
              f'{self._thermometer_rshunt * 1000.0:.6g} mOhms, '
              f'rparasitic = '
              f'{self._thermometer_rparasitic * 1000.0:.6g} mOhms, '
              f'rn = {self._thermometer_rn * 1000.0:.6g} mOhms')
        print(f'Heater TES circuit: rshunt = '
              f'{self._heater_rshunt * 1000.0:.6g} mOhms, '
              f'rparasitic = '
              f'{self._heater_rparasitic * 1000.0:.6g} mOhms, '
              f'rn = {self._heater_rn * 1000.0:.6g} mOhms')

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
            # remembered so shutdown can restore the operator's bias
            # points, including when a Ctrl-C lands inside a relock
            self._heater_initial_bias_ua = float(heater_bias_ua)
            self._thermometer_initial_bias_ua = float(
                thermometer_bias_ua
            )

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

            # everything needed to recompute R0 offline under
            # different circuit assumptions. The thermometer bias is
            # deliberately not here: a relock can shift it, so it is a
            # per row CSV column instead
            self._diagnostics['circuit'] = {
                'sg_current_amps_pp': self._sg_current_amps_pp,
                'close_loop_norm': self._get_close_loop_norm(),
                'thermometer_rshunt_ohms': self._thermometer_rshunt,
                'thermometer_rparasitic_ohms': (
                    self._thermometer_rparasitic
                ),
                'thermometer_rn_ohms': self._thermometer_rn,
                'heater_rshunt_ohms': self._heater_rshunt,
                'heater_rparasitic_ohms': self._heater_rparasitic,
                'heater_rn_ohms': self._heater_rn,
            }

            # the relock runs at the top of the bias vector so that
            # startup matches the conditions every later relock runs
            # under
            self._set_heater_bias(bias_ua=self._bias_list[0])
            self._diagnostics['startup_relock'] = (
                self.relock_and_verify()
            )

            # the heater TES goes to its lowest normal state before
            # the startup check and the drift check, so both are taken
            # at the same fixed, lowest power state
            self._set_heater_bias(bias_ua=self._bias_min)

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

                self.run_single_step(
                    temperature_mk=temperature_mk,
                    step_index=step_index
                )

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
        heater setpoint to 0, both TES biases restored to their
        pre-run values (left untouched if unknown), diagnostics
        flushed.

        The thermometer TES bias is restored as well as the heater's,
        because the relock drives the thermometer hard normal and an
        interrupt landing inside one would otherwise leave it there.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        print('INFO: Safe shutdown, turning off the signal generator, '
              'setting heater setpoint to 0 and restoring the heater '
              'TES bias')

        self.teardown_signal_generator()

        # a Ctrl-C landing inside the restore below must not skip the
        # rest of shutdown, so it is remembered and re-raised at the end
        pending_interrupt = None

        if self._instrument is not None:

            try:
                self._synced_temperature_sweep().heater_to_zero()
            except Exception as err:
                print(f'ERROR setting heater setpoint to 0: {err}')

            # both TES biases are restored. The thermometer is in this
            # list because the relock drives it hard normal, so an
            # interrupt landing inside a relock would otherwise strand
            # it at relock_bias_uA
            restore_targets = [
                ('heater', self._heater_tes_channel,
                 self._heater_initial_bias_ua),
                ('thermometer', self._thermometer_tes_channel,
                 self._thermometer_initial_bias_ua),
            ]

            for label, channel, initial_bias_ua in restore_targets:

                if initial_bias_ua is None:
                    print(f'INFO: Pre-run {label} TES bias unknown, '
                          f'leaving {label} TES bias untouched')
                    continue

                # the driver reports a refused write by return value
                # rather than by raising, so the success message is
                # printed only when the write actually reported
                # success. It is the operator's only confirmation that
                # the TES was put back
                try:
                    success = self._instrument.set_tes_bias(
                        bias=initial_bias_ua,
                        unit='uA',
                        detector_channel=channel
                    )

                    if success:
                        print(f'INFO: {label} TES bias set back to '
                              'its original pre-run value of '
                              f'{initial_bias_ua:.6g} uA')
                    else:
                        print(f'ERROR restoring {label} TES bias: the '
                              'instrument refused the write, so the '
                              f'{label} TES is NOT at its pre-run '
                              f'value of {initial_bias_ua:.6g} uA! '
                              'Check it by hand.')

                except Exception as err:
                    print(f'ERROR restoring {label} TES bias: {err}')

                except BaseException as err:
                    # a second Ctrl-C landing here would otherwise skip
                    # the diagnostics save and the DAQ teardown below
                    print(f'ERROR restoring {label} TES bias: {err!r}. '
                          'Finishing shutdown before stopping.')
                    pending_interrupt = err

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

        if pending_interrupt is not None:
            raise pending_interrupt

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

    def run_single_step(self, temperature_mk=None, step_index=None):
        """
        Run one temperature point of the Gab sweep.

        Sets the MC temperature, relocks the thermometer at the top of
        the bias vector, then walks the heater bias down through every
        point recording R0 at each one. No R0 is targeted and nothing
        is converged: the operating point is chosen offline from the
        recorded curve.

        Parameters
        ----------
        temperature_mk : float
            MC temperature setpoint [mK].
        step_index : int
            Zero-based index of this temperature in the sweep.

        Returns
        -------
        rows : list of dict
            One row per bias point, keyed by CSV_COLUMNS.
        """

        if self._verbose:
            print(f'\nINFO: Step {step_index}: setting MC temperature '
                  f'to {temperature_mk:.6g} mK')

        # the setpoint is only applied here; the driver's own wait is
        # not used because it cannot report whether it reached the
        # setpoint or simply ran out of time
        self._synced_temperature_sweep().set_setpoint(
            temperature_mk=temperature_mk
        )

        temperature_ok, temperature_history = self.wait_for_temperature(
            temperature_mk=temperature_mk
        )

        step_diagnostics = {'step': step_index,
                            'temperature_setpoint_mk': temperature_mk,
                            'temperature_ok': temperature_ok,
                            'temperature_history': temperature_history,
                            'points': list()}

        # the relock runs at the top of the vector, where the absorber
        # is warmest and the thermometer sits highest in its
        # transition, and never between two bias points: a relock
        # shifts the readout offset, which would split this
        # temperature's R0 curve across two different footings
        self._set_heater_bias(bias_ua=self._bias_list[0])
        relock_result = self.relock_and_verify()
        step_diagnostics['relock'] = relock_result

        rows = list()
        nb_failed_fits = 0

        for bias_index, bias_ua in enumerate(self._bias_list):

            row_dict, point_diagnostics = self.measure_bias_point(
                step_index=step_index,
                bias_index=bias_index,
                bias_ua=bias_ua,
                temperature_mk=temperature_mk,
                temperature_ok=temperature_ok
            )

            if not row_dict['didv_fit_ok']:
                nb_failed_fits = nb_failed_fits + 1

            rows.append(row_dict)
            step_diagnostics['points'].append(point_diagnostics)
            self._append_datapoint(row_dict=row_dict)

        self._diagnostics['steps'].append(step_diagnostics)

        if nb_failed_fits == len(self._bias_list):
            print(f'WARNING: Step {step_index} '
                  f'({temperature_mk:.6g} mK): the dIdV fit failed at '
                  'every bias point. This is a dead temperature, not '
                  'a statistic: it contributes nothing to the '
                  'measurement. Check the thermometer lock and bias.')
        elif nb_failed_fits > 0 and self._verbose:
            print(f'INFO: Step {step_index}: {nb_failed_fits} of '
                  f'{len(self._bias_list)} bias points had no usable '
                  'dIdV fit, as expected at the ends of the vector')

        return rows

    def _set_heater_bias(self, bias_ua=None):
        """
        Set the heater TES bias and wait for it to settle.

        Parameters
        ----------
        bias_ua : float
            Requested heater TES bias [uA].

        Returns
        -------
        applied_bias_ua : float
            The bias the front end board actually applied [uA].
        """

        success = self._instrument.set_tes_bias(
            bias=bias_ua,
            unit='uA',
            detector_channel=self._heater_tes_channel
        )

        if not success:
            print('ERROR: the instrument refused to set the heater '
                  f'TES bias to {bias_ua:.6g} uA!')

        if self._post_bias_wait > 0:
            time.sleep(self._post_bias_wait)

        return float(self._instrument.get_tes_bias(
            detector_channel=self._heater_tes_channel,
            unit='uA'
        ))

    def measure_bias_point(self, step_index=None, bias_index=None,
                           bias_ua=None, temperature_mk=None,
                           temperature_ok=None):
        """
        Measure one heater bias point of one temperature step.

        Parameters
        ----------
        step_index : int
            Zero-based temperature index.
        bias_index : int
            Zero-based position in the bias vector.
        bias_ua : float
            Requested heater TES bias [uA].
        temperature_mk : float
            MC temperature setpoint [mK].
        temperature_ok : bool
            Whether the setpoint was reached for this temperature.

        Returns
        -------
        row_dict : dict
            One row keyed by CSV_COLUMNS.
        point_diagnostics : dict
            Fit parameters and covariance for offline recomputation.
        """

        applied_bias_ua = self._set_heater_bias(bias_ua=bias_ua)

        stability_ok, stability_history = self.wait_for_settled_r0()

        quality = self.measure_r0_quality(bias_index=bias_index)

        temperature_measurement = self.measure_mc_temperature()

        power_w = heater_power_watts(
            bias_ua=applied_bias_ua,
            rshunt=self._heater_rshunt,
            rparasitic=self._heater_rparasitic,
            rnormal=self._heater_rn
        )

        thermometer_bias_ua = (
            self._get_thermometer_bias_amps() * 1.0e6
        )

        row_dict = {
            'step': step_index,
            'bias_index': bias_index,
            'timestamp': datetime.now().isoformat(),
            'temperature_setpoint_mk': temperature_mk,
            'mc_temperature_mk': (
                temperature_measurement['temperature_k'] * 1000.0
            ),
            'mc_temperature_err_mk': (
                temperature_measurement['temperature_err_k'] * 1000.0
            ),
            'heater_tes_bias_requested_ua': bias_ua,
            'heater_tes_bias_ua': applied_bias_ua,
            'heater_tes_power_w': power_w,
            'thermometer_tes_bias_ua': thermometer_bias_ua,
            'thermometer_r0_ohms': quality['r0'],
            'thermometer_r0_err_ohms': quality['r0_err'],
            'thermometer_i0_amps': quality['i0'],
            'thermometer_p0_watts': quality['p0'],
            'didv_fit_cost': quality['fit_cost'],
            'didv_fit_ok': quality['didv_fit_ok'],
            'autocuts_ok': quality['autocuts_ok'],
            'nb_traces': quality['nb_traces'],
            'nb_traces_kept': quality['nb_traces_kept'],
            'stability_ok': stability_ok,
            'temperature_ok': temperature_ok,
        }

        point_diagnostics = {
            'bias_index': bias_index,
            'fit_params': quality['fit_params'],
            'cov': quality['cov'],
            'stability_history': stability_history,
            'temperature_measurement': temperature_measurement,
            'row': row_dict,
        }

        if self._verbose:
            self._print_r0_quality(
                quality=quality,
                label=(f'Step {step_index} bias '
                       f'{bias_index + 1}/{len(self._bias_list)} at '
                       f'{applied_bias_ua:.6g} uA')
            )

        return row_dict, point_diagnostics


    def _save_diagnostics(self):
        """
        Save the diagnostics dictionary as a pickle.
        """

        if self._output_path is None:
            return

        diagnostics_path = self._output_path + '/gab_sweep_diagnostics.p'
        with open(diagnostics_path, 'wb') as f:
            pickle.dump(self._diagnostics, f)
