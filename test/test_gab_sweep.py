import numpy as np
import pytest

from pytesdaq.sequencer import gab_sweep as gab_sweep_module
from pytesdaq.sequencer.gab_sweep import (
    build_temperature_list,
    compute_next_bias,
)


def test_build_temperature_list_from_vect():
    config_dict = {
        'use_temperature_vect': True,
        'temperature_vect': ['42', 41.0, '40.5', '38'],
    }
    result = build_temperature_list(config_dict=config_dict)
    assert result == [42.0, 41.0, 40.5, 38.0]


def test_build_temperature_list_from_single_value_vect():
    # get_sequencer_setup collapses single-element lists to a scalar
    config_dict = {
        'use_temperature_vect': True,
        'temperature_vect': 42.0,
    }
    result = build_temperature_list(config_dict=config_dict)
    assert result == [42.0]


def test_build_temperature_list_from_start_stop_step():
    config_dict = {
        'use_temperature_vect': False,
        'temperature_start': '42',
        'temperature_stop': '38',
        'temperature_step': '1',
    }
    result = build_temperature_list(config_dict=config_dict)
    assert result == [42.0, 41.0, 40.0, 39.0, 38.0]


def test_build_temperature_list_rejects_ascending_vect():
    config_dict = {
        'use_temperature_vect': True,
        'temperature_vect': [38, 40, 42],
    }
    with pytest.raises(ValueError):
        build_temperature_list(config_dict=config_dict)


def test_build_temperature_list_rejects_zero_step():
    config_dict = {
        'use_temperature_vect': False,
        'temperature_start': 42,
        'temperature_stop': 38,
        'temperature_step': 0,
    }
    with pytest.raises(ValueError):
        build_temperature_list(config_dict=config_dict)


def test_compute_next_bias_first_move_is_fixed_step_up():
    # with a single history point, physics says increase the heater bias
    result = compute_next_bias(
        bias_history=[0.0],
        baseline_history=[100.0],
        baseline_ref=120.0,
        bias_step_start=15.0,
    )
    assert result == 15.0


def test_compute_next_bias_secant_moves_toward_reference():
    # baseline rose from 100 to 110 when bias went 0 -> 15
    # slope is 10/15, reference 120 needs 10 more baseline units
    result = compute_next_bias(
        bias_history=[0.0, 15.0],
        baseline_history=[100.0, 110.0],
        baseline_ref=120.0,
        bias_step_start=15.0,
    )
    assert result == pytest.approx(30.0)


def test_compute_next_bias_clamps_large_secant_step():
    # very shallow slope would suggest a huge jump; clamp to 2x step
    result = compute_next_bias(
        bias_history=[0.0, 15.0],
        baseline_history=[100.0, 100.001],
        baseline_ref=120.0,
        bias_step_start=15.0,
    )
    assert result == pytest.approx(15.0 + 30.0)


def test_compute_next_bias_corrects_overshoot_downward():
    # baseline overshot the reference; secant must step back down
    result = compute_next_bias(
        bias_history=[15.0, 30.0],
        baseline_history=[110.0, 130.0],
        baseline_ref=120.0,
        bias_step_start=15.0,
    )
    assert result < 30.0
    assert result == pytest.approx(22.5)


def test_compute_next_bias_never_negative():
    result = compute_next_bias(
        bias_history=[5.0, 2.0],
        baseline_history=[130.0, 125.0],
        baseline_ref=50.0,
        bias_step_start=15.0,
    )
    assert result >= 0.0


def test_compute_next_bias_never_below_bias_min():
    # secant wants to go far below the minimum; the heater TES must
    # stay normal, so the result is floored at bias_min
    result = compute_next_bias(
        bias_history=[120.0, 110.0],
        baseline_history=[130.0, 125.0],
        baseline_ref=50.0,
        bias_step_start=15.0,
        bias_min=100.0,
    )
    assert result == 100.0


def test_compute_next_bias_first_move_respects_bias_min():
    # a first move from below the minimum lands at bias_min, not at
    # last_bias plus the fixed step
    result = compute_next_bias(
        bias_history=[0.0],
        baseline_history=[100.0],
        baseline_ref=120.0,
        bias_step_start=15.0,
        bias_min=100.0,
    )
    assert result == 100.0


def test_compute_next_bias_rejects_mismatched_history():
    with pytest.raises(ValueError):
        compute_next_bias(
            bias_history=[0.0, 15.0],
            baseline_history=[100.0],
            baseline_ref=120.0,
            bias_step_start=15.0,
        )


def test_compute_next_bias_repeated_bias_uses_last_distinct_pair():
    # regression: after clamping at the floor the last two biases are
    # equal; the slope must come from the last pair of distinct biases
    # instead of falling back to a blind step up, which made the loop
    # bounce between the floor and one step above it
    result = compute_next_bias(
        bias_history=[39.0, 38.0, 38.0],
        baseline_history=[130.0, 129.0, 128.0],
        baseline_ref=100.0,
        bias_step_start=1.0,
        bias_min=38.0,
    )
    assert result == 38.0


def test_compute_next_bias_grows_probe_when_response_below_noise():
    # the baseline moved less than the noise floor, so the slope is
    # meaningless; the probe step doubles in the same direction until
    # the response is measurable
    result = compute_next_bias(
        bias_history=[38.0, 39.0],
        baseline_history=[250.0, 250.5],
        baseline_ref=260.0,
        bias_step_start=1.0,
        noise_floor=2.0,
    )
    assert result == pytest.approx(41.0)


def test_compute_next_bias_probe_growth_is_capped():
    # probe growth doubles the last move but never exceeds
    # 4x bias_step_start
    result = compute_next_bias(
        bias_history=[38.0, 42.0],
        baseline_history=[250.0, 250.5],
        baseline_ref=260.0,
        bias_step_start=1.0,
        noise_floor=2.0,
    )
    assert result == pytest.approx(46.0)


def test_compute_next_bias_field_regression_noise_secant_wrong_direction():
    # regression with the exact numbers from a run14 test sweep: the
    # baseline is 8 ADC units below the reference and the true slope
    # is +20 ADC/uA, but the last two baselines differ by only
    # 0.5 ADC (noise), giving the old two-point secant a slope of
    # -1.3 ADC/uA; it then stepped DOWN 2 uA to 40.36 instead of
    # nudging the bias up. The fit over the full history must drive a
    # small step up: slope 17.3 ADC/uA, 8 ADC below reference.
    result = compute_next_bias(
        bias_history=[40.9795, 41.9563, 42.3633],
        baseline_history=[316.569, 339.182, 338.655],
        baseline_ref=346.651,
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
        baseline_history=[316.569, 339.182, 338.655],
        baseline_ref=346.651,
        bias_step_start=1.0,
        bias_min=37.9678,
    )
    assert result > 42.3633
    assert result == pytest.approx(42.826, abs=0.01)


def test_compute_next_bias_fit_wins_over_probe_when_history_has_signal():
    # regression with the exact numbers from a run14 sweep with a
    # large drift noise floor (21 ADC): the +3 uA first move gave a
    # real 60 ADC response, but the old last-pair guard compared 60
    # against 3x21 = 63 and doubled the probe to +6 uA from a
    # baseline only 2 percent below target. The history plainly holds
    # an 18 ADC/uA slope, so the fit must drive a small step up.
    result = compute_next_bias(
        bias_history=[43.5029, 46.5147, 46.5147],
        baseline_history=[404.334, 464.365, 454.837],
        baseline_ref=464.316,
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
        baseline_history=[100.0, 120.0, 115.0],
        baseline_ref=130.0,
        bias_step_start=15.0,
    )
    # fit slope 0.75 ADC/uA, 15 ADC below reference: step +20
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
        'heater_tes_channel = B'
    )
    config_file = tmp_path / 'gab_sweep_same_channel.ini'
    config_file.write_text(config_text)

    with pytest.raises(ValueError, match='must be different channels'):
        GabSweep(
            sequencer_file=str(config_file),
            setup_file='pytesdaq/config/setup.ini',
            dry_run=True,
        )


def test_wait_for_settled_baseline_timer_mode(monkeypatch):
    # timer mode sleeps settle_wait_time and never runs the check
    sweep = _make_dry_sweep()
    sweep._use_stability_check = False
    sweep._settle_wait_time = 42.0

    slept = list()
    monkeypatch.setattr(gab_sweep_module.time, 'sleep', slept.append)

    def fail_stability():
        raise AssertionError('stability check must not run in timer mode')

    sweep.wait_for_stable_baseline = fail_stability

    settle_ok, history = sweep.wait_for_settled_baseline()

    assert settle_ok is True
    assert history == []
    assert slept == [42.0]


def test_wait_for_settled_baseline_stability_mode():
    # stability mode delegates, passing its result through unchanged
    sweep = _make_dry_sweep()
    sweep._use_stability_check = True
    sweep.wait_for_stable_baseline = lambda: (False, [1.0, 2.0])

    settle_ok, history = sweep.wait_for_settled_baseline()

    assert settle_ok is False
    assert history == [1.0, 2.0]


def test_timer_mode_does_not_require_stability_parameters():
    # the example config is timer mode and omits the stability
    # parameters, so constructing it must not raise
    sweep = _make_dry_sweep()

    assert sweep._use_stability_check is False
    assert sweep._settle_wait_time == 60.0
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


def test_measure_baseline_quality_reports_metrics():
    # fake DAQ returning flat noisy traces around a known level
    sweep = _make_dry_sweep()

    rng = np.random.default_rng(seed=42)
    nb_events = 20
    traces = rng.normal(loc=500.0, scale=1.0, size=(nb_events, 1, 4000))

    class FakeDaq:
        @staticmethod
        def read_many_events(nevents, adctovolt=False):
            return traces

    sweep._daq = FakeDaq()

    quality = sweep.measure_baseline_quality()

    assert quality['nb_traces'] == nb_events
    assert 0 < quality['nb_traces_kept'] <= nb_events
    assert quality['baseline'] == pytest.approx(500.0, abs=1.0)
    assert quality['spread'] >= 0.0

    # measure_baseline stays a thin float-returning wrapper
    assert sweep.measure_baseline() == pytest.approx(
        quality['baseline'], abs=1.0
    )


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
    sweep.measure_baseline = lambda nb_events=None: 250.0
    sweep.wait_for_settled_baseline = lambda: (True, [])
    sweep._baseline_ref = 250.0

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
    sweep.measure_baseline = lambda nb_events=None: 250.0
    sweep.wait_for_settled_baseline = lambda: (True, [])
    sweep._baseline_ref = 250.0

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
    sweep.wait_for_settled_baseline = lambda: (True, [])

    def fake_baseline(nb_events=None):
        # baseline responds to the bias actually applied
        return 100.0 + device['bias']

    sweep.measure_baseline = fake_baseline
    sweep._baseline_ref = 250.0

    sweep._set_heater_bias_min()
    result = sweep._run_feedback()

    assert len(result['bias_history']) > 1

    # each baseline must be consistent with the bias entry it is paired
    # with: recording the requested bias instead would offset every
    # pair by the quantum and skew the secant slope
    for bias, baseline in zip(result['bias_history'],
                              result['baseline_history']):
        assert baseline == pytest.approx(100.0 + bias, abs=1e-9)


def test_run_feedback_converges_with_fake_device():
    # fake linear device: baseline responds linearly to heater bias;
    # the device starts at bias_min (100 uA in the example config)
    sweep = _make_dry_sweep()

    device = {'bias': 100.0}
    baseline_ref = 250.0

    def fake_baseline(nb_events=None):
        # baseline rises 1 ADC unit per uA of heater bias from 100
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
    sweep.measure_baseline = fake_baseline
    sweep.wait_for_settled_baseline = lambda: (True, [])
    sweep._baseline_ref = baseline_ref
    sweep._post_bias_wait = 0.0

    result = sweep._run_feedback()

    assert result['converged'] is True
    assert result['cap_reached'] is False
    final_baseline = result['baseline_history'][-1]
    offset = abs(final_baseline - baseline_ref) / baseline_ref
    assert offset * 100.0 <= sweep._baseline_tolerance_percent


def test_run_feedback_stops_at_bias_cap():
    # device too weak: baseline barely responds, cap must end feedback;
    # the device starts below bias_min so the feedback must first raise
    # the bias to keep the heater TES normal
    sweep = _make_dry_sweep()

    device = {'bias': 0.0}

    def fake_baseline(nb_events=None):
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
    sweep.measure_baseline = fake_baseline
    sweep.wait_for_settled_baseline = lambda: (True, [])
    sweep._baseline_ref = 150.0
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

    sweep._instrument = FakeInstrument()
    sweep._daq = None
    sweep._heater_initial_bias_ua = 42.0

    sweep.shutdown()

    assert device['bias'] == 42.0


def _make_linear_device_sweep(device=None, baseline_offset=100.0):
    # fake linear device shared by the feedback tests: the baseline
    # responds 1 ADC unit per uA of heater bias
    sweep = _make_dry_sweep()

    def fake_baseline(nb_events=None):
        return baseline_offset + device['bias']

    def fake_set_bias(bias, unit=None, detector_channel=None):
        device['bias'] = float(bias)
        return True

    def fake_get_bias(detector_channel=None, unit=None):
        return device['bias']

    class FakeInstrument:
        set_tes_bias = staticmethod(fake_set_bias)
        get_tes_bias = staticmethod(fake_get_bias)

    sweep._instrument = FakeInstrument()
    sweep.measure_baseline = fake_baseline
    sweep.wait_for_settled_baseline = lambda: (True, [])
    sweep._post_bias_wait = 0.0

    return sweep


def test_run_feedback_uses_provided_initial_baseline():
    # run_single_step already measured the settled baseline, so the
    # feedback must start from it instead of silently measuring a
    # second one it never prints
    device = {'bias': 100.0}
    sweep = _make_linear_device_sweep(device=device)
    sweep._baseline_ref = 250.0

    nb_calls = {'count': 0}
    original_measure = sweep.measure_baseline

    def counting_measure(nb_events=None):
        nb_calls['count'] = nb_calls['count'] + 1
        return original_measure(nb_events=nb_events)

    sweep.measure_baseline = counting_measure

    result = sweep._run_feedback(initial_baseline=200.0)

    assert result['baseline_history'][0] == 200.0
    # one history entry per measurement plus the provided one
    assert len(result['baseline_history']) == nb_calls['count'] + 1


def test_run_feedback_requires_confirmation_reading():
    # a single in-tolerance reading is not convergence: it must be
    # confirmed by a second reading at the same bias
    device = {'bias': 100.0}
    sweep = _make_linear_device_sweep(device=device)
    sweep._baseline_ref = 250.0

    result = sweep._run_feedback()

    assert result['converged'] is True
    assert result['bias_history'][-1] == result['bias_history'][-2]

    tolerance = sweep._baseline_tolerance_percent
    for baseline in result['baseline_history'][-2:]:
        offset = abs(baseline - 250.0) / 250.0 * 100.0
        assert offset <= tolerance


def test_run_feedback_confirmation_rejects_drifting_baseline():
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

    baseline_sequence = [250.0, 280.0, 250.0, 250.0]

    def fake_baseline(nb_events=None):
        if len(baseline_sequence) > 0:
            return baseline_sequence.pop(0)
        return 250.0

    sweep._instrument = FakeInstrument()
    sweep.measure_baseline = fake_baseline
    sweep.wait_for_settled_baseline = lambda: (True, [])
    sweep._post_bias_wait = 0.0
    sweep._baseline_ref = 250.0

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
    baseline_sequence = [250.0, 244.8]

    def fake_baseline(nb_events=None):
        if len(baseline_sequence) > 0:
            return baseline_sequence.pop(0)
        return 250.0

    sweep._instrument = FakeInstrument()
    sweep.measure_baseline = fake_baseline
    sweep.wait_for_settled_baseline = lambda: (True, [])
    sweep._post_bias_wait = 0.0
    sweep._baseline_ref = 250.0

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
    baseline_sequence = [245.2, 240.5]

    def fake_baseline(nb_events=None):
        if len(baseline_sequence) > 0:
            return baseline_sequence.pop(0)
        return 250.0

    sweep._instrument = FakeInstrument()
    sweep.measure_baseline = fake_baseline
    sweep.wait_for_settled_baseline = lambda: (True, [])
    sweep._post_bias_wait = 0.0
    sweep._baseline_ref = 250.0

    result = sweep._run_feedback()

    assert result['converged'] is True
    # the near miss was rejected, at least one real bias move followed
    assert len(result['bias_history']) > 2


def test_run_feedback_detects_pinned_at_floor():
    # the baseline sits far above the reference and rises with bias:
    # the target needs a bias below the floor, which is not allowed,
    # so the feedback must flag the point instead of looping on it
    device = {'bias': 100.0}
    sweep = _make_linear_device_sweep(device=device, baseline_offset=300.0)
    sweep._baseline_ref = 250.0

    result = sweep._run_feedback()

    assert result['pinned_at_floor'] is True
    assert result['converged'] is False
    assert result['bias_history'][-1] == pytest.approx(
        sweep._get_bias_floor()
    )


def test_drift_check_parameters_have_defaults():
    # the drift check keys are optional in the config
    sweep = _make_dry_sweep()

    assert sweep._drift_check_nb_measurements == 5
    assert sweep._drift_check_wait_time == 60.0
    assert sweep._baseline_noise_floor == 0.0


def test_run_drift_check_measures_scatter(monkeypatch):
    # the drift check repeats the baseline measurement at fixed
    # conditions and stores the scatter as the feedback noise floor
    sweep = _make_dry_sweep()

    baselines = [250.0, 252.0, 248.0, 251.0, 249.0]
    quality_sequence = list()
    for value in baselines:
        quality_sequence.append({
            'baseline': value,
            'spread': 1.0,
            'nb_traces': 100,
            'nb_traces_kept': 90,
        })

    def fake_quality(nb_events=None):
        return quality_sequence.pop(0)

    sweep.measure_baseline_quality = fake_quality

    slept = list()
    monkeypatch.setattr(gab_sweep_module.time, 'sleep', slept.append)

    drift = sweep.run_drift_check()

    assert drift['baselines'] == baselines
    assert drift['mean'] == pytest.approx(np.mean(baselines))
    assert drift['scatter'] == pytest.approx(np.std(baselines))
    assert sweep._baseline_noise_floor == pytest.approx(np.std(baselines))
    # one wait between consecutive measurements, none before the first
    assert slept == [60.0, 60.0, 60.0, 60.0]
    assert sweep._diagnostics['drift_check'] == drift


def test_run_drift_check_warns_when_scatter_exceeds_tolerance(
        monkeypatch, capsys):
    # drift larger than the convergence tolerance means the feedback
    # cannot work reliably, the user must be warned up front
    sweep = _make_dry_sweep()

    baselines = [250.0, 290.0, 210.0, 270.0, 230.0]
    quality_sequence = list()
    for value in baselines:
        quality_sequence.append({
            'baseline': value,
            'spread': 1.0,
            'nb_traces': 100,
            'nb_traces_kept': 90,
        })

    def fake_quality(nb_events=None):
        return quality_sequence.pop(0)

    sweep.measure_baseline_quality = fake_quality
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
    assert sweep._baseline_noise_floor == 0.0


def test_pinned_at_floor_recorded_in_csv():
    from pytesdaq.sequencer import GabSweep

    assert 'pinned_at_floor' in GabSweep.CSV_COLUMNS


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

    sweep._instrument = FakeInstrument()
    sweep._daq = None

    sweep.shutdown()

    assert device['bias'] == 500.0
