import os

import numpy as np
import pytest
import qetpy as qp

from pytesdaq.sequencer import gab_sweep as gab_sweep_module
from pytesdaq.sequencer.gab_sweep import (
    build_bias_list,
    heater_power_watts,
    compute_next_bias,
    fit_didv_r0,
    propagate_r0_error_to_bias,
)

# committed test fixture, so the suite runs on a fresh clone
SETUP_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'fixtures',
    'setup_test.ini'
)


def test_compute_next_bias_first_move_is_fixed_step_up():
    # with a single history point, physics says increase the heater bias
    result = compute_next_bias(
        bias_history=[0.0],
        r0_history=[100.0],
        r0_ref=120.0,
        bias_step_start=15.0,
    )
    assert result == 15.0


def test_compute_next_bias_secant_moves_toward_reference():
    # R0 rose from 100 to 110 when bias went 0 -> 15
    # slope is 10/15, reference 120 needs 10 more R0 units
    result = compute_next_bias(
        bias_history=[0.0, 15.0],
        r0_history=[100.0, 110.0],
        r0_ref=120.0,
        bias_step_start=15.0,
    )
    assert result == pytest.approx(30.0)


def test_compute_next_bias_clamps_large_secant_step():
    # very shallow slope would suggest a huge jump; clamp to 2x step
    result = compute_next_bias(
        bias_history=[0.0, 15.0],
        r0_history=[100.0, 100.001],
        r0_ref=120.0,
        bias_step_start=15.0,
    )
    assert result == pytest.approx(15.0 + 30.0)


def test_compute_next_bias_corrects_overshoot_downward():
    # R0 overshot the reference; secant must step back down
    result = compute_next_bias(
        bias_history=[15.0, 30.0],
        r0_history=[110.0, 130.0],
        r0_ref=120.0,
        bias_step_start=15.0,
    )
    assert result < 30.0
    assert result == pytest.approx(22.5)


def test_compute_next_bias_never_negative():
    result = compute_next_bias(
        bias_history=[5.0, 2.0],
        r0_history=[130.0, 125.0],
        r0_ref=50.0,
        bias_step_start=15.0,
    )
    assert result >= 0.0


def test_compute_next_bias_never_below_bias_min():
    # secant wants to go far below the minimum; the heater TES must
    # stay normal, so the result is floored at bias_min
    result = compute_next_bias(
        bias_history=[120.0, 110.0],
        r0_history=[130.0, 125.0],
        r0_ref=50.0,
        bias_step_start=15.0,
        bias_min=100.0,
    )
    assert result == 100.0


def test_compute_next_bias_first_move_respects_bias_min():
    # a first move from below the minimum lands at bias_min, not at
    # last_bias plus the fixed step
    result = compute_next_bias(
        bias_history=[0.0],
        r0_history=[100.0],
        r0_ref=120.0,
        bias_step_start=15.0,
        bias_min=100.0,
    )
    assert result == 100.0


def test_compute_next_bias_rejects_mismatched_history():
    with pytest.raises(ValueError):
        compute_next_bias(
            bias_history=[0.0, 15.0],
            r0_history=[100.0],
            r0_ref=120.0,
            bias_step_start=15.0,
        )


def test_compute_next_bias_repeated_bias_uses_last_distinct_pair():
    # regression: after clamping at the floor the last two biases are
    # equal; the slope must come from the last pair of distinct biases
    # instead of falling back to a blind step up, which made the loop
    # bounce between the floor and one step above it
    result = compute_next_bias(
        bias_history=[39.0, 38.0, 38.0],
        r0_history=[130.0, 129.0, 128.0],
        r0_ref=100.0,
        bias_step_start=1.0,
        bias_min=38.0,
    )
    assert result == 38.0


def test_compute_next_bias_grows_probe_when_response_below_noise():
    # R0 moved less than the noise floor, so the slope is meaningless;
    # the probe step doubles in the same direction until the response
    # is measurable
    result = compute_next_bias(
        bias_history=[38.0, 39.0],
        r0_history=[250.0, 250.5],
        r0_ref=260.0,
        bias_step_start=1.0,
        noise_floor=2.0,
    )
    assert result == pytest.approx(41.0)


def test_compute_next_bias_probe_growth_is_capped():
    # probe growth doubles the last move but never exceeds
    # 4x bias_step_start
    result = compute_next_bias(
        bias_history=[38.0, 42.0],
        r0_history=[250.0, 250.5],
        r0_ref=260.0,
        bias_step_start=1.0,
        noise_floor=2.0,
    )
    assert result == pytest.approx(46.0)


def test_compute_next_bias_field_regression_noise_secant_wrong_direction():
    # regression with the exact numbers from a run14 test sweep
    # (values were ADC baselines then, arbitrary units here): the
    # reading is 8 units below the reference and the true slope is
    # +20 units/uA, but the last two readings differ by only 0.5
    # units (noise), giving the old two-point secant a slope of
    # -1.3 units/uA; it then stepped DOWN 2 uA to 40.36 instead of
    # nudging the bias up. The fit over the full history must drive a
    # small step up: slope 17.3 units/uA, 8 units below reference.
    result = compute_next_bias(
        bias_history=[40.9795, 41.9563, 42.3633],
        r0_history=[316.569, 339.182, 338.655],
        r0_ref=346.651,
        bias_step_start=1.0,
        bias_min=37.9678,
        noise_floor=4.4,
    )
    assert result > 42.3633
    assert result == pytest.approx(42.826, abs=0.01)


def test_compute_next_bias_field_regression_holds_without_noise_floor():
    # same field case with the drift check disabled (noise floor 0):
    # the full-history fit still overrides the misleading last pair
    result = compute_next_bias(
        bias_history=[40.9795, 41.9563, 42.3633],
        r0_history=[316.569, 339.182, 338.655],
        r0_ref=346.651,
        bias_step_start=1.0,
        bias_min=37.9678,
    )
    assert result > 42.3633
    assert result == pytest.approx(42.826, abs=0.01)


def test_compute_next_bias_fit_wins_over_probe_when_history_has_signal():
    # regression with the exact numbers from a run14 sweep with a
    # large drift noise floor (21 units): the +3 uA first move gave a
    # real 60 unit response, but the old last-pair guard compared 60
    # against 3x21 = 63 and doubled the probe to +6 uA from a reading
    # only 2 percent below target. The history plainly holds an
    # 18 units/uA slope, so the fit must drive a small step up.
    result = compute_next_bias(
        bias_history=[43.5029, 46.5147, 46.5147],
        r0_history=[404.334, 464.365, 454.837],
        r0_ref=464.316,
        bias_step_start=3.0,
        bias_min=37.9678,
        noise_floor=21.0,
    )
    assert 46.5147 < result < 48.0
    assert result == pytest.approx(47.03, abs=0.01)


def test_compute_next_bias_fit_overrides_misleading_last_pair():
    # the last-pair secant slope is negative while the least squares
    # fit over the full history is clearly positive: the fit wins and
    # the step goes toward the reference per the fit
    result = compute_next_bias(
        bias_history=[0.0, 10.0, 20.0],
        r0_history=[100.0, 120.0, 115.0],
        r0_ref=130.0,
        bias_step_start=15.0,
    )
    # fit slope 0.75 units/uA, 15 units below reference: step +20
    assert result == pytest.approx(40.0)


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


def test_propagate_r0_error_to_bias_linear():
    # linear model: a 10 percent R0 uncertainty is a 10 percent bias
    # uncertainty, so 0.015 on 0.15 R0 gives 20 uA on a 200 uA bias
    result = propagate_r0_error_to_bias(
        r0=0.15,
        r0_err=0.015,
        heater_bias=200.0,
    )
    assert result == pytest.approx(20.0)


def test_propagate_r0_error_to_bias_scales_with_fraction():
    # a 1 percent R0 uncertainty gives a 1 percent bias uncertainty
    result = propagate_r0_error_to_bias(
        r0=0.2,
        r0_err=0.002,
        heater_bias=350.0,
    )
    assert result == pytest.approx(3.5)


def test_propagate_r0_error_to_bias_zero_r0_is_safe():
    # a zero R0 has no defined fractional uncertainty, return zero
    # instead of dividing by zero
    result = propagate_r0_error_to_bias(
        r0=0.0,
        r0_err=0.01,
        heater_bias=200.0,
    )
    assert result == 0.0


def test_propagate_r0_error_to_bias_uses_magnitudes():
    # sign of the bias must not flip the (positive) uncertainty
    result = propagate_r0_error_to_bias(
        r0=0.15,
        r0_err=0.015,
        heater_bias=-200.0,
    )
    assert result == pytest.approx(20.0)


def _make_quantizing_instrument(device, quantum=0.001):
    # controller that cannot hold the requested bias exactly and
    # always lands just below it, like the real FEB
    def fake_set_bias(bias, unit=None, detector_channel=None):
        device['bias'] = float(bias) - quantum
        return True

    def fake_get_bias(detector_channel=None, unit=None):
        return device['bias']

    class FakeInstrument:
        set_tes_bias = staticmethod(fake_set_bias)
        get_tes_bias = staticmethod(fake_get_bias)

    return FakeInstrument()


def test_bias_floor_uses_read_back_value():
    # the floor is what the controller landed on, not what we asked for
    sweep = _make_dry_sweep()
    device = {'bias': 0.0}
    sweep._instrument = _make_quantizing_instrument(device)
    sweep._post_bias_wait = 0.0

    # before any set, the floor is the configured request
    assert sweep._get_bias_floor() == sweep._bias_min

    sweep._set_heater_bias_min()

    assert sweep._bias_min_actual == pytest.approx(
        sweep._bias_min - 0.001
    )
    assert sweep._get_bias_floor() == sweep._bias_min_actual
    assert sweep._get_bias_floor() < sweep._bias_min


def test_quantized_bias_does_not_retrigger_floor_warning(capsys):
    # regression: setting bias_min then entering feedback must not warn
    # just because the controller rounded the bias down
    sweep = _make_dry_sweep()
    device = {'bias': 0.0}
    sweep._instrument = _make_quantizing_instrument(device)
    sweep._post_bias_wait = 0.0
    sweep.measure_r0 = lambda nb_events=None: 250.0
    sweep.wait_for_settled_r0 = lambda: (True, [])
    sweep._r0_ref = 250.0

    sweep._set_heater_bias_min()
    capsys.readouterr()

    result = sweep._run_feedback()

    output = capsys.readouterr().out
    assert 'below the bias floor' not in output
    assert result['bias_history'][0] == pytest.approx(
        sweep._bias_min - 0.001
    )


def test_bias_genuinely_below_floor_still_warns(capsys):
    # a real excursion below the floor must still be caught and fixed
    sweep = _make_dry_sweep()
    device = {'bias': 0.0}
    sweep._instrument = _make_quantizing_instrument(device)
    sweep._post_bias_wait = 0.0
    sweep.measure_r0 = lambda nb_events=None: 250.0
    sweep.wait_for_settled_r0 = lambda: (True, [])
    sweep._r0_ref = 250.0

    sweep._set_heater_bias_min()

    # heater drops far below the floor, e.g. set by hand
    device['bias'] = 1.0
    capsys.readouterr()

    result = sweep._run_feedback()

    output = capsys.readouterr().out
    assert 'below the bias floor' in output
    assert result['bias_history'][0] >= sweep._get_bias_floor()


def test_bias_history_records_applied_not_requested_bias():
    # the secant update must be fed the bias the controller actually
    # applied, so bias_history holds read back values throughout
    sweep = _make_dry_sweep()
    device = {'bias': 0.0}
    sweep._instrument = _make_quantizing_instrument(device, quantum=0.001)
    sweep._post_bias_wait = 0.0
    sweep.wait_for_settled_r0 = lambda: (True, [])

    def fake_r0(nb_events=None):
        # R0 responds to the bias actually applied
        return 100.0 + device['bias']

    sweep.measure_r0 = fake_r0
    sweep._r0_ref = 250.0

    sweep._set_heater_bias_min()
    result = sweep._run_feedback()

    assert len(result['bias_history']) > 1

    # each R0 must be consistent with the bias entry it is paired
    # with: recording the requested bias instead would offset every
    # pair by the quantum and skew the secant slope
    for bias, r0 in zip(result['bias_history'],
                        result['r0_history']):
        assert r0 == pytest.approx(100.0 + bias, abs=1e-9)


def test_run_feedback_converges_with_fake_device():
    # fake linear device: R0 responds linearly to heater bias; the
    # device starts at bias_min (100 uA in the example config)
    sweep = _make_dry_sweep()

    device = {'bias': 100.0}
    r0_ref = 250.0

    def fake_r0(nb_events=None):
        # R0 rises 1 unit per uA of heater bias from 100
        return 100.0 + device['bias']

    def fake_set_bias(bias, unit=None, detector_channel=None):
        device['bias'] = float(bias)
        return True

    def fake_get_bias(detector_channel=None, unit=None):
        return device['bias']

    class FakeInstrument:
        set_tes_bias = staticmethod(fake_set_bias)
        get_tes_bias = staticmethod(fake_get_bias)

    sweep._instrument = FakeInstrument()
    sweep.measure_r0 = fake_r0
    sweep.wait_for_settled_r0 = lambda: (True, [])
    sweep._r0_ref = r0_ref
    sweep._post_bias_wait = 0.0

    result = sweep._run_feedback()

    assert result['converged'] is True
    assert result['cap_reached'] is False
    final_r0 = result['r0_history'][-1]
    offset = abs(final_r0 - r0_ref) / r0_ref
    assert offset * 100.0 <= sweep._r0_stability_tolerance_percent


def test_run_feedback_stops_at_bias_cap():
    # device too weak: R0 barely responds, cap must end feedback; the
    # device starts below bias_min so the feedback must first raise
    # the bias to keep the heater TES normal
    sweep = _make_dry_sweep()

    device = {'bias': 0.0}

    def fake_r0(nb_events=None):
        return 100.0 + (0.001 * device['bias'])

    def fake_set_bias(bias, unit=None, detector_channel=None):
        device['bias'] = float(bias)
        return True

    def fake_get_bias(detector_channel=None, unit=None):
        return device['bias']

    class FakeInstrument:
        set_tes_bias = staticmethod(fake_set_bias)
        get_tes_bias = staticmethod(fake_get_bias)

    sweep._instrument = FakeInstrument()
    sweep.measure_r0 = fake_r0
    sweep.wait_for_settled_r0 = lambda: (True, [])
    sweep._r0_ref = 150.0
    sweep._post_bias_wait = 0.0

    result = sweep._run_feedback()

    assert result['cap_reached'] is True
    assert result['converged'] is False
    assert result['bias_history'][0] == sweep._bias_min
    assert result['bias_history'][-1] == sweep._bias_max
    assert min(result['bias_history']) >= sweep._bias_min


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


def _make_linear_device_sweep(device=None, r0_offset=100.0):
    # fake linear device shared by the feedback tests: R0 responds
    # 1 unit per uA of heater bias
    sweep = _make_dry_sweep()

    def fake_r0(nb_events=None):
        return r0_offset + device['bias']

    def fake_set_bias(bias, unit=None, detector_channel=None):
        device['bias'] = float(bias)
        return True

    def fake_get_bias(detector_channel=None, unit=None):
        return device['bias']

    class FakeInstrument:
        set_tes_bias = staticmethod(fake_set_bias)
        get_tes_bias = staticmethod(fake_get_bias)

    sweep._instrument = FakeInstrument()
    sweep.measure_r0 = fake_r0
    sweep.wait_for_settled_r0 = lambda: (True, [])
    sweep._post_bias_wait = 0.0

    return sweep


def test_run_feedback_uses_provided_initial_r0():
    # run_single_step already measured the settled R0, so the
    # feedback must start from it instead of silently measuring a
    # second one it never prints
    device = {'bias': 100.0}
    sweep = _make_linear_device_sweep(device=device)
    sweep._r0_ref = 250.0

    nb_calls = {'count': 0}
    original_measure = sweep.measure_r0

    def counting_measure(nb_events=None):
        nb_calls['count'] = nb_calls['count'] + 1
        return original_measure(nb_events=nb_events)

    sweep.measure_r0 = counting_measure

    result = sweep._run_feedback(initial_r0=200.0)

    assert result['r0_history'][0] == 200.0
    # one history entry per measurement plus the provided one
    assert len(result['r0_history']) == nb_calls['count'] + 1


def test_run_feedback_requires_confirmation_reading():
    # a single in-tolerance reading is not convergence: it must be
    # confirmed by a second reading at the same bias
    device = {'bias': 100.0}
    sweep = _make_linear_device_sweep(device=device)
    sweep._r0_ref = 250.0

    result = sweep._run_feedback()

    assert result['converged'] is True
    assert result['bias_history'][-1] == result['bias_history'][-2]

    tolerance = sweep._r0_stability_tolerance_percent
    for r0 in result['r0_history'][-2:]:
        offset = abs(r0 - 250.0) / 250.0 * 100.0
        assert offset <= tolerance


def test_run_feedback_confirmation_rejects_drifting_r0():
    # the first reading is in tolerance by luck, the confirmation
    # reading drifts out: the feedback must keep going instead of
    # accepting the lucky reading
    sweep = _make_dry_sweep()

    device = {'bias': 100.0}

    def fake_set_bias(bias, unit=None, detector_channel=None):
        device['bias'] = float(bias)
        return True

    def fake_get_bias(detector_channel=None, unit=None):
        return device['bias']

    class FakeInstrument:
        set_tes_bias = staticmethod(fake_set_bias)
        get_tes_bias = staticmethod(fake_get_bias)

    r0_sequence = [250.0, 280.0, 250.0, 250.0]

    def fake_r0(nb_events=None):
        if len(r0_sequence) > 0:
            return r0_sequence.pop(0)
        return 250.0

    sweep._instrument = FakeInstrument()
    sweep.measure_r0 = fake_r0
    sweep.wait_for_settled_r0 = lambda: (True, [])
    sweep._post_bias_wait = 0.0
    sweep._r0_ref = 250.0

    result = sweep._run_feedback()

    assert result['converged'] is True
    # the failed confirmation forced at least one real bias move
    assert len(result['bias_history']) > 2
    assert result['bias_history'][2] != result['bias_history'][0]


def test_run_feedback_confirmation_near_miss_converges_on_mean():
    # field case: first reading dead on the reference, confirmation
    # reading a hair outside tolerance (drift); the mean of the two
    # readings is well within tolerance, so the point is accepted
    # instead of restarting the feedback from a good bias
    sweep = _make_dry_sweep()

    device = {'bias': 100.0}

    def fake_set_bias(bias, unit=None, detector_channel=None):
        device['bias'] = float(bias)
        return True

    def fake_get_bias(detector_channel=None, unit=None):
        return device['bias']

    class FakeInstrument:
        set_tes_bias = staticmethod(fake_set_bias)
        get_tes_bias = staticmethod(fake_get_bias)

    # reference 250, tolerance 2 percent (band 245 to 255):
    # confirmation lands at 244.8 (-2.08 percent), mean 247.4
    r0_sequence = [250.0, 244.8]

    def fake_r0(nb_events=None):
        if len(r0_sequence) > 0:
            return r0_sequence.pop(0)
        return 250.0

    sweep._instrument = FakeInstrument()
    sweep.measure_r0 = fake_r0
    sweep.wait_for_settled_r0 = lambda: (True, [])
    sweep._post_bias_wait = 0.0
    sweep._r0_ref = 250.0
    sweep._r0_stability_tolerance_percent = 2.0

    result = sweep._run_feedback()

    assert result['converged'] is True
    # accepted at the confirmation, no further bias moves
    assert len(result['bias_history']) == 2
    assert result['bias_history'][0] == result['bias_history'][1]


def test_run_feedback_confirmation_near_miss_rejected_when_mean_out():
    # both readings lean the same way and their mean is outside
    # tolerance: the near miss must not be accepted
    sweep = _make_dry_sweep()

    device = {'bias': 100.0}

    def fake_set_bias(bias, unit=None, detector_channel=None):
        device['bias'] = float(bias)
        return True

    def fake_get_bias(detector_channel=None, unit=None):
        return device['bias']

    class FakeInstrument:
        set_tes_bias = staticmethod(fake_set_bias)
        get_tes_bias = staticmethod(fake_get_bias)

    # reference 250, tolerance 2 percent: first reading in tolerance
    # at -1.92 percent, confirmation at -3.8 percent, mean -2.86
    # percent is out, feedback must continue
    r0_sequence = [245.2, 240.5]

    def fake_r0(nb_events=None):
        if len(r0_sequence) > 0:
            return r0_sequence.pop(0)
        return 250.0

    sweep._instrument = FakeInstrument()
    sweep.measure_r0 = fake_r0
    sweep.wait_for_settled_r0 = lambda: (True, [])
    sweep._post_bias_wait = 0.0
    sweep._r0_ref = 250.0

    result = sweep._run_feedback()

    assert result['converged'] is True
    # the near miss was rejected, at least one real bias move followed
    assert len(result['bias_history']) > 2


def test_run_feedback_detects_pinned_at_floor():
    # R0 sits far above the reference and rises with bias: the target
    # needs a bias below the floor, which is not allowed, so the
    # feedback must flag the point instead of looping on it
    device = {'bias': 100.0}
    sweep = _make_linear_device_sweep(device=device, r0_offset=300.0)
    sweep._r0_ref = 250.0

    result = sweep._run_feedback()

    assert result['pinned_at_floor'] is True
    assert result['converged'] is False
    assert result['bias_history'][-1] == pytest.approx(
        sweep._get_bias_floor()
    )


def test_drift_check_parameters_parse_from_example():
    # the drift check keys are optional in the config
    sweep = _make_dry_sweep()

    assert sweep._drift_check_nb_measurements == 3
    assert sweep._drift_check_wait_time == 5.0
    assert sweep._r0_noise_floor == 0.0


def test_run_drift_check_measures_scatter(monkeypatch):
    # the drift check repeats the R0 measurement at fixed conditions
    # and stores the scatter as the feedback noise floor
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
        })

    def fake_quality(nb_events=None):
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
    assert sweep._r0_noise_floor == pytest.approx(np.std(r0_values))
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
        })

    def fake_quality(nb_events=None):
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
    assert sweep._r0_noise_floor == 0.0


def test_r0_columns_recorded_in_csv():
    from pytesdaq.sequencer import GabSweep

    assert 'pinned_at_floor' in GabSweep.CSV_COLUMNS
    assert 'thermometer_r0_ohms' in GabSweep.CSV_COLUMNS
    assert 'thermometer_r0_err_ohms' in GabSweep.CSV_COLUMNS
    assert 'mc_temperature_err_mk' in GabSweep.CSV_COLUMNS
    assert 'heater_tes_bias_err_ua' in GabSweep.CSV_COLUMNS


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


def test_run_single_step_writes_every_row_key_to_csv(tmp_path,
                                                     monkeypatch):
    # the recorded row must be writable through csv.DictWriter, which
    # rejects any key missing from CSV_COLUMNS; running a real step
    # catches a row key added without updating the column list
    import csv as csv_module
    from pytesdaq.sequencer import GabSweep

    sweep = _make_dry_sweep()

    device = {'bias': 38.0}

    class FakeInstrument:
        @staticmethod
        def set_temperature(temperature, **kwargs):
            return True

        @staticmethod
        def get_temperature(channel_name=None, instrument_name=None):
            return 0.042

        @staticmethod
        def set_tes_bias(bias, unit=None, detector_channel=None):
            device['bias'] = float(bias)
            return True

        @staticmethod
        def get_tes_bias(detector_channel=None, unit=None):
            return device['bias']

    sweep._instrument = FakeInstrument()
    sweep._post_bias_wait = 0.0
    # timing now lives on the shared temperature sweep, not on
    # GabSweep itself
    sweep._temperature_sweep._sampling_time_s = 0.0
    sweep._temperature_sweep._stable_time_s = 0.0
    sweep._temperature_sweep._poll_interval_s = 0.0
    sweep.wait_for_settled_r0 = lambda: (True, [])
    sweep.measure_r0_quality = lambda nb_events=None: {
        'r0': 0.150,
        'r0_err': 0.001,
        'i0': 1.0e-6,
        'p0': 1.0e-13,
        'fit_cost': 1.0,
        'nb_traces': 200,
        'nb_traces_kept': 180,
    }

    monkeypatch.setattr(gab_sweep_module.time, 'sleep', lambda s: None)

    csv_path = tmp_path / 'gab_sweep_data.csv'
    with open(csv_path, 'w', newline='') as f:
        writer = csv_module.DictWriter(f, fieldnames=GabSweep.CSV_COLUMNS)
        writer.writeheader()
    sweep._csv_path = str(csv_path)

    sweep.run_single_step(temperature_mk=42.0, step_index=0)

    with open(csv_path, 'r', newline='') as f:
        rows = list(csv_module.DictReader(f))

    assert len(rows) == 1
    assert rows[0]['temperature_ok'] == 'True'
    assert rows[0]['step'] == '0'
    # no column left unwritten
    assert all(value != '' for value in rows[0].values())


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
