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
