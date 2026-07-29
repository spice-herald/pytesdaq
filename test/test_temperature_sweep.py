import numpy as np
import pytest

from pytesdaq.sequencer import temperature_sweep as temperature_sweep_module
from pytesdaq.sequencer.temperature_sweep import (
    TemperatureSweep,
    build_temperature_list,
    config_get,
    config_has,
    fit_temperature_gaussian,
)


def _make_config(**overrides):
    """
    Build a minimal config accepted by TemperatureSweep, keys
    lowercased the way configparser delivers them.

    Parameters
    ----------
    overrides : dict
        Keyword arguments overriding individual default config values.

    Returns
    -------
    config_dict : dict
        Config dictionary with the defaults merged with overrides.
    """

    config_dict = {
        'thermometer_name': 'CP',
        'thermometer_instrument': 'macrt',
        'heater_name': 'heaterMC',
        'use_temperature_vect': True,
        'temperature_vect_mk': [42.0, 41.0, 40.0],
        'temperature_poll_interval_s': 1.0,
        'temperature_stable_time_s': 3.0,
        'temperature_max_wait_time_s': 100.0,
        'temperature_tolerance_frac': 0.02,
        'temperature_sampling_time_s': 5.0,
    }
    config_dict.update(overrides)
    return config_dict


def _make_sweep(readings, monkeypatch, **overrides):
    """
    Build a sweep whose thermometer returns the given readings [K],
    with a fake clock advancing only when sleep is called.

    Parameters
    ----------
    readings : list of float
        Thermometer readings [K] returned in order by the fake
        instrument; the last value repeats once exhausted.
    monkeypatch : pytest fixture
        Used to patch temperature_sweep_module.time.time and
        temperature_sweep_module.time.sleep with a fake clock.
    overrides : dict
        Keyword arguments overriding individual default config values,
        forwarded to _make_config.

    Returns
    -------
    sweep : TemperatureSweep
        Sweep configured with a fake instrument and a fake clock.
    """

    sweep = TemperatureSweep(config_dict=_make_config(**overrides),
                             verbose=False)

    values = list(readings)

    class FakeInstrument:
        @staticmethod
        def get_temperature(channel_name=None, instrument_name=None):
            if len(values) > 1:
                return values.pop(0)
            return values[0]

    sweep.instrument = FakeInstrument()

    clock = {'now': 0.0}

    def fake_time():
        return clock['now']

    def fake_sleep(seconds):
        clock['now'] = clock['now'] + seconds

    monkeypatch.setattr(temperature_sweep_module.time, 'time', fake_time)
    monkeypatch.setattr(temperature_sweep_module.time, 'sleep', fake_sleep)

    return sweep


def test_build_temperature_list_from_vect():
    """
    Build the temperature list from a vector of mixed str/float
    values.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    config_dict = {
        'use_temperature_vect': True,
        'temperature_vect_mk': ['42', 41.0, '40.5', '38'],
    }
    result = build_temperature_list(config_dict=config_dict)
    assert result == [42.0, 41.0, 40.5, 38.0]


def test_build_temperature_list_from_single_value_vect():
    """
    Build the temperature list from a single-value vect; the config
    parser (get_sequencer_setup) collapses single-element lists to a
    scalar, so this scalar form must still be accepted.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    config_dict = {
        'use_temperature_vect': True,
        'temperature_vect_mk': 42.0,
    }
    result = build_temperature_list(config_dict=config_dict)
    assert result == [42.0]


def test_build_temperature_list_from_start_stop_step():
    """
    Build the temperature list from start/stop/step config values.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    config_dict = {
        'use_temperature_vect': False,
        'temperature_start_mk': '42',
        'temperature_stop_mk': '38',
        'temperature_step_mk': '1',
    }
    result = build_temperature_list(config_dict=config_dict)
    assert result == [42.0, 41.0, 40.0, 39.0, 38.0]


def test_build_temperature_list_rejects_ascending_vect():
    """
    Reject an ascending temperature vect, since the sweep must be
    strictly decreasing.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    config_dict = {
        'use_temperature_vect': True,
        'temperature_vect_mk': [38, 40, 42],
    }
    with pytest.raises(ValueError):
        build_temperature_list(config_dict=config_dict)


def test_build_temperature_list_rejects_zero_step():
    """
    Reject a zero temperature_step_mk, since it would never advance
    the sweep.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    config_dict = {
        'use_temperature_vect': False,
        'temperature_start_mk': 42,
        'temperature_stop_mk': 38,
        'temperature_step_mk': 0,
    }
    with pytest.raises(ValueError):
        build_temperature_list(config_dict=config_dict)


def test_fit_temperature_gaussian_recovers_mean_and_sigma():
    """
    Recover the true mean and sigma of a Gaussian-distributed sample
    set from fit_temperature_gaussian.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    rng = np.random.default_rng(seed=7)
    samples = rng.normal(0.040, 0.0002, size=500)
    result = fit_temperature_gaussian(samples=samples)
    assert result['fit_ok'] is True
    assert result['mean'] == pytest.approx(0.040, abs=0.00005)
    assert result['sigma'] == pytest.approx(0.0002, rel=0.3)
    assert result['nb_samples'] == 500


def test_fit_temperature_gaussian_falls_back_on_identical_samples():
    """
    Fall back to the sample mean and zero sigma when all samples are
    identical, since a quantizing controller can return the same
    reading every time and the histogram fit cannot run on zero
    spread.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    result = fit_temperature_gaussian(samples=[0.040] * 50)
    assert result['fit_ok'] is False
    assert result['mean'] == pytest.approx(0.040)
    assert result['sigma'] == pytest.approx(0.0)


def test_fit_temperature_gaussian_falls_back_on_few_samples():
    """
    Fall back to the sample mean and standard deviation when too few
    samples are available for a histogram fit.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    samples = [0.040, 0.041, 0.039]
    result = fit_temperature_gaussian(samples=samples)
    assert result['fit_ok'] is False
    assert result['mean'] == pytest.approx(np.mean(samples))
    assert result['sigma'] == pytest.approx(np.std(samples))


def test_fit_temperature_gaussian_rejects_empty_samples():
    """
    Reject an empty sample list, since no temperature can be
    estimated from zero readings.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    with pytest.raises(ValueError):
        fit_temperature_gaussian(samples=[])


def test_config_lookup_ignores_unit_suffix_case():
    """
    Resolve a config key by its canonical capitalization even though
    configparser lowercases every option name, so the canonical
    capitalization written in a config file must still resolve.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    config_dict = {'temperature_start_mk': 42.0}
    assert config_has(config_dict, 'temperature_start_mK')
    assert config_get(config_dict, 'temperature_start_mK') == 42.0
    assert not config_has(config_dict, 'missing_key_mK')


def test_wait_for_temperature_waits_out_a_slow_approach(monkeypatch):
    """
    Wait out a slow temperature approach: the fridge coasts down for
    several polls before arriving, and the wait must not return until
    the setpoint is reached and held.

    Parameters
    ----------
    monkeypatch : pytest fixture
        Used indirectly, through _make_sweep, to patch time.time and
        time.sleep with a fake clock.

    Returns
    -------
    None
    """

    readings = [0.060, 0.055, 0.050, 0.045, 0.0401]
    sweep = _make_sweep(readings, monkeypatch)

    temperature_ok, history = sweep.wait_for_temperature(
        temperature_mk=40.0
    )

    assert temperature_ok is True
    assert history[:4] == pytest.approx([60.0, 55.0, 50.0, 45.0])
    assert history[-1] == pytest.approx(40.1)


def test_wait_for_temperature_restarts_hold_on_excursion(monkeypatch):
    """
    Restart the hold timer on a temperature excursion: a reading that
    drifts back out of tolerance restarts the hold, so a brief touch
    of the setpoint is not enough.

    Parameters
    ----------
    monkeypatch : pytest fixture
        Used indirectly, through _make_sweep, to patch time.time and
        time.sleep with a fake clock.

    Returns
    -------
    None
    """

    readings = [0.0401, 0.050, 0.0401]
    sweep = _make_sweep(readings, monkeypatch)

    temperature_ok, history = sweep.wait_for_temperature(
        temperature_mk=40.0
    )

    assert temperature_ok is True
    assert pytest.approx(50.0) in history
    assert history.index(pytest.approx(50.0)) < len(history) - 1


def test_wait_for_temperature_times_out_when_setpoint_unreachable(
        monkeypatch):
    """
    Time out when the setpoint is unreachable: a fridge that never
    gets there must time out and report failure rather than silently
    letting the sweep measure.

    Parameters
    ----------
    monkeypatch : pytest fixture
        Used indirectly, through _make_sweep, to patch time.time and
        time.sleep with a fake clock.

    Returns
    -------
    None
    """

    readings = [0.060]
    sweep = _make_sweep(readings, monkeypatch)

    temperature_ok, history = sweep.wait_for_temperature(
        temperature_mk=40.0
    )

    assert temperature_ok is False
    assert len(history) > 1


def test_measure_temperature_samples_over_window(monkeypatch):
    """
    Sample the temperature over a window: the measurement keeps
    sampling until the window closes and reports the Gaussian mean and
    sigma of the readings.

    Parameters
    ----------
    monkeypatch : pytest fixture
        Used to patch temperature_sweep_module.time.time with a fake
        clock that advances 10 ms per call.

    Returns
    -------
    None
    """

    sweep = TemperatureSweep(
        config_dict=_make_config(temperature_sampling_time_s=1.0),
        verbose=False
    )

    rng = np.random.default_rng(seed=11)
    readings = list(rng.normal(0.040, 0.0002, size=200))

    class FakeInstrument:
        @staticmethod
        def get_temperature(channel_name=None, instrument_name=None):
            return readings.pop(0)

    sweep.instrument = FakeInstrument()

    # fake clock: each call advances 10 ms, so a 1 s window takes
    # 100 samples deterministically
    clock = {'now': 0.0}

    def fake_time():
        clock['now'] = clock['now'] + 0.010
        return clock['now']

    monkeypatch.setattr(temperature_sweep_module.time, 'time', fake_time)

    measurement = sweep.measure_temperature()

    assert measurement['nb_samples'] == pytest.approx(100, abs=1)
    assert measurement['temperature_k'] == pytest.approx(0.040, abs=0.0001)
    assert len(measurement['samples']) == measurement['nb_samples']


def test_measure_temperature_zero_window_takes_one_sample():
    """
    Take exactly one sample on a zero sampling window: a zero window
    still returns a single reading with the fallback statistics.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    sweep = TemperatureSweep(
        config_dict=_make_config(temperature_sampling_time_s=0.0),
        verbose=False
    )

    class FakeInstrument:
        @staticmethod
        def get_temperature(channel_name=None, instrument_name=None):
            return 0.040

    sweep.instrument = FakeInstrument()

    measurement = sweep.measure_temperature()

    assert measurement['nb_samples'] == 1
    assert measurement['temperature_k'] == pytest.approx(0.040)
    assert measurement['fit_ok'] is False


def test_set_setpoint_does_not_use_the_driver_blocking_wait():
    """
    Apply a setpoint without using the driver's own blocking wait: the
    driver's own wait cannot report whether it reached the setpoint or
    ran out of time, so this sweep polls instead.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    calls = list()

    class FakeInstrument:
        @staticmethod
        def set_temperature(temperature, channel_name=None,
                            heater_channel_name=None,
                            instrument_name=None,
                            wait_temperature_reached=None):
            calls.append({
                'temperature': temperature,
                'channel_name': channel_name,
                'heater_channel_name': heater_channel_name,
                'wait_temperature_reached': wait_temperature_reached,
            })

    sweep = TemperatureSweep(config_dict=_make_config(), verbose=False)
    sweep.instrument = FakeInstrument()

    sweep.set_setpoint(temperature_mk=40.0)

    assert calls[0]['temperature'] == pytest.approx(0.040)
    assert calls[0]['channel_name'] == 'CP'
    assert calls[0]['heater_channel_name'] == 'heaterMC'
    assert calls[0]['wait_temperature_reached'] is False


def test_heater_to_zero_sets_setpoint_zero():
    """
    Set the heater setpoint to zero through heater_to_zero.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    calls = list()

    class FakeInstrument:
        @staticmethod
        def set_temperature(temperature, channel_name=None,
                            heater_channel_name=None,
                            instrument_name=None,
                            wait_temperature_reached=None):
            calls.append(temperature)

    sweep = TemperatureSweep(config_dict=_make_config(), verbose=False)
    sweep.instrument = FakeInstrument()

    sweep.heater_to_zero()

    assert calls == [0]


def test_missing_required_key_is_rejected():
    """
    Reject construction when a required config key is missing.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    config_dict = _make_config()
    del config_dict['temperature_tolerance_frac']
    with pytest.raises(ValueError, match='temperature_tolerance_frac'):
        TemperatureSweep(config_dict=config_dict, verbose=False)


def test_temperature_list_is_exposed():
    """
    Expose the parsed temperature list and thermometer/heater names
    through TemperatureSweep's read-only properties.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    sweep = TemperatureSweep(config_dict=_make_config(), verbose=False)
    assert sweep.temperature_list_mk == [42.0, 41.0, 40.0]
    assert sweep.thermometer_name == 'CP'
    assert sweep.heater_name == 'heaterMC'
