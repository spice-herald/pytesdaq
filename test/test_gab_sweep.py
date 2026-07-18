import numpy as np
import pytest
import qetpy as qp

from pytesdaq.sequencer import gab_sweep as gab_sweep_module
from pytesdaq.sequencer.gab_sweep import (
    build_temperature_list,
    compute_next_bias,
    fit_didv_r0,
    fit_temperature_gaussian,
    propagate_r0_error_to_bias,
)


def test_build_temperature_list_from_vect():
    config_dict = {
        'use_temperature_vect': True,
        'temperature_vect_mk': ['42', 41.0, '40.5', '38'],
    }
    result = build_temperature_list(config_dict=config_dict)
    assert result == [42.0, 41.0, 40.5, 38.0]


def test_build_temperature_list_from_single_value_vect():
    # get_sequencer_setup collapses single-element lists to a scalar
    config_dict = {
        'use_temperature_vect': True,
        'temperature_vect_mk': 42.0,
    }
    result = build_temperature_list(config_dict=config_dict)
    assert result == [42.0]


def test_build_temperature_list_from_start_stop_step():
    config_dict = {
        'use_temperature_vect': False,
        'temperature_start_mk': '42',
        'temperature_stop_mk': '38',
        'temperature_step_mk': '1',
    }
    result = build_temperature_list(config_dict=config_dict)
    assert result == [42.0, 41.0, 40.0, 39.0, 38.0]


def test_build_temperature_list_rejects_ascending_vect():
    config_dict = {
        'use_temperature_vect': True,
        'temperature_vect_mk': [38, 40, 42],
    }
    with pytest.raises(ValueError):
        build_temperature_list(config_dict=config_dict)


def test_build_temperature_list_rejects_zero_step():
    config_dict = {
        'use_temperature_vect': False,
        'temperature_start_mk': 42,
        'temperature_stop_mk': 38,
        'temperature_step_mk': 0,
    }
    with pytest.raises(ValueError):
        build_temperature_list(config_dict=config_dict)


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
        setup_file='pytesdaq/config/setup.ini',
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
            setup_file='pytesdaq/config/setup.ini',
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
            setup_file='pytesdaq/config/setup.ini',
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
    assert sweep._rshunt == 0.005
    assert sweep._rparasitic == 0.00176

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
            setup_file='pytesdaq/config/setup.ini',
            dry_run=True,
        )


def _make_synthetic_didv_traces(sweep, r0_true, nb_traces=10,
                                noise_amps=1.0e-8, seed=42):
    # synthetic 2-pole square wave response with a known R0: in the
    # infinite loop gain approximation dVdI(0) = A + B = rl - r0
    # tau1 is kept well below the signal generator period so plenty
    # of harmonics constrain the zero frequency dVdI (a fall time
    # comparable to the period makes R0 poorly determined)
    rl = sweep._rshunt + sweep._rparasitic
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
        rsh=sweep._rshunt,
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
        rsh=sweep._rshunt,
        rp=sweep._rparasitic,
        ibias=1.0e-4,
        r0_guess=0.15,
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

    quality = sweep.measure_r0_quality()

    assert quality['nb_traces'] == nb_traces
    assert 0 < quality['nb_traces_kept'] <= nb_traces
    assert quality['r0'] == pytest.approx(r0_true, rel=0.05)
    assert quality['r0_err'] >= 0.0

    # a good fit seeds the next fit's guess
    assert sweep._r0_guess == pytest.approx(quality['r0'])

    # measure_r0 stays a thin float-returning wrapper
    assert sweep.measure_r0() == pytest.approx(r0_true, rel=0.05)


def test_measure_r0_requires_signal_generator_setup():
    # measuring before the square wave is on would silently fit noise
    sweep = _make_dry_sweep()

    with pytest.raises(ValueError, match='signal generator'):
        sweep.measure_r0_quality()


def test_fit_temperature_gaussian_recovers_mean_and_sigma():
    # a Gaussian histogram fit on normal samples must recover the
    # distribution mean and sigma
    rng = np.random.default_rng(seed=7)
    true_mean = 0.040
    true_sigma = 0.0002
    samples = rng.normal(true_mean, true_sigma, size=500)

    result = fit_temperature_gaussian(samples=samples)

    assert result['fit_ok'] is True
    assert result['nb_samples'] == 500
    assert result['mean'] == pytest.approx(true_mean, abs=true_sigma / 4)
    assert result['sigma'] == pytest.approx(true_sigma, rel=0.3)


def test_fit_temperature_gaussian_falls_back_on_identical_samples():
    # a quantizing controller can return the same reading every time:
    # no histogram fit is possible, sample statistics are used
    samples = [0.040] * 50

    result = fit_temperature_gaussian(samples=samples)

    assert result['fit_ok'] is False
    assert result['mean'] == pytest.approx(0.040)
    assert result['sigma'] == 0.0


def test_fit_temperature_gaussian_falls_back_on_few_samples():
    # too few samples for a histogram: sample statistics are used
    samples = [0.040, 0.041, 0.039]

    result = fit_temperature_gaussian(samples=samples)

    assert result['fit_ok'] is False
    assert result['mean'] == pytest.approx(np.mean(samples))
    assert result['sigma'] == pytest.approx(np.std(samples))


def test_fit_temperature_gaussian_rejects_empty_samples():
    with pytest.raises(ValueError):
        fit_temperature_gaussian(samples=[])


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


def test_measure_mc_temperature_samples_over_window(monkeypatch):
    # the measurement keeps sampling until the window closes and
    # reports the Gaussian mean and sigma of the readings
    sweep = _make_dry_sweep()
    sweep._temperature_sampling_time_s = 1.0

    rng = np.random.default_rng(seed=11)
    readings = list(rng.normal(0.040, 0.0002, size=200))

    class FakeInstrument:
        @staticmethod
        def get_temperature(channel_name=None, instrument_name=None):
            return readings.pop(0)

    sweep._instrument = FakeInstrument()

    # fake clock: each call advances 10 ms, so a 1 s window takes
    # 100 samples deterministically
    clock = {'now': 0.0}

    def fake_time():
        clock['now'] = clock['now'] + 0.010
        return clock['now']

    monkeypatch.setattr(gab_sweep_module.time, 'time', fake_time)

    measurement = sweep.measure_mc_temperature()

    assert measurement['nb_samples'] == pytest.approx(100, abs=1)
    assert measurement['temperature_k'] == pytest.approx(0.040, abs=0.0001)
    assert measurement['temperature_err_k'] == pytest.approx(
        0.0002, rel=0.5
    )
    assert len(measurement['samples']) == measurement['nb_samples']


def test_measure_mc_temperature_zero_window_takes_one_sample(monkeypatch):
    # a zero sampling window still returns a single reading with the
    # fallback statistics
    sweep = _make_dry_sweep()
    sweep._temperature_sampling_time_s = 0.0

    class FakeInstrument:
        @staticmethod
        def get_temperature(channel_name=None, instrument_name=None):
            return 0.040

    sweep._instrument = FakeInstrument()

    measurement = sweep.measure_mc_temperature()

    assert measurement['nb_samples'] == 1
    assert measurement['temperature_k'] == pytest.approx(0.040)
    assert measurement['temperature_err_k'] == 0.0
    assert measurement['fit_ok'] is False


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
    assert offset * 100.0 <= sweep._r0_tolerance_percent


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

    def fake_set_bias(bias, unit=None, detector_channel=None):
        device['bias'] = float(bias)
        return True

    def fake_set_temperature(value, **kwargs):
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
            return True

    sweep._instrument = FakeInstrument()
    sweep._daq = None

    sweep.shutdown()

    assert ('onoff', 'off') in calls
    assert ('connect', False) in calls


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

    tolerance = sweep._r0_tolerance_percent
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
    sweep._r0_tolerance_percent = 2.0

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

    def fake_set_bias(bias, unit=None, detector_channel=None):
        device['bias'] = float(bias)
        return True

    def fake_set_temperature(value, **kwargs):
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


def _make_temperature_sweep(readings, monkeypatch):
    # dry-run sweep whose thermometer returns the given readings [K],
    # with sleep disabled and a fake clock advancing 1 s per reading
    sweep = _make_dry_sweep()
    sweep._temperature_poll_interval_s = 1.0
    sweep._temperature_stable_time_s = 3.0
    sweep._temperature_max_wait_time_s = 100.0
    sweep._temperature_tolerance = 0.02

    values = list(readings)

    class FakeInstrument:
        @staticmethod
        def get_temperature(channel_name=None, instrument_name=None):
            if len(values) > 1:
                return values.pop(0)
            return values[0]

    sweep._instrument = FakeInstrument()

    clock = {'now': 0.0}

    def fake_time():
        return clock['now']

    def fake_sleep(seconds):
        clock['now'] = clock['now'] + seconds

    monkeypatch.setattr(gab_sweep_module.time, 'time', fake_time)
    monkeypatch.setattr(gab_sweep_module.time, 'sleep', fake_sleep)

    return sweep


def test_wait_for_temperature_waits_out_a_slow_approach(monkeypatch):
    # the fridge coasts down for several polls before arriving; the
    # wait must not return until the setpoint is reached and held
    readings = [0.060, 0.055, 0.050, 0.045, 0.0401]
    sweep = _make_temperature_sweep(readings, monkeypatch)

    temperature_ok, history = sweep.wait_for_temperature(
        temperature_mk=40.0
    )

    assert temperature_ok is True

    # the four out-of-tolerance readings, then the hold window
    assert history[:4] == pytest.approx([60.0, 55.0, 50.0, 45.0])
    assert history[-1] == pytest.approx(40.1)


def test_wait_for_temperature_restarts_hold_on_excursion(monkeypatch):
    # a reading that drifts back out of tolerance restarts the hold,
    # so a brief touch of the setpoint is not enough
    readings = [0.0401, 0.050, 0.0401]
    sweep = _make_temperature_sweep(readings, monkeypatch)

    temperature_ok, history = sweep.wait_for_temperature(
        temperature_mk=40.0
    )

    assert temperature_ok is True

    # the excursion at 50 mK must appear before the accepted hold
    assert pytest.approx(50.0) in history
    assert history.index(pytest.approx(50.0)) < len(history) - 1


def test_wait_for_temperature_times_out_when_setpoint_unreachable(
        monkeypatch):
    # a fridge that never gets there must time out and report failure
    # rather than silently letting the sweep measure
    readings = [0.060]
    sweep = _make_temperature_sweep(readings, monkeypatch)

    temperature_ok, history = sweep.wait_for_temperature(
        temperature_mk=40.0
    )

    assert temperature_ok is False
    assert len(history) > 1


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
    sweep._temperature_sampling_time_s = 0.0
    sweep._temperature_stable_time_s = 0.0
    sweep._temperature_poll_interval_s = 0.0
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
