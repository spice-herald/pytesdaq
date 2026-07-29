import csv

import pytest

from pytesdaq.sequencer.iv_didv import IV_dIdV
from pytesdaq.sequencer import GtaSweep


def test_iv_didv_accepts_a_supplied_instrument_control():
    """
    Test that IV_dIdV accepts a supplied instrument control object.

    GtaSweep builds one Control and hands it over, instead of one
    being created per temperature step.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    sequencer = IV_dIdV.__new__(IV_dIdV)
    sequencer._instruments_inst = None

    sentinel = object()
    sequencer.instrument_control = sentinel

    assert sequencer.instrument_control is sentinel
    assert sequencer._instruments_inst is sentinel


def test_iv_didv_exposes_where_data_landed():
    """
    Test that IV_dIdV exposes group_name and raw_data_path properties.

    These properties allow a caller to read back where the data landed after
    a measurement run.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    sequencer = IV_dIdV.__new__(IV_dIdV)
    sequencer._group_name = 'iv_I1_D20260728_T160000'
    sequencer._raw_data_path = '/sdata1/run74/raw/iv_I1_D20260728_T160000'

    assert sequencer.group_name == 'iv_I1_D20260728_T160000'
    assert sequencer.raw_data_path.endswith('T160000')


def test_iv_didv_run_comment_suffix_defaults_to_empty():
    """
    Test that run_comment_suffix property works as expected.

    The run_comment_suffix defaults to empty string and can be set to tag
    each series with the condition it was taken at.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    sequencer = IV_dIdV.__new__(IV_dIdV)
    sequencer._run_comment_suffix = ''

    assert sequencer.run_comment_suffix == ''

    sequencer.run_comment_suffix = ', T_set = 40 mK'
    assert sequencer.run_comment_suffix == ', T_set = 40 mK'


def _make_dry_sweep(config_file='pytesdaq/config/gta_sweep.ini.example'):
    """
    Build a GtaSweep instance in dry-run mode from a config file.

    Parameters
    ----------
    config_file : str
        Path to the gta_sweep config file.

    Returns
    -------
    sweep : GtaSweep
        A GtaSweep instance constructed with dry_run=True.
    """
    sweep = GtaSweep(
        sequencer_file=config_file,
        setup_file='pytesdaq/config/setup.ini',
        dry_run=True,
    )
    return sweep


def test_config_parses_from_example():
    """
    Test that the gta_sweep example config parses into a temperature
    sweep with the expected thermometer, heater, and a setpoint list.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    sweep = _make_dry_sweep()

    assert sweep._temperature_sweep.thermometer_name == 'CP'
    assert sweep._temperature_sweep.heater_name == 'heaterMC'
    assert len(sweep._temperature_sweep.temperature_list_mk) > 1

    # strictly decreasing, the sweep goes from high to low
    temperatures = sweep._temperature_sweep.temperature_list_mk
    assert temperatures == sorted(temperatures, reverse=True)


def test_classification_excludes_non_tes_channels():
    """
    Test that classify_tes_channels excludes non-TES channels.

    The TTL and accelerometer inputs are on the connection map but
    must never be biased, so they must never show up among the TES
    channels returned by classify_tes_channels.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    sweep = _make_dry_sweep()
    tes_channels, non_tes_channels = sweep.classify_tes_channels()

    assert sweep._tes_channel in tes_channels
    for channel in non_tes_channels:
        assert channel not in tes_channels


def test_zero_channels_excludes_the_swept_channel():
    """
    Test that the swept channel is excluded from the zeroed channels.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    sweep = _make_dry_sweep()

    assert sweep._tes_channel not in sweep._zero_channels
    for channel in sweep._zero_channels:
        assert channel in sweep.classify_tes_channels()[0]


def test_rejects_a_swept_channel_that_is_not_a_tes(tmp_path):
    """
    Test that requesting a non-TES channel as the swept channel fails.

    rigolTTL is on the connection map but has no "tes:" field, so it
    cannot be biased. Asking to sweep it must fail loudly at startup
    rather than the sweep silently doing nothing useful. This is also
    what protects a setup file that marks no channels at all, such as
    setup.ini.example_lbl.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Pytest fixture directory for writing the modified config file.

    Returns
    -------
    None
    """
    with open('pytesdaq/config/gta_sweep.ini.example', 'r') as f:
        config_text = f.read()

    config_text = config_text.replace(
        'tes_channel = D',
        'tes_channel = rigolTTL'
    )
    config_file = tmp_path / 'gta_sweep_non_tes_channel.ini'
    config_file.write_text(config_text)

    with pytest.raises(ValueError, match='not marked as a TES channel'):
        GtaSweep(
            sequencer_file=str(config_file),
            setup_file='pytesdaq/config/setup.ini',
            dry_run=True,
        )


def test_rejects_an_unknown_channel(tmp_path):
    """
    Test that requesting a channel not on the connection map at all
    fails.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Pytest fixture directory for writing the modified config file.

    Returns
    -------
    None
    """
    with open('pytesdaq/config/gta_sweep.ini.example', 'r') as f:
        config_text = f.read()

    config_text = config_text.replace(
        'tes_channel = D',
        'tes_channel = not_a_real_channel'
    )
    config_file = tmp_path / 'gta_sweep_bad_channel.ini'
    config_file.write_text(config_text)

    with pytest.raises(ValueError):
        GtaSweep(
            sequencer_file=str(config_file),
            setup_file='pytesdaq/config/setup.ini',
            dry_run=True,
        )


def test_dry_run_prints_the_plan_without_hardware(capsys):
    """
    Test that dry_run prints the sweep plan without any hardware
    interaction.

    Parameters
    ----------
    capsys : pytest fixture
        Captures stdout and stderr produced during the test.

    Returns
    -------
    None
    """
    sweep = _make_dry_sweep()
    sweep.run()

    printed = capsys.readouterr().out
    assert 'DRY RUN' in printed
    assert 'Temperature setpoints' in printed
    assert 'zeroed' in printed.lower()


class _FakeBiasInstrument:
    """
    Fake instrument control that records every bias write.

    This lets a test check what the sweep did to each channel and in
    what order, without touching real hardware.
    """

    def __init__(self, biases):
        """
        Store the starting per-channel biases and an empty write log.

        Parameters
        ----------
        biases : dict
            Detector channel name to starting TES bias [uA].

        Returns
        -------
        None
        """
        self.biases = dict(biases)
        self.writes = list()

    def get_tes_bias(self, detector_channel=None, unit=None):
        """
        Return the bias currently recorded for a channel.

        Parameters
        ----------
        detector_channel : str or None
            Detector channel name to read.
        unit : str or None
            Unit of the returned bias, unused by this fake.

        Returns
        -------
        bias : float
            The bias currently recorded for the channel.
        """
        return self.biases[detector_channel]

    def set_tes_bias(self, bias, unit=None, detector_channel=None):
        """
        Record a bias write for a channel.

        Parameters
        ----------
        bias : float
            The bias value to write.
        unit : str or None
            Unit of the bias, unused by this fake.
        detector_channel : str or None
            Detector channel name to write to.

        Returns
        -------
        success : bool
            Always True, mimicking a successful hardware write.
        """
        self.biases[detector_channel] = bias
        self.writes.append((detector_channel, bias))
        return True


def _sweep_with_fake_instrument():
    """
    Build a dry-run GtaSweep wired to a fake bias instrument.

    Each TES channel, the swept channel and the zero channels alike,
    is given a distinct starting bias, so a test can verify that
    captured, zeroed, and restored values line up with the right
    channel.

    Parameters
    ----------
    None

    Returns
    -------
    sweep : GtaSweep
        A GtaSweep instance with its instrument replaced by the fake.
    instrument : _FakeBiasInstrument
        The fake instrument, for inspecting recorded writes.
    """
    sweep = _make_dry_sweep()
    channels = [sweep._tes_channel] + sweep._zero_channels
    biases = dict()
    for index, channel in enumerate(channels):
        biases[channel] = 10.0 + index
    instrument = _FakeBiasInstrument(biases)
    sweep._instrument = instrument
    sweep._temperature_sweep.instrument = instrument
    return sweep, instrument


def test_capture_initial_biases_records_every_tes_channel():
    """
    Test that capture_initial_biases records every real TES channel.

    Reading the pre-run biases must not itself write anything to the
    instrument.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    sweep, instrument = _sweep_with_fake_instrument()

    captured = sweep.capture_initial_biases()

    assert sweep._tes_channel in captured
    for channel in sweep._zero_channels:
        assert channel in captured
    # nothing was written while only reading
    assert instrument.writes == []


def test_zero_other_channels_leaves_the_swept_channel_alone():
    """
    Test that zero_other_channels zeroes every channel except the one
    being swept.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    sweep, instrument = _sweep_with_fake_instrument()
    sweep.capture_initial_biases()

    sweep.zero_other_channels()

    for channel in sweep._zero_channels:
        assert instrument.biases[channel] == 0
    assert instrument.biases[sweep._tes_channel] != 0

    written_channels = [channel for channel, bias in instrument.writes]
    assert sweep._tes_channel not in written_channels


def test_zero_other_channels_never_touches_a_non_tes_channel():
    """
    Test that zero_other_channels never writes to a channel that is
    not a TES.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    sweep, instrument = _sweep_with_fake_instrument()
    sweep.capture_initial_biases()

    sweep.zero_other_channels()

    written_channels = [channel for channel, bias in instrument.writes]
    for channel in sweep._non_tes_channels:
        assert channel not in written_channels


def test_restore_initial_biases_puts_every_channel_back():
    """
    Test that restore_initial_biases puts every captured channel back
    to its pre-run bias, including the swept channel wherever the IV
    sweep left it.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    sweep, instrument = _sweep_with_fake_instrument()
    initial = dict(sweep.capture_initial_biases())

    sweep.zero_other_channels()
    # the IV sweep leaves the swept channel wherever it ended
    instrument.biases[sweep._tes_channel] = 0.5

    sweep.restore_initial_biases()

    for channel, bias in initial.items():
        assert instrument.biases[channel] == pytest.approx(bias)


def test_restore_initial_biases_continues_past_a_failing_channel():
    """
    One channel refusing to restore must not strand the others.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    sweep, instrument = _sweep_with_fake_instrument()
    initial = dict(sweep.capture_initial_biases())
    sweep.zero_other_channels()

    failing_channel = sweep._zero_channels[0]
    original_set = instrument.set_tes_bias

    def flaky_set(bias, unit=None, detector_channel=None):
        """
        Raise for one channel and delegate to the real fake write
        for every other channel, to simulate an instrument that is
        not responding on a single channel.

        Parameters
        ----------
        bias : float
            The bias value to write.
        unit : str or None
            Unit of the bias, unused by this fake.
        detector_channel : str or None
            Detector channel name to write to.

        Returns
        -------
        success : bool
            True, mimicking a successful hardware write, for every
            channel other than the failing one.
        """
        if detector_channel == failing_channel:
            raise RuntimeError('instrument not responding')
        return original_set(bias, unit=unit,
                            detector_channel=detector_channel)

    instrument.set_tes_bias = flaky_set

    sweep.restore_initial_biases()

    for channel, bias in initial.items():
        if channel == failing_channel:
            continue
        assert instrument.biases[channel] == pytest.approx(bias)


def test_capture_is_not_repeated_on_a_second_call():
    """
    Capturing twice after zeroing would record 0 as the value to
    restore, which would silently discard the user's bias points, so
    the first capture must win.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    sweep, instrument = _sweep_with_fake_instrument()
    initial = dict(sweep.capture_initial_biases())
    sweep.zero_other_channels()

    recaptured = sweep.capture_initial_biases()

    assert recaptured == initial


def test_capture_initial_biases_leaves_no_partial_state_on_failure():
    """
    A capture where get_tes_bias raises partway through must leave
    self._initial_biases_ua empty and the completeness flag False, so
    a later successful capture records the real pre-run values rather
    than inheriting a partial dict.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    sweep, instrument = _sweep_with_fake_instrument()
    failing_channel = sweep._zero_channels[0]
    original_get = instrument.get_tes_bias

    def flaky_get(detector_channel=None, unit=None):
        """
        Raise for one channel and delegate to the real fake read for
        every other channel, to simulate an instrument that stops
        responding partway through a capture.

        Parameters
        ----------
        detector_channel : str or None
            Detector channel name to read.
        unit : str or None
            Unit of the returned bias, unused by this fake.

        Returns
        -------
        bias : float
            The bias currently recorded for the channel, for every
            channel other than the failing one.
        """
        if detector_channel == failing_channel:
            raise RuntimeError('instrument not responding')
        return original_get(detector_channel=detector_channel, unit=unit)

    instrument.get_tes_bias = flaky_get

    with pytest.raises(RuntimeError):
        sweep.capture_initial_biases()

    assert sweep._initial_biases_ua == dict()
    assert sweep._biases_captured is False

    instrument.get_tes_bias = original_get
    captured = sweep.capture_initial_biases()

    assert captured == instrument.biases


class _FakeIvSequencer:
    """
    Stand-in for IV_dIdV: records that a sweep ran and reports where
    the data would have landed.
    """

    def __init__(self):
        """
        Set up a fake IV sequencer with a fixed group name and raw
        data path, and an empty log of run comment suffixes.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        self.instrument_control = None
        self.run_comment_suffix = ''
        self.runs = list()
        self.group_name = 'iv_I1_D20260728_T160000'
        self.raw_data_path = '/data/run74/raw/iv_I1_D20260728_T160000'

    def _run_iv_didv(self):
        """
        Record the current run comment suffix and report success.

        Parameters
        ----------
        None

        Returns
        -------
        success : bool
            Always True, mimicking a successful IV sweep.
        """
        self.runs.append(self.run_comment_suffix)
        return True


def test_run_single_step_writes_every_row_key_to_csv(tmp_path):
    """
    Test that run_single_step returns a row with exactly the declared
    CSV columns, correctly populated.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Pytest fixture directory for writing the CSV file.

    Returns
    -------
    None
    """
    from pytesdaq.sequencer import GtaSweep

    sweep, instrument = _sweep_with_fake_instrument()
    sweep._dry_run = False
    sweep.capture_initial_biases()

    temperatures = [0.0402, 0.0399]

    def fake_measure():
        """
        Pop and return the next fake temperature measurement.

        Parameters
        ----------
        None

        Returns
        -------
        measurement : dict
            Fake temperature measurement with keys temperature_k,
            temperature_err_k, fit_ok, nb_samples and samples.
        """
        value = temperatures.pop(0)
        return {'temperature_k': value, 'temperature_err_k': 0.0001,
                'fit_ok': True, 'nb_samples': 100, 'samples': [value]}

    sweep._temperature_sweep.measure_temperature = fake_measure
    sweep._temperature_sweep.set_setpoint = lambda temperature_mk=None: None
    sweep._temperature_sweep.wait_for_temperature = (
        lambda temperature_mk=None: (True, [40.0])
    )

    sweep._iv_sequencer = _FakeIvSequencer()

    sweep._csv_path = str(tmp_path / 'gta_sweep_data.csv')
    with open(sweep._csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=GtaSweep.CSV_COLUMNS)
        writer.writeheader()

    row = sweep.run_single_step(temperature_mk=40.0, step_index=0)

    # every declared column is present, none extra
    assert set(row.keys()) == set(GtaSweep.CSV_COLUMNS)

    assert row['temperature_setpoint_mk'] == pytest.approx(40.0)
    assert row['mc_temperature_before_mk'] == pytest.approx(40.2)
    assert row['mc_temperature_after_mk'] == pytest.approx(39.9)
    assert row['temperature_drift_mk'] == pytest.approx(-0.3)
    assert row['temperature_ok'] is True
    assert row['tes_channel'] == sweep._tes_channel
    assert row['iv_group_name'] == 'iv_I1_D20260728_T160000'
    assert row['iv_success'] is True


def test_run_single_step_tags_the_iv_run_comment_with_temperature():
    """
    Test that run_single_step tags the IV sequencer's run comment
    suffix with the step index and setpoint temperature.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    sweep, instrument = _sweep_with_fake_instrument()
    sweep._dry_run = False
    sweep.capture_initial_biases()

    sweep._temperature_sweep.measure_temperature = lambda: {
        'temperature_k': 0.040, 'temperature_err_k': 0.0001,
        'fit_ok': True, 'nb_samples': 10, 'samples': [0.040]}
    sweep._temperature_sweep.set_setpoint = lambda temperature_mk=None: None
    sweep._temperature_sweep.wait_for_temperature = (
        lambda temperature_mk=None: (True, [40.0])
    )

    iv_sequencer = _FakeIvSequencer()
    sweep._iv_sequencer = iv_sequencer
    sweep._csv_path = None

    sweep.run_single_step(temperature_mk=40.0, step_index=0)

    assert len(iv_sequencer.runs) == 1
    assert '40' in iv_sequencer.runs[0]


def test_run_single_step_records_a_timed_out_setpoint(tmp_path):
    """
    Test that a temperature timeout flags the row but still takes the
    IV sweep, since the recorded temperature is the measured one, not
    the setpoint.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Pytest fixture directory, unused since this test disables the
        CSV write, kept for parity with the other run_single_step
        tests.

    Returns
    -------
    None
    """
    sweep, instrument = _sweep_with_fake_instrument()
    sweep._dry_run = False
    sweep.capture_initial_biases()

    sweep._temperature_sweep.measure_temperature = lambda: {
        'temperature_k': 0.045, 'temperature_err_k': 0.0001,
        'fit_ok': True, 'nb_samples': 10, 'samples': [0.045]}
    sweep._temperature_sweep.set_setpoint = lambda temperature_mk=None: None
    sweep._temperature_sweep.wait_for_temperature = (
        lambda temperature_mk=None: (False, [45.0])
    )

    iv_sequencer = _FakeIvSequencer()
    sweep._iv_sequencer = iv_sequencer
    sweep._csv_path = None

    row = sweep.run_single_step(temperature_mk=40.0, step_index=0)

    assert row['temperature_ok'] is False
    assert len(iv_sequencer.runs) == 1


def test_shutdown_restores_biases_and_zeroes_the_heater():
    """
    Test that shutdown zeroes the MC heater setpoint and restores
    every TES channel to its pre-run bias.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    sweep, instrument = _sweep_with_fake_instrument()
    initial = dict(sweep.capture_initial_biases())
    sweep.zero_other_channels()

    heater_calls = list()
    sweep._temperature_sweep.heater_to_zero = (
        lambda: heater_calls.append(True)
    )

    sweep.shutdown()

    assert heater_calls == [True]
    for channel, bias in initial.items():
        assert instrument.biases[channel] == pytest.approx(bias)


def test_shutdown_runs_even_when_a_step_raises():
    """
    Test that an exception mid sweep still restores the biases,
    because run()'s finally block must always reach shutdown().

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    sweep, instrument = _sweep_with_fake_instrument()
    sweep._dry_run = False
    initial = dict(sweep.capture_initial_biases())

    sweep._temperature_sweep.heater_to_zero = lambda: None
    sweep._instantiate_drivers = lambda: None
    sweep._build_iv_sequencer = lambda: _FakeIvSequencer()
    sweep._create_output_directory = lambda: None
    sweep._save_diagnostics = lambda: None

    def exploding_step(temperature_mk=None, step_index=None):
        """
        Raise unconditionally, standing in for an instrument failure
        partway through the sweep.

        Parameters
        ----------
        temperature_mk : float or None
            MC temperature setpoint in mK, unused.
        step_index : int or None
            Zero-based index of this point in the sweep, unused.

        Returns
        -------
        None
        """
        raise RuntimeError('instrument fell over')

    sweep.run_single_step = exploding_step

    with pytest.raises(RuntimeError):
        sweep.run()

    for channel, bias in initial.items():
        assert instrument.biases[channel] == pytest.approx(bias)
