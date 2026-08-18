import csv
import os

import numpy as np
import pytest
import qetpy as qp

from pytesdaq.sequencer import gab_sweep as gab_sweep_module
from pytesdaq.sequencer.gab_sweep import (
    build_bias_list,
    heater_power_watts,
    fit_didv_r0,
)

# committed test fixture, so the suite runs on a fresh clone
SETUP_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'fixtures',
    'setup_test.ini'
)


def _make_dry_sweep():
    from pytesdaq.sequencer import GabSweep
    sweep = GabSweep(
        sequencer_file='pytesdaq/config/gab_sweep.ini.example',
        setup_file=SETUP_FILE,
        dry_run=True,
    )
    return sweep


def test_rejects_same_thermometer_and_heater_channel(tmp_path):
    # one TES cannot be both the thermometer and the heater
    from pytesdaq.sequencer import GabSweep

    with open('pytesdaq/config/gab_sweep.ini.example', 'r') as f:
        config_text = f.read()

    config_text = config_text.replace(
        'heater_tes_channel = C',
        'heater_tes_channel = D'
    )
    config_file = tmp_path / 'gab_sweep_same_channel.ini'
    config_file.write_text(config_text)

    with pytest.raises(ValueError, match='must be different channels'):
        GabSweep(
            sequencer_file=str(config_file),
            setup_file=SETUP_FILE,
            dry_run=True,
        )


def test_wait_for_settled_r0_timer_mode(monkeypatch):
    # timer mode sleeps settle_wait_time and never runs the check
    sweep = _make_dry_sweep()
    sweep._use_stability_check = False
    sweep._settle_wait_time = 42.0

    slept = list()
    monkeypatch.setattr(gab_sweep_module.time, 'sleep', slept.append)

    def fail_stability():
        raise AssertionError('stability check must not run in timer mode')

    sweep.wait_for_stable_r0 = fail_stability

    settle_ok, history = sweep.wait_for_settled_r0()

    assert settle_ok is True
    assert history == []
    assert slept == [42.0]


def test_wait_for_settled_r0_stability_mode():
    # stability mode delegates, passing its result through unchanged
    sweep = _make_dry_sweep()
    sweep._use_stability_check = True
    sweep.wait_for_stable_r0 = lambda: (False, [1.0, 2.0])

    settle_ok, history = sweep.wait_for_settled_r0()

    assert settle_ok is False
    assert history == [1.0, 2.0]


def test_timer_mode_does_not_require_stability_parameters():
    # the example config is timer mode and omits the stability
    # parameters, so constructing it must not raise
    sweep = _make_dry_sweep()

    assert sweep._use_stability_check is False
    assert sweep._settle_wait_time == 5.0
    assert sweep._stability_timeout is None
    assert sweep._nb_events_stability is None


def test_stability_mode_requires_its_parameters(tmp_path):
    # switching the method on without its parameters must be caught
    from pytesdaq.sequencer import GabSweep

    with open('pytesdaq/config/gab_sweep.ini.example', 'r') as f:
        config_text = f.read()

    config_text = config_text.replace(
        'use_stability_check = false',
        'use_stability_check = true'
    )
    config_file = tmp_path / 'gab_sweep_stability.ini'
    config_file.write_text(config_text)

    with pytest.raises(ValueError, match='nb_events_stability'):
        GabSweep(
            sequencer_file=str(config_file),
            setup_file=SETUP_FILE,
            dry_run=True,
        )


def test_didv_config_parses_from_example():
    # the signal generator and fit keys parse into the expected
    # attributes; these keys are optional and fall back to the same
    # defaults when omitted
    sweep = _make_dry_sweep()

    assert sweep._signal_gen_frequency == 50.0
    assert sweep._signal_gen_voltage == 20.0
    assert sweep._signal_gen_current is None
    assert sweep._signal_gen_offset == 0.0
    assert sweep._signal_gen_phase == 0.0
    assert sweep._didv_fcutoff == 50000.0
    assert sweep._thermometer_rshunt == 0.005
    assert sweep._thermometer_rparasitic == 0.00176

    # 50 ms at 50 Hz rounds to an integer number of periods
    assert sweep._nb_cycles == round(0.050 * 50.0)
    assert sweep._trace_length_ms_actual == pytest.approx(
        sweep._nb_cycles / 50.0 * 1000.0
    )


def test_rejects_both_signal_gen_voltage_and_current(tmp_path):
    # the amplitude is either a voltage or a current, never both
    from pytesdaq.sequencer import GabSweep

    with open('pytesdaq/config/gab_sweep.ini.example', 'r') as f:
        config_text = f.read()

    config_text = config_text.replace(
        '#signal_gen_voltage_mVpp = 20',
        'signal_gen_voltage_mVpp = 20'
    )
    config_text = config_text.replace(
        '#signal_gen_current_uApp = 5',
        'signal_gen_current_uApp = 5'
    )
    config_file = tmp_path / 'gab_sweep_both_amplitudes.ini'
    config_file.write_text(config_text)

    with pytest.raises(ValueError, match='not both'):
        GabSweep(
            sequencer_file=str(config_file),
            setup_file=SETUP_FILE,
            dry_run=True,
        )


def _make_synthetic_didv_traces(sweep, r0_true, nb_traces=10,
                                noise_amps=1.0e-8, seed=42):
    # synthetic 2-pole square wave response with a known R0: in the
    # infinite loop gain approximation dVdI(0) = A + B = rl - r0
    # tau1 is kept well below the signal generator period so plenty
    # of harmonics constrain the zero frequency dVdI (a fall time
    # comparable to the period makes R0 poorly determined)
    rl = sweep._thermometer_rshunt + sweep._thermometer_rparasitic
    params = {
        'A': 0.2,
        'B': (rl - r0_true) - 0.2,
        'C': 0.0,
        'tau1': 1.0e-4,
        'tau2': 1.0e-5,
        'tau3': 0.0,
    }

    sgamp = 2.0e-6
    nb_samples = int(round(
        sweep._nb_cycles * sweep._sample_rate
        / sweep._signal_gen_frequency
    ))
    t = np.arange(nb_samples) / sweep._sample_rate
    response = qp.squarewaveresponse(
        t,
        sgamp,
        sweep._signal_gen_frequency,
        params,
        rsh=sweep._thermometer_rshunt,
    )

    rng = np.random.default_rng(seed=seed)
    noise = rng.normal(0.0, noise_amps, size=(nb_traces, nb_samples))
    traces = response[None, :] + noise

    return traces, sgamp


def test_fit_didv_r0_recovers_known_r0():
    # the module level fit helper must recover the R0 baked into a
    # synthetic 2-pole square wave response
    sweep = _make_dry_sweep()
    r0_true = 0.150
    traces, sgamp = _make_synthetic_didv_traces(sweep, r0_true)

    result = fit_didv_r0(
        traces=traces,
        sample_rate=sweep._sample_rate,
        sgfreq=sweep._signal_gen_frequency,
        sgamp=sgamp,
        rsh=sweep._thermometer_rshunt,
        rp=sweep._thermometer_rparasitic,
        ibias=1.0e-4,
        guess_params=None,
        fcutoff=sweep._didv_fcutoff,
    )

    assert result['r0'] == pytest.approx(r0_true, rel=0.05)
    assert result['r0_err'] >= 0.0
    assert np.isfinite(result['fit_cost'])


def test_measure_r0_quality_reports_metrics():
    # fake DAQ returning synthetic dIdV traces in volts with a unity
    # volts to amps normalization
    sweep = _make_dry_sweep()
    r0_true = 0.150
    traces, sgamp = _make_synthetic_didv_traces(sweep, r0_true)
    nb_traces = traces.shape[0]

    class FakeDaq:
        @staticmethod
        def read_many_events(nevents, adctovolt=False):
            return traces[:, None, :]

    sweep._daq = FakeDaq()
    sweep._sg_current_amps_pp = sgamp
    sweep._close_loop_norm = 1.0
    sweep._thermometer_bias_amps = 1.0e-4
    sweep._guess_params = [None]

    quality = sweep.measure_r0_quality(bias_index=0)

    assert quality['nb_traces'] == nb_traces
    assert 0 < quality['nb_traces_kept'] <= nb_traces
    assert quality['r0'] == pytest.approx(r0_true, rel=0.05)
    assert quality['r0_err'] >= 0.0

    # a good fit seeds the same bias point at the next temperature
    assert sweep._guess_params[0] is not None

    # measure_r0 stays a thin float-returning wrapper
    assert sweep.measure_r0() == pytest.approx(r0_true, rel=0.05)


def test_measure_r0_requires_signal_generator_setup():
    # measuring before the square wave is on would silently fit noise
    sweep = _make_dry_sweep()

    with pytest.raises(ValueError, match='signal generator'):
        sweep.measure_r0_quality()


def test_shutdown_restores_initial_heater_bias():
    # shutdown must put the heater TES back at the bias the user had
    # it at before the run
    sweep = _make_dry_sweep()

    device = {'bias': 500.0}
    heater_calls = list()

    def fake_set_bias(bias, unit=None, detector_channel=None):
        """
        Record the commanded TES bias.

        Parameters
        ----------
        bias : float
            The bias value to write.
        unit : str or None
            Unit of the bias, unused by this fake.
        detector_channel : str or None
            Detector channel name to write to, unused by this fake.

        Returns
        -------
        success : bool
            Always True.
        """
        device['bias'] = float(bias)
        return True

    def fake_set_temperature(value, **kwargs):
        """
        Record the commanded setpoint and where it was routed.

        Recording the routing matters: a heater-to-zero aimed at the
        wrong channel leaves the real heater driving.

        Parameters
        ----------
        value : float
            The commanded temperature setpoint.
        **kwargs : dict
            Channel routing and wait flags passed by the caller.

        Returns
        -------
        success : bool
            Always True.
        """
        heater_calls.append((value, kwargs))
        return True

    class FakeInstrument:
        set_tes_bias = staticmethod(fake_set_bias)
        set_temperature = staticmethod(fake_set_temperature)

        @staticmethod
        def set_signal_gen_onoff(on_off_flag, detector_channel=None):
            return True

        @staticmethod
        def connect_signal_gen_to_tes(do_connect, detector_channel=None):
            return True

    sweep._instrument = FakeInstrument()
    sweep._daq = None
    sweep._heater_initial_bias_ua = 42.0

    sweep.shutdown()

    assert device['bias'] == 42.0

    # the MC heater setpoint must be driven to 0, on the configured
    # heater channel, without blocking on the fridge getting there
    assert len(heater_calls) == 1
    value, kwargs = heater_calls[0]
    assert value == 0
    assert kwargs['heater_channel_name'] == sweep._heater_name
    assert kwargs['channel_name'] == sweep._thermometer_name
    assert kwargs['wait_temperature_reached'] is False


def test_shutdown_reports_a_refused_heater_bias_restore(capsys):
    """
    Control.set_tes_bias reports a refused write by return value, not
    by raising. Printing the success line regardless would tell the
    operator the heater TES was put back when it was not, and a heater
    TES left biased keeps warming the absorber.

    Parameters
    ----------
    capsys : pytest fixture
        Captures stdout and stderr produced during the test.

    Returns
    -------
    None
    """
    sweep = _make_dry_sweep()

    def refusing_set_bias(bias=None, unit=None, detector_channel=None):
        """
        Refuse the write the way the real driver does, by returning
        False rather than raising.

        Parameters
        ----------
        bias : float or None
            The bias value to write, unused by this fake.
        unit : str or None
            Unit of the bias, unused by this fake.
        detector_channel : str or None
            Detector channel name, unused by this fake.

        Returns
        -------
        success : bool
            Always False.
        """
        return False

    class FakeInstrument:
        set_tes_bias = staticmethod(refusing_set_bias)

        @staticmethod
        def set_temperature(value, **kwargs):
            return True

        @staticmethod
        def set_signal_gen_onoff(on_off_flag, detector_channel=None):
            return True

        @staticmethod
        def connect_signal_gen_to_tes(do_connect, detector_channel=None):
            return True

    sweep._instrument = FakeInstrument()
    sweep._daq = None
    sweep._heater_initial_bias_ua = 42.0

    capsys.readouterr()
    sweep.shutdown()
    printed = capsys.readouterr().out

    assert 'set back to its' not in printed
    assert 'ERROR' in printed


def test_shutdown_turns_off_signal_generator():
    # the square wave must not be left running on the thermometer TES
    sweep = _make_dry_sweep()

    calls = list()

    class FakeInstrument:
        @staticmethod
        def set_signal_gen_onoff(on_off_flag, detector_channel=None):
            calls.append(('onoff', on_off_flag))
            return True

        @staticmethod
        def connect_signal_gen_to_tes(do_connect, detector_channel=None):
            calls.append(('connect', do_connect))
            return True

        @staticmethod
        def set_temperature(value, **kwargs):
            calls.append(('temperature', value,
                          kwargs.get('heater_channel_name')))
            return True

    sweep._instrument = FakeInstrument()
    sweep._daq = None

    sweep.shutdown()

    assert ('onoff', 'off') in calls
    assert ('connect', False) in calls
    assert ('temperature', 0, sweep._heater_name) in calls


def test_drift_check_parameters_parse_from_example():
    # the drift check keys are optional in the config
    sweep = _make_dry_sweep()

    assert sweep._drift_check_nb_measurements == 3
    assert sweep._drift_check_wait_time == 5.0


def test_run_drift_check_measures_scatter(monkeypatch):
    # the drift check repeats the R0 measurement at fixed conditions;
    # its scatter is the R0 repeatability, the error bar on every point
    sweep = _make_dry_sweep()

    r0_values = [250.0, 252.0, 248.0, 251.0, 249.0]
    quality_sequence = list()
    for value in r0_values:
        quality_sequence.append({
            'r0': value,
            'r0_err': 1.0,
            'i0': 1.0e-6,
            'p0': 1.0e-13,
            'fit_cost': 1.0,
            'nb_traces': 50,
            'nb_traces_kept': 45,
            'autocuts_ok': True,
            'didv_fit_ok': True,
        })

    def fake_quality(nb_events=None, bias_index=None):
        return quality_sequence.pop(0)

    sweep.measure_r0_quality = fake_quality
    sweep._drift_check_nb_measurements = len(r0_values)
    sweep._drift_check_wait_time = 60.0

    slept = list()
    monkeypatch.setattr(gab_sweep_module.time, 'sleep', slept.append)

    drift = sweep.run_drift_check()

    assert drift['r0_values'] == r0_values
    assert drift['mean'] == pytest.approx(np.mean(r0_values))
    assert drift['scatter'] == pytest.approx(np.std(r0_values))
    assert drift['scatter'] == pytest.approx(np.std(r0_values))
    # one wait between consecutive measurements, none before the first
    assert slept == [60.0, 60.0, 60.0, 60.0]
    assert sweep._diagnostics['drift_check'] == drift


def test_run_drift_check_warns_when_scatter_exceeds_tolerance(
        monkeypatch, capsys):
    # drift larger than the convergence tolerance means the feedback
    # cannot work reliably, the user must be warned up front
    sweep = _make_dry_sweep()

    r0_values = [250.0, 290.0, 210.0, 270.0, 230.0]
    quality_sequence = list()
    for value in r0_values:
        quality_sequence.append({
            'r0': value,
            'r0_err': 1.0,
            'i0': 1.0e-6,
            'p0': 1.0e-13,
            'fit_cost': 1.0,
            'nb_traces': 50,
            'nb_traces_kept': 45,
            'autocuts_ok': True,
            'didv_fit_ok': True,
        })

    def fake_quality(nb_events=None, bias_index=None):
        return quality_sequence.pop(0)

    sweep.measure_r0_quality = fake_quality
    monkeypatch.setattr(gab_sweep_module.time, 'sleep', lambda t: None)

    sweep.run_drift_check()

    output = capsys.readouterr().out
    assert 'WARNING' in output
    assert 'drift' in output


def test_run_drift_check_disabled_returns_none():
    # fewer than 2 measurements cannot give a scatter, the check is
    # skipped and the noise floor stays at zero
    sweep = _make_dry_sweep()
    sweep._drift_check_nb_measurements = 0

    result = sweep.run_drift_check()

    assert result is None


def test_shutdown_leaves_heater_bias_when_initial_unknown():
    # a failure before preflight means the pre-run bias was never
    # read, so shutdown must not touch the heater TES bias
    sweep = _make_dry_sweep()

    device = {'bias': 500.0}
    heater_calls = list()

    def fake_set_bias(bias, unit=None, detector_channel=None):
        """
        Record the commanded TES bias.

        Parameters
        ----------
        bias : float
            The bias value to write.
        unit : str or None
            Unit of the bias, unused by this fake.
        detector_channel : str or None
            Detector channel name to write to, unused by this fake.

        Returns
        -------
        success : bool
            Always True.
        """
        device['bias'] = float(bias)
        return True

    def fake_set_temperature(value, **kwargs):
        """
        Record the commanded setpoint and where it was routed.

        Parameters
        ----------
        value : float
            The commanded temperature setpoint.
        **kwargs : dict
            Channel routing and wait flags passed by the caller.

        Returns
        -------
        success : bool
            Always True.
        """
        heater_calls.append((value, kwargs))
        return True

    class FakeInstrument:
        set_tes_bias = staticmethod(fake_set_bias)
        set_temperature = staticmethod(fake_set_temperature)

        @staticmethod
        def set_signal_gen_onoff(on_off_flag, detector_channel=None):
            return True

        @staticmethod
        def connect_signal_gen_to_tes(do_connect, detector_channel=None):
            return True

    sweep._instrument = FakeInstrument()
    sweep._daq = None

    sweep.shutdown()

    assert device['bias'] == 500.0

    # not knowing the pre-run TES bias is no reason to leave the MC
    # heater driving, so the setpoint still goes to 0
    assert len(heater_calls) == 1
    value, kwargs = heater_calls[0]
    assert value == 0
    assert kwargs['heater_channel_name'] == sweep._heater_name


def test_gab_syncs_instrument_and_verbose_to_the_shared_sweep():
    """
    Both the instrument and the verbose flag can be reassigned after
    construction: _instantiate_drivers replaces the instrument, and
    the inherited verbose setter writes only to this object. The
    shared sweep holds its own copies, so both are pushed across
    before every use rather than captured once at construction.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    sweep = _make_dry_sweep()

    replacement_instrument = object()
    sweep._instrument = replacement_instrument
    sweep._verbose = False

    synced = sweep._synced_temperature_sweep()

    assert synced.instrument is replacement_instrument
    assert synced.verbose is False

    # and again after they change, so this is a refresh not a one-off
    another_instrument = object()
    sweep._instrument = another_instrument
    sweep._verbose = True

    synced = sweep._synced_temperature_sweep()

    assert synced.instrument is another_instrument
    assert synced.verbose is True


def test_gab_delegates_wait_for_temperature_to_shared_sweep():
    """
    Confirm wait_for_temperature stays a public GabSweep method that
    forwards to the shared TemperatureSweep, rather than re-testing
    the wait logic itself (that logic now lives in
    test_temperature_sweep.py against TemperatureSweep directly).

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    sweep = _make_dry_sweep()
    calls = list()

    def fake_wait(temperature_mk=None):
        """
        Record the setpoint it was asked to wait for and report that
        it was reached.

        Parameters
        ----------
        temperature_mk : float or None
            MC temperature setpoint [mK].

        Returns
        -------
        temperature_ok : bool
            Always True.
        history : list of float
            A single fake reading [mK].
        """
        calls.append(temperature_mk)
        return True, [40.0]

    sweep._temperature_sweep.wait_for_temperature = fake_wait

    temperature_ok, history = sweep.wait_for_temperature(
        temperature_mk=40.0
    )

    assert calls == [40.0]
    assert temperature_ok is True
    assert history == [40.0]


def test_gab_delegates_measure_mc_temperature_to_shared_sweep():
    """
    Confirm measure_mc_temperature stays a public GabSweep method that
    forwards to the shared TemperatureSweep's measure_temperature,
    rather than re-testing the sampling and fit logic itself (that
    logic now lives in test_temperature_sweep.py against
    TemperatureSweep directly).

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    sweep = _make_dry_sweep()

    def fake_measure():
        """
        Report a fixed temperature measurement in the shape the real
        measure_temperature returns.

        Parameters
        ----------
        None

        Returns
        -------
        measurement : dict
            Keys temperature_k, temperature_err_k [K], fit_ok,
            nb_samples and samples.
        """
        return {'temperature_k': 0.040, 'temperature_err_k': 0.0001,
                'fit_ok': True, 'nb_samples': 100, 'samples': [0.040]}

    sweep._temperature_sweep.measure_temperature = fake_measure

    measurement = sweep.measure_mc_temperature()

    assert measurement['temperature_k'] == pytest.approx(0.040)


def test_config_lookup_ignores_unit_suffix_case():
    # configparser lowercases option names, so the canonical
    # capitalization used in the code must still find the value
    config_dict = {'bias_min_ua': '100', 'sample_rate_hz': '1250000'}

    assert gab_sweep_module.config_has(config_dict, 'bias_min_uA')
    assert gab_sweep_module.config_get(
        config_dict, 'sample_rate_Hz'
    ) == '1250000'
    assert not gab_sweep_module.config_has(config_dict, 'missing_key_uA')


def test_build_bias_list_from_step_is_descending():
    # start/stop/step form spans the endpoints and comes out descending
    config_dict = {
        'use_bias_vect': False,
        'bias_min_ua': 38.0,
        'bias_max_ua': 300.0,
        'bias_step_ua': 15.0,
    }
    result = build_bias_list(config_dict=config_dict)

    assert result[0] == pytest.approx(300.0)
    assert result[-1] == pytest.approx(38.0)
    for index in range(1, len(result)):
        assert result[index] < result[index - 1]


def test_build_bias_list_explicit_vector_sorted_descending():
    # typed ascending, swept descending
    config_dict = {
        'use_bias_vect': True,
        'bias_vect_ua': [38.0, 90.0, 180.0, 300.0],
        'bias_min_ua': 38.0,
        'bias_max_ua': 300.0,
    }
    result = build_bias_list(config_dict=config_dict)

    assert result == [300.0, 180.0, 90.0, 38.0]


def test_build_bias_list_rejects_missing_endpoint():
    # a vector that never measures the parked state is rejected
    config_dict = {
        'use_bias_vect': True,
        'bias_vect_ua': [90.0, 180.0, 300.0],
        'bias_min_ua': 38.0,
        'bias_max_ua': 300.0,
    }
    with pytest.raises(ValueError, match='38'):
        build_bias_list(config_dict=config_dict)


def test_build_bias_list_rejects_entry_outside_endpoints():
    config_dict = {
        'use_bias_vect': True,
        'bias_vect_ua': [38.0, 90.0, 400.0, 300.0],
        'bias_min_ua': 38.0,
        'bias_max_ua': 300.0,
    }
    with pytest.raises(ValueError, match='outside'):
        build_bias_list(config_dict=config_dict)


def test_build_bias_list_rejects_duplicates():
    config_dict = {
        'use_bias_vect': True,
        'bias_vect_ua': [38.0, 90.0, 90.0, 300.0],
        'bias_min_ua': 38.0,
        'bias_max_ua': 300.0,
    }
    with pytest.raises(ValueError, match='duplicate'):
        build_bias_list(config_dict=config_dict)


def test_build_bias_list_dedups_near_endpoint_within_tolerance():
    # an arange point landing a hair below bias_max must not survive
    # next to the appended bias_max
    config_dict = {
        'use_bias_vect': False,
        'bias_min_ua': 0.0,
        'bias_max_ua': 300.0,
        'bias_step_ua': 300.0 / 7.0,
    }
    result = build_bias_list(config_dict=config_dict)

    gaps = [
        result[index - 1] - result[index]
        for index in range(1, len(result))
    ]
    assert min(gaps) > 1.0e-6


def test_heater_power_matches_closed_form():
    # P = I^2 Rsh^2 Rn / (Rsh + Rp + Rn)^2
    power = heater_power_watts(
        bias_ua=300.0,
        rshunt=5.0e-3,
        rparasitic=2.98e-3,
        rnormal=624.0e-3,
    )
    bias_amps = 300.0e-6
    rload = 5.0e-3 + 2.98e-3
    tes_current = bias_amps * 5.0e-3 / (rload + 624.0e-3)
    expected = (tes_current ** 2) * 624.0e-3

    assert power == pytest.approx(expected)


def test_heater_power_is_zero_at_zero_bias():
    power = heater_power_watts(
        bias_ua=0.0,
        rshunt=5.0e-3,
        rparasitic=2.98e-3,
        rnormal=624.0e-3,
    )
    assert power == pytest.approx(0.0)


def test_circuit_resistances_parse_from_example():
    # all six keys land as Ohms on the sweep
    sweep = _make_dry_sweep()

    assert sweep._thermometer_rshunt == pytest.approx(5.0e-3)
    assert sweep._thermometer_rparasitic == pytest.approx(1.76e-3)
    assert sweep._thermometer_rn > 0
    assert sweep._heater_rshunt == pytest.approx(5.0e-3)
    assert sweep._heater_rparasitic == pytest.approx(2.98e-3)
    assert sweep._heater_rn == pytest.approx(624.0e-3)


@pytest.mark.parametrize('missing_key', [
    'thermometer_rshunt_mOhm',
    'thermometer_rparasitic_mOhm',
    'thermometer_rn_mOhm',
    'heater_rshunt_mOhm',
    'heater_rparasitic_mOhm',
    'heater_rn_mOhm',
])
def test_missing_resistance_key_fails_naming_it(tmp_path, missing_key):
    # a config file that half-applies is worse than one that refuses
    from pytesdaq.sequencer import GabSweep

    with open('pytesdaq/config/gab_sweep.ini.example', 'r') as f:
        config_text = f.read()

    config_text = config_text.replace(f'{missing_key} = ', '#removed = ')
    config_file = tmp_path / 'gab_sweep_missing.ini'
    config_file.write_text(config_text)

    with pytest.raises(ValueError, match=missing_key):
        GabSweep(
            sequencer_file=str(config_file),
            setup_file=SETUP_FILE,
            dry_run=True,
        )


def _make_fake_daq(traces):
    # read_many_events returns (nb_events, nb_channels, nb_samples);
    # the sweep reads a single channel
    class FakeDaq:
        @staticmethod
        def read_many_events(nb_events, adctovolt=True):
            return traces[:, None, :]

    return FakeDaq()


def test_measure_r0_quality_flags_a_failed_fit(monkeypatch):
    # at the ends of the bias vector the fit fails; that is data,
    # not an error, and the sweep must keep going
    sweep = _make_dry_sweep()
    sweep._sg_current_amps_pp = 2.0e-6
    sweep._close_loop_norm = 1.0
    sweep._thermometer_bias_amps = 1.0e-5
    sweep._guess_params = [None]

    traces, _ = _make_synthetic_didv_traces(sweep, r0_true=0.1)
    sweep._daq = _make_fake_daq(traces)

    def exploding_fit(**kwargs):
        raise RuntimeError('fit did not converge')

    monkeypatch.setattr(gab_sweep_module, 'fit_didv_r0', exploding_fit)

    quality = sweep.measure_r0_quality(bias_index=0)

    assert quality['didv_fit_ok'] is False
    assert np.isnan(quality['r0'])
    assert np.isnan(quality['r0_err'])


def test_measure_r0_quality_flags_nonfinite_r0(monkeypatch):
    sweep = _make_dry_sweep()
    sweep._sg_current_amps_pp = 2.0e-6
    sweep._close_loop_norm = 1.0
    sweep._thermometer_bias_amps = 1.0e-5
    sweep._guess_params = [None]

    traces, _ = _make_synthetic_didv_traces(sweep, r0_true=0.1)
    sweep._daq = _make_fake_daq(traces)

    def negative_r0_fit(**kwargs):
        return {
            'r0': -0.5,
            'r0_err': 0.01,
            'i0': 1.0e-6,
            'p0': 1.0e-15,
            'fit_cost': 1.0,
            'fit_params': dict(),
            'fit_params_tuple': None,
            'cov': None,
        }

    monkeypatch.setattr(gab_sweep_module, 'fit_didv_r0', negative_r0_fit)

    quality = sweep.measure_r0_quality(bias_index=0)

    assert quality['didv_fit_ok'] is False
    assert np.isnan(quality['r0'])


def test_measure_r0_quality_reports_autocuts_fallback(monkeypatch):
    # autocuts rejecting everything is reported separately from
    # autocuts keeping everything
    sweep = _make_dry_sweep()
    sweep._close_loop_norm = 1.0
    sweep._thermometer_bias_amps = 1.0e-5
    sweep._guess_params = [None]

    traces, sgamp = _make_synthetic_didv_traces(sweep, r0_true=0.1)
    sweep._sg_current_amps_pp = sgamp
    sweep._daq = _make_fake_daq(traces)

    monkeypatch.setattr(
        gab_sweep_module.qp,
        'autocuts_didv',
        lambda traces, fs=None: np.zeros(traces.shape[0], dtype=bool)
    )

    quality = sweep.measure_r0_quality(bias_index=0)

    assert quality['autocuts_ok'] is False
    assert quality['nb_traces_kept'] == quality['nb_traces']


def test_good_fit_stores_guess_params_at_its_bias_index():
    sweep = _make_dry_sweep()
    sweep._close_loop_norm = 1.0
    sweep._thermometer_bias_amps = 1.0e-5
    sweep._guess_params = [None, None, None]

    traces, sgamp = _make_synthetic_didv_traces(sweep, r0_true=0.1)
    sweep._sg_current_amps_pp = sgamp
    sweep._daq = _make_fake_daq(traces)

    quality = sweep.measure_r0_quality(bias_index=1)

    assert quality['didv_fit_ok'] is True
    assert sweep._guess_params[1] is not None
    assert len(sweep._guess_params[1]) == 7
    # neighbours are untouched
    assert sweep._guess_params[0] is None
    assert sweep._guess_params[2] is None


def test_failed_fit_leaves_its_guess_params_untouched(monkeypatch):
    sweep = _make_dry_sweep()
    sweep._sg_current_amps_pp = 2.0e-6
    sweep._close_loop_norm = 1.0
    sweep._thermometer_bias_amps = 1.0e-5
    sentinel = (1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0)
    sweep._guess_params = [sentinel]

    traces, _ = _make_synthetic_didv_traces(sweep, r0_true=0.1)
    sweep._daq = _make_fake_daq(traces)

    def exploding_fit(**kwargs):
        raise RuntimeError('fit did not converge')

    monkeypatch.setattr(gab_sweep_module, 'fit_didv_r0', exploding_fit)

    sweep.measure_r0_quality(bias_index=0)

    assert sweep._guess_params[0] == sentinel


def test_stability_check_rejects_all_nan_readings(monkeypatch):
    # NaN > tolerance is False, so the old comparison reported five
    # garbage readings as stable. The timeout is deliberately huge so
    # that a False here can only come from rejecting the NaNs, never
    # from running out of time
    sweep = _make_dry_sweep()
    sweep._use_stability_check = True
    sweep._nb_events_stability = 1
    sweep._stability_timeout = 1.0e6
    sweep.measure_r0 = lambda nb_events=None: float('nan')

    monkeypatch.setattr(gab_sweep_module.time, 'sleep', lambda s: None)

    stability_ok, history = sweep.wait_for_stable_r0()

    assert stability_ok is False


def test_stability_check_rejects_mixed_good_and_nan(monkeypatch):
    sweep = _make_dry_sweep()
    sweep._use_stability_check = True
    sweep._nb_events_stability = 1
    sweep._stability_timeout = 1.0e6

    monkeypatch.setattr(gab_sweep_module.time, 'sleep', lambda s: None)

    readings = [0.1, float('nan'), 0.1, float('nan'), float('nan')]
    state = {'index': 0}

    def fake_measure(nb_events=None):
        value = readings[min(state['index'], len(readings) - 1)]
        state['index'] = state['index'] + 1
        return value

    sweep.measure_r0 = fake_measure

    stability_ok, history = sweep.wait_for_stable_r0()

    assert stability_ok is False


def test_stability_check_exits_early_on_a_run_of_nan(monkeypatch):
    # a run of non-finite reads must not loop to stability_timeout_s
    sweep = _make_dry_sweep()
    sweep._use_stability_check = True
    sweep._nb_events_stability = 1
    sweep._stability_timeout = 1.0e6
    sweep.measure_r0 = lambda nb_events=None: float('nan')

    monkeypatch.setattr(gab_sweep_module.time, 'sleep', lambda s: None)

    stability_ok, history = sweep.wait_for_stable_r0()

    assert stability_ok is False
    assert len(history) <= 10


def test_stability_check_still_accepts_agreeing_readings(monkeypatch):
    sweep = _make_dry_sweep()
    sweep._use_stability_check = True
    sweep._nb_events_stability = 1
    sweep._stability_timeout = 1.0e6
    sweep._r0_stability_tolerance_percent = 1.0
    sweep.measure_r0 = lambda nb_events=None: 0.1

    monkeypatch.setattr(gab_sweep_module.time, 'sleep', lambda s: None)

    stability_ok, history = sweep.wait_for_stable_r0()

    assert stability_ok is True


def _make_relock_instrument(device):
    # records the order of bias writes and relock calls so the
    # procedure can be asserted as a sequence
    def fake_set_bias(bias=None, unit=None, detector_channel=None):
        device['bias'] = float(bias)
        device['log'].append(('bias', float(bias)))
        return True

    def fake_get_bias(detector_channel=None, unit=None):
        return device['bias']

    def fake_relock(detector_channel=None, num_relock=2):
        device['log'].append(('relock', num_relock))

    class FakeInstrument:
        set_tes_bias = staticmethod(fake_set_bias)
        get_tes_bias = staticmethod(fake_get_bias)
        relock = staticmethod(fake_relock)

    return FakeInstrument()


def test_relock_drives_normal_then_returns_and_relocks_twice():
    sweep = _make_dry_sweep()
    device = {'bias': 20.0, 'log': list()}
    sweep._instrument = _make_relock_instrument(device)
    sweep._post_bias_wait = 0.0
    sweep._thermometer_initial_bias_ua = 20.0
    sweep._relock_bias_ua = 100.0
    sweep._relock_nb_cycles = 2

    sweep.relock_thermometer()

    assert device['log'] == [
        ('bias', 100.0),
        ('relock', 2),
        ('bias', 20.0),
        ('relock', 2),
    ]


def test_relock_refreshes_the_cached_thermometer_bias():
    # the board quantizes, so what comes back can differ from what
    # was asked for, and that value is ibias in every R0
    sweep = _make_dry_sweep()
    device = {'bias': 20.0, 'log': list()}
    instrument = _make_relock_instrument(device)

    def quantizing_set_bias(bias=None, unit=None, detector_channel=None):
        device['bias'] = float(bias) - 0.001
        device['log'].append(('bias', float(bias)))
        return True

    instrument.set_tes_bias = quantizing_set_bias
    sweep._instrument = instrument
    sweep._post_bias_wait = 0.0
    sweep._thermometer_initial_bias_ua = 20.0
    sweep._relock_bias_ua = 100.0
    sweep._relock_nb_cycles = 2
    sweep._thermometer_bias_amps = 20.0e-6

    sweep.relock_thermometer()

    assert sweep._get_thermometer_bias_amps() == pytest.approx(
        19.999e-6
    )


def test_transition_check_passes_inside_the_window():
    sweep = _make_dry_sweep()
    sweep._thermometer_rn = 1.0
    sweep._transition_check_frac_rn_min = 0.05
    sweep._transition_check_frac_rn_max = 0.95
    sweep.measure_r0_quality = lambda nb_events=None, bias_index=None: {
        'r0': 0.5, 'didv_fit_ok': True,
    }

    in_transition, quality = sweep.check_thermometer_in_transition()

    assert in_transition is True


@pytest.mark.parametrize('r0_value', [0.01, 0.99])
def test_transition_check_fails_outside_the_window(r0_value):
    sweep = _make_dry_sweep()
    sweep._thermometer_rn = 1.0
    sweep._transition_check_frac_rn_min = 0.05
    sweep._transition_check_frac_rn_max = 0.95
    sweep.measure_r0_quality = lambda nb_events=None, bias_index=None: {
        'r0': r0_value, 'didv_fit_ok': True,
    }

    in_transition, quality = sweep.check_thermometer_in_transition()

    assert in_transition is False


def test_transition_check_fails_on_a_failed_fit():
    sweep = _make_dry_sweep()
    sweep._thermometer_rn = 1.0
    sweep._transition_check_frac_rn_min = 0.05
    sweep._transition_check_frac_rn_max = 0.95
    sweep.measure_r0_quality = lambda nb_events=None, bias_index=None: {
        'r0': float('nan'), 'didv_fit_ok': False,
    }

    in_transition, quality = sweep.check_thermometer_in_transition()

    assert in_transition is False


def test_relock_and_verify_retries_then_continues(capsys):
    # exhausting the attempts warns loudly and keeps the sweep going
    sweep = _make_dry_sweep()
    device = {'bias': 20.0, 'log': list()}
    sweep._instrument = _make_relock_instrument(device)
    sweep._post_bias_wait = 0.0
    sweep._thermometer_initial_bias_ua = 20.0
    sweep._relock_bias_ua = 100.0
    sweep._relock_nb_cycles = 2
    sweep._relock_max_attempts = 3
    sweep.check_thermometer_in_transition = lambda: (
        False, {'r0': 0.001, 'didv_fit_ok': True}
    )

    result = sweep.relock_and_verify()

    assert result['relock_ok'] is False
    assert result['nb_attempts'] == 3
    assert 'WARNING' in capsys.readouterr().out


def test_relock_and_verify_stops_at_the_first_success():
    sweep = _make_dry_sweep()
    device = {'bias': 20.0, 'log': list()}
    sweep._instrument = _make_relock_instrument(device)
    sweep._post_bias_wait = 0.0
    sweep._thermometer_initial_bias_ua = 20.0
    sweep._relock_bias_ua = 100.0
    sweep._relock_nb_cycles = 2
    sweep._relock_max_attempts = 3
    sweep.check_thermometer_in_transition = lambda: (
        True, {'r0': 0.5, 'didv_fit_ok': True}
    )

    result = sweep.relock_and_verify()

    assert result['relock_ok'] is True
    assert result['nb_attempts'] == 1


def test_shutdown_restores_the_thermometer_bias():
    # a Ctrl-C inside the relock would otherwise strand the
    # thermometer at relock_bias_uA
    sweep = _make_dry_sweep()
    device = {'bias': 100.0, 'log': list()}
    sweep._instrument = _make_relock_instrument(device)
    sweep._thermometer_initial_bias_ua = 20.0
    sweep._heater_initial_bias_ua = 38.0
    sweep._daq = None
    sweep._output_path = None

    sweep.shutdown()

    assert device['bias'] == pytest.approx(20.0)


def test_relock_config_parses_from_example():
    sweep = _make_dry_sweep()

    assert sweep._relock_bias_ua == pytest.approx(100.0)
    assert sweep._relock_nb_cycles == 2
    assert sweep._relock_max_attempts == 3
    assert sweep._transition_check_frac_rn_min == pytest.approx(0.05)
    assert sweep._transition_check_frac_rn_max == pytest.approx(0.95)


class _FakeTemperatureSweep:
    @staticmethod
    def set_setpoint(temperature_mk=None):
        return None


def _make_bias_sweep_sweep(device):
    # a sweep wired to fakes, ready to run one temperature step
    sweep = _make_dry_sweep()
    sweep._instrument = _make_relock_instrument(device)
    sweep._post_bias_wait = 0.0
    sweep._thermometer_initial_bias_ua = 20.0
    sweep._bias_list = [300.0, 150.0, 38.0]
    sweep._guess_params = [None, None, None]
    sweep.wait_for_settled_r0 = lambda: (True, [])
    sweep.relock_and_verify = lambda: {
        'relock_ok': True, 'nb_attempts': 1, 'r0': 0.5,
    }
    sweep.measure_mc_temperature = lambda: {
        'temperature_k': 0.042,
        'temperature_err_k': 0.0001,
        'fit_ok': True,
        'nb_samples': 10,
        'samples': [0.042],
    }
    sweep.measure_r0_quality = (
        lambda nb_events=None, bias_index=None: {
            'r0': 0.1,
            'r0_err': 0.001,
            'i0': 1.0e-6,
            'p0': 1.0e-15,
            'fit_cost': 1.0,
            'fit_params': {'A': 1.0},
            'cov': [[1.0]],
            'nb_traces': 10,
            'nb_traces_kept': 10,
            'autocuts_ok': True,
            'didv_fit_ok': True,
        }
    )
    sweep.wait_for_temperature = lambda temperature_mk=None: (True, [])
    sweep._synced_temperature_sweep = lambda: _FakeTemperatureSweep()
    sweep._thermometer_bias_amps = 20.0e-6
    return sweep


def test_one_row_per_bias_point_in_descending_order(tmp_path):
    device = {'bias': 38.0, 'log': list()}
    sweep = _make_bias_sweep_sweep(device)
    sweep._csv_path = str(tmp_path / 'gab_sweep_data.csv')
    with open(sweep._csv_path, 'w', newline='') as f:
        csv.DictWriter(
            f, fieldnames=sweep.CSV_COLUMNS
        ).writeheader()

    rows = sweep.run_single_step(temperature_mk=42.0, step_index=0)

    assert len(rows) == 3
    assert [row['bias_index'] for row in rows] == [0, 1, 2]
    applied = [row['heater_tes_bias_requested_ua'] for row in rows]
    for index in range(1, len(applied)):
        assert applied[index] < applied[index - 1]


def test_step_ends_at_bias_min_and_next_starts_at_bias_max():
    device = {'bias': 38.0, 'log': list()}
    sweep = _make_bias_sweep_sweep(device)
    sweep._csv_path = None
    sweep._append_datapoint = lambda row_dict=None: None

    sweep.run_single_step(temperature_mk=42.0, step_index=0)

    bias_writes = [
        value for kind, value in device['log'] if kind == 'bias'
    ]
    assert bias_writes[0] == pytest.approx(300.0)
    assert bias_writes[-1] == pytest.approx(38.0)


def test_rows_record_the_applied_bias_not_the_requested():
    # the board snaps the request; R0 responds to what it applied
    device = {'bias': 38.0, 'log': list()}
    sweep = _make_bias_sweep_sweep(device)
    sweep._csv_path = None
    sweep._append_datapoint = lambda row_dict=None: None

    def quantizing_set_bias(bias=None, unit=None, detector_channel=None):
        device['bias'] = float(bias) - 0.5
        device['log'].append(('bias', float(bias)))
        return True

    sweep._instrument.set_tes_bias = quantizing_set_bias

    rows = sweep.run_single_step(temperature_mk=42.0, step_index=0)

    for row in rows:
        assert row['heater_tes_bias_ua'] == pytest.approx(
            row['heater_tes_bias_requested_ua'] - 0.5
        )


def test_every_csv_column_is_written_on_every_row():
    device = {'bias': 38.0, 'log': list()}
    sweep = _make_bias_sweep_sweep(device)
    sweep._csv_path = None
    sweep._append_datapoint = lambda row_dict=None: None

    rows = sweep.run_single_step(temperature_mk=42.0, step_index=0)

    for row in rows:
        assert set(row.keys()) == set(sweep.CSV_COLUMNS)


def test_no_relock_between_bias_points_of_one_temperature():
    device = {'bias': 38.0, 'log': list()}
    sweep = _make_bias_sweep_sweep(device)
    sweep._csv_path = None
    sweep._append_datapoint = lambda row_dict=None: None

    relock_calls = {'count': 0}

    def counting_relock():
        relock_calls['count'] = relock_calls['count'] + 1
        return {'relock_ok': True, 'nb_attempts': 1, 'r0': 0.5}

    sweep.relock_and_verify = counting_relock

    sweep.run_single_step(temperature_mk=42.0, step_index=0)

    assert relock_calls['count'] == 1


def test_heater_power_column_matches_the_applied_bias():
    device = {'bias': 38.0, 'log': list()}
    sweep = _make_bias_sweep_sweep(device)
    sweep._csv_path = None
    sweep._append_datapoint = lambda row_dict=None: None

    rows = sweep.run_single_step(temperature_mk=42.0, step_index=0)

    for row in rows:
        expected = heater_power_watts(
            bias_ua=row['heater_tes_bias_ua'],
            rshunt=sweep._heater_rshunt,
            rparasitic=sweep._heater_rparasitic,
            rnormal=sweep._heater_rn,
        )
        assert row['heater_tes_power_w'] == pytest.approx(expected)


def test_dead_temperature_warns_loudly(capsys):
    # every fit failing is not a statistic, it is a dead temperature
    device = {'bias': 38.0, 'log': list()}
    sweep = _make_bias_sweep_sweep(device)
    sweep._csv_path = None
    sweep._append_datapoint = lambda row_dict=None: None
    sweep.measure_r0_quality = (
        lambda nb_events=None, bias_index=None: {
            'r0': float('nan'),
            'r0_err': float('nan'),
            'i0': float('nan'),
            'p0': float('nan'),
            'fit_cost': float('nan'),
            'fit_params': None,
            'cov': None,
            'nb_traces': 10,
            'nb_traces_kept': 10,
            'autocuts_ok': True,
            'didv_fit_ok': False,
        }
    )

    sweep.run_single_step(temperature_mk=42.0, step_index=0)

    assert 'dead temperature' in capsys.readouterr().out


def test_dry_run_prints_the_bias_vector_and_point_count(capsys):
    sweep = _make_dry_sweep()

    sweep._print_dry_run()

    output = capsys.readouterr().out
    nb_points = (len(sweep._temperature_list_mk)
                 * len(sweep._bias_list))

    assert str(nb_points) in output
    assert f'{sweep._bias_list[0]:.6g}' in output
    assert f'{sweep._bias_list[-1]:.6g}' in output
