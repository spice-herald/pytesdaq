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
