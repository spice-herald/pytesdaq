import csv
import os
import pickle
from unittest.mock import MagicMock

import pytest

from pytesdaq.sequencer import gta_sweep as gta_sweep_module
from pytesdaq.sequencer import iv_didv as iv_didv_module
from pytesdaq.sequencer.iv_didv import IV_dIdV
from pytesdaq.sequencer import GtaSweep

# committed test fixture, so the suite runs on a fresh clone. The
# operational pytesdaq/config/setup.ini is machine local and
# untracked, and setup.ini.example_lbl marks no channel with "tes:",
# which would make every channel classification test vacuous
SETUP_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'fixtures',
    'setup_test.ini'
)


def _make_real_iv_sequencer(online_iv=True):
    """
    Build a real IV_dIdV the way GtaSweep does.

    Constructing the real object rather than IV_dIdV.__new__ is the
    point: __new__ skips __init__, so a test built on it can only
    assert values it set itself and would still pass if __init__ never
    initialised the attribute at all.

    Parameters
    ----------
    online_iv : bool
        Whether to enable the online IV diagnostic plots. Tests that
        drive the sweep against a fake DAQ turn this off, because the
        diagnostic fits the traces the DAQ returns and a fake returns
        none.

    Returns
    -------
    sequencer : IV_dIdV
        A configured IV sequencer that has touched no hardware.
    """
    sequencer = IV_dIdV(
        iv=True,
        didv=False,
        rp=False,
        rn=False,
        temperature_sweep=False,
        tes_bias_sweep=True,
        online_iv=online_iv,
        sweep_channels=['TestTES_D'],
        sequencer_file='pytesdaq/config/gta_sweep.ini.example',
        setup_file=SETUP_FILE,
        dummy_mode=True,
        verbose=False,
    )
    return sequencer


def test_iv_didv_init_leaves_the_new_accessors_inert():
    """
    A real IV_dIdV must start with no instrument control and an empty
    run comment suffix.

    These two defaults are what make the accessors additive: run()
    builds its own Control when none was supplied, and appending an
    empty suffix leaves every existing run comment unchanged. If
    __init__ stopped setting them, every existing run_iv_didv.py run
    would die with AttributeError.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    sequencer = _make_real_iv_sequencer()

    assert sequencer.instrument_control is None
    assert sequencer.run_comment_suffix == ''


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
    sequencer = _make_real_iv_sequencer()

    sentinel = object()
    sequencer.instrument_control = sentinel

    assert sequencer.instrument_control is sentinel
    assert sequencer._instruments_inst is sentinel


def test_iv_didv_run_does_not_replace_a_supplied_instrument_control(
        monkeypatch):
    """
    run() builds its own instrument control only when none was
    supplied. Rebuilding it would defeat the whole reason GtaSweep
    hands one over, which is that a Control is built once for the
    sweep rather than once per temperature step.

    Parameters
    ----------
    monkeypatch : pytest fixture
        Used to stub out Control construction and the sweep itself.

    Returns
    -------
    None
    """
    sequencer = _make_real_iv_sequencer()

    built = list()

    def unexpected_control(setup_file=None, dummy_mode=False):
        """
        Record that a Control was built and return a new object.

        Parameters
        ----------
        setup_file : str or None
            Setup file path, unused by this stub.
        dummy_mode : bool
            Dummy mode flag, unused by this stub.

        Returns
        -------
        control : object
            A stand-in for the instrument control instance.
        """
        built.append(setup_file)
        return object()

    monkeypatch.setattr(iv_didv_module.instrument, 'Control',
                        unexpected_control)
    monkeypatch.setattr(sequencer, '_run_iv_didv', lambda: True)

    sentinel = object()
    sequencer.instrument_control = sentinel
    sequencer.run()

    assert built == []
    assert sequencer.instrument_control is sentinel


def test_iv_didv_run_builds_an_instrument_control_when_none_supplied(
        monkeypatch):
    """
    The other half of the reuse guard: a caller that supplies nothing,
    which is every existing run_iv_didv.py run, must still get a
    Control built for it.

    Parameters
    ----------
    monkeypatch : pytest fixture
        Used to stub out Control construction and the sweep itself.

    Returns
    -------
    None
    """
    sequencer = _make_real_iv_sequencer()

    built = list()
    control = object()

    def fake_control(setup_file=None, dummy_mode=False):
        """
        Record that a Control was built and return a fixed object.

        Parameters
        ----------
        setup_file : str or None
            Setup file path, recorded so the test can check it.
        dummy_mode : bool
            Dummy mode flag, unused by this stub.

        Returns
        -------
        control : object
            A stand-in for the instrument control instance.
        """
        built.append(setup_file)
        return control

    monkeypatch.setattr(iv_didv_module.instrument, 'Control',
                        fake_control)
    monkeypatch.setattr(sequencer, '_run_iv_didv', lambda: True)

    sequencer.run()

    assert len(built) == 1
    assert sequencer.instrument_control is control


def test_iv_didv_exposes_where_data_landed():
    """
    Test that IV_dIdV exposes group_name and raw_data_path properties.

    These properties allow a caller to read back where the data landed
    after a measurement run.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    sequencer = _make_real_iv_sequencer()
    sequencer._group_name = 'iv_I1_D20260728_T160000'
    sequencer._raw_data_path = '/sdata1/run74/raw/iv_I1_D20260728_T160000'

    assert sequencer.group_name == 'iv_I1_D20260728_T160000'
    assert sequencer.raw_data_path == (
        '/sdata1/run74/raw/iv_I1_D20260728_T160000'
    )


def test_iv_didv_where_data_landed_is_read_only():
    """
    group_name and raw_data_path report where the data went. A caller
    that could assign them could make the Gta CSV point at a series
    that was never written.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    sequencer = _make_real_iv_sequencer()

    with pytest.raises(AttributeError):
        sequencer.group_name = 'not_a_real_group'

    with pytest.raises(AttributeError):
        sequencer.raw_data_path = '/not/a/real/path'


def test_iv_didv_run_comment_suffix_defaults_to_empty():
    """
    Test that run_comment_suffix property works as expected.

    The run_comment_suffix defaults to empty string and can be set to
    tag each series with the condition it was taken at.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    sequencer = _make_real_iv_sequencer()

    assert sequencer.run_comment_suffix == ''

    sequencer.run_comment_suffix = ', T_set = 40 mK'
    assert sequencer.run_comment_suffix == ', T_set = 40 mK'


def _drive_iv_sweep(sequencer, monkeypatch):
    """
    Run a real IV_dIdV._run_iv_didv against a fake DAQ and instrument.

    The DAQ is a MagicMock rather than a hand written fake because the
    sweep touches a wide slice of its surface and this test cares
    about exactly one call on it, daq.run. The per bias point settling
    sleep is patched out, otherwise the configured 10 s times 23 bias
    points would make this test take four minutes.

    Parameters
    ----------
    sequencer : IV_dIdV
        The sequencer to drive.
    monkeypatch : pytest fixture
        Used to patch the settling sleep and the DAQ constructor.

    Returns
    -------
    run_comments : list of str
        The run comment passed to daq.run at each bias point.
    result : bool
        What _run_iv_didv returned.
    """
    run_comments = list()

    def record_run(**kwargs):
        """
        Record the run comment and report a successful data taking run.

        Parameters
        ----------
        **kwargs : dict
            The arguments the sequencer passed to daq.run.

        Returns
        -------
        success : bool
            Always True.
        """
        run_comments.append(kwargs.get('run_comment'))
        return True

    fake_daq = MagicMock()
    fake_daq.run.side_effect = record_run
    sequencer._daq = fake_daq

    fake_control = MagicMock()
    fake_control._config.get_tes_controller.return_value = 'feb'
    fake_control.set_tes_bias.return_value = True
    sequencer._instruments_inst = fake_control

    monkeypatch.setattr(iv_didv_module.daq, 'DAQ',
                        MagicMock(return_value=fake_daq))
    monkeypatch.setattr(iv_didv_module.time, 'sleep', lambda seconds: None)

    result = sequencer._run_iv_didv()

    return run_comments, result


def test_iv_didv_stamps_the_run_comment_suffix_into_every_series(
        monkeypatch):
    """
    The suffix is how each raw IV series records which temperature
    step it belongs to. If it never reached the run comment the data
    would still be written, so nothing would look wrong at the time,
    and the provenance would only be missed during offline analysis.

    Parameters
    ----------
    monkeypatch : pytest fixture
        Used to patch the settling sleep and the DAQ constructor.

    Returns
    -------
    None
    """
    sequencer = _make_real_iv_sequencer(online_iv=False)
    sequencer.run_comment_suffix = ', Gta step 3, T_set = 34 mK'

    run_comments, result = _drive_iv_sweep(sequencer, monkeypatch)

    assert result is True
    assert len(run_comments) > 1
    for run_comment in run_comments:
        assert run_comment.endswith(', Gta step 3, T_set = 34 mK')

    # the bias is still in there, the suffix is appended not replacing
    assert 'TES bias' in run_comments[0]


def test_iv_didv_leaves_the_run_comment_alone_by_default(monkeypatch):
    """
    Every existing run_iv_didv.py run supplies no suffix, and its run
    comments must come out exactly as they did before the accessor was
    added.

    Parameters
    ----------
    monkeypatch : pytest fixture
        Used to patch the settling sleep and the DAQ constructor.

    Returns
    -------
    None
    """
    sequencer = _make_real_iv_sequencer(online_iv=False)

    run_comments, result = _drive_iv_sweep(sequencer, monkeypatch)

    assert result is True
    for run_comment in run_comments:
        assert run_comment.startswith('IV: ')
        assert run_comment.endswith('uA')


def test_iv_didv_reports_failure_when_a_bias_cannot_be_applied(
        monkeypatch):
    """
    The driver reports a refused bias write by return value. Carrying
    on would record a full sweep of data taken at whatever bias the
    hardware was sitting at, and report it as good.

    Parameters
    ----------
    monkeypatch : pytest fixture
        Used to patch the settling sleep and the DAQ constructor.

    Returns
    -------
    None
    """
    sequencer = _make_real_iv_sequencer(online_iv=False)

    fake_daq = MagicMock()
    fake_daq.run.return_value = True
    sequencer._daq = fake_daq

    fake_control = MagicMock()
    fake_control._config.get_tes_controller.return_value = 'feb'
    fake_control.set_tes_bias.return_value = False
    sequencer._instruments_inst = fake_control

    monkeypatch.setattr(iv_didv_module.daq, 'DAQ',
                        MagicMock(return_value=fake_daq))
    monkeypatch.setattr(iv_didv_module.time, 'sleep', lambda seconds: None)

    result = sequencer._run_iv_didv()

    assert result is False
    assert fake_daq.run.call_count == 0


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
        setup_file=SETUP_FILE,
        dry_run=True,
    )
    return sweep


def test_build_iv_sequencer_configures_the_composed_sweep(monkeypatch):
    """
    GtaSweep owns temperature and sweeps one TES, and hands over the
    single instrument control it built. Every one of those is carried
    by a constructor argument, so a wrong argument is silent: dIdV
    left on would take dIdV data at every bias point, and the IV
    sequencer's own temperature sweep left on would fight this class
    over the fridge setpoint.

    Parameters
    ----------
    monkeypatch : pytest fixture
        Used to replace IV_dIdV with a recorder.

    Returns
    -------
    None
    """
    recorded = dict()

    class _RecordingIvSequencer:
        """
        Stand-in for IV_dIdV that records its constructor arguments.
        """

        def __init__(self, **kwargs):
            """
            Record every constructor argument.

            Parameters
            ----------
            **kwargs : dict
                The arguments GtaSweep passed.

            Returns
            -------
            None
            """
            recorded.update(kwargs)
            self.instrument_control = None

    monkeypatch.setattr(gta_sweep_module, 'IV_dIdV',
                        _RecordingIvSequencer)

    sweep, instrument = _sweep_with_fake_instrument()
    iv_sequencer = sweep._build_iv_sequencer()

    assert recorded['iv'] is True
    assert recorded['didv'] is False
    assert recorded['rp'] is False
    assert recorded['rn'] is False

    # this class owns the fridge setpoint
    assert recorded['temperature_sweep'] is False

    # load bearing: _run_iv_didv only re-creates the measurement
    # directories per invocation when the bias sweep is enabled, which
    # is what gives each temperature step its own raw data group
    assert recorded['tes_bias_sweep'] is True

    assert recorded['sweep_channels'] == [sweep._tes_channel]

    # one Control for the whole sweep, not one per temperature step
    assert iv_sequencer.instrument_control is sweep._instrument


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
    for index in range(1, len(temperatures)):
        assert temperatures[index] < temperatures[index - 1]


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
            setup_file=SETUP_FILE,
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

    with pytest.raises(ValueError, match='not_a_real_channel'):
        GtaSweep(
            sequencer_file=str(config_file),
            setup_file=SETUP_FILE,
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


def _write_config_variant(tmp_path, replacements, name='gta_variant.ini'):
    """
    Write a copy of the example Gta config with substitutions applied.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Directory to write the config file into.
    replacements : list of tuple
        (old_text, new_text) pairs applied in order.
    name : str
        File name to write.

    Returns
    -------
    config_path : str
        Path to the written config file.
    """
    with open('pytesdaq/config/gta_sweep.ini.example', 'r') as f:
        config_text = f.read()

    for old_text, new_text in replacements:
        assert old_text in config_text
        config_text = config_text.replace(old_text, new_text)

    config_path = tmp_path / name
    config_path.write_text(config_text)

    return str(config_path)


def test_dry_run_prints_the_bias_vector_that_will_actually_run(
        tmp_path, capsys):
    """
    With use_negative_tes_bias set, IV_dIdV negates every entry of the
    bias vector before using it. The dry run is the safety preview for
    a script that writes real currents into a TES, so printing the
    wrong sign there is the one place it must not happen.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Pytest fixture directory for writing the modified config file.
    capsys : pytest fixture
        Captures stdout and stderr produced during the test.

    Returns
    -------
    None
    """
    config_path = _write_config_variant(
        tmp_path,
        [('use_negative_tes_bias = false',
          'use_negative_tes_bias = true')]
    )

    sweep = _make_dry_sweep(config_file=config_path)
    sweep.run()

    printed = capsys.readouterr().out
    bias_line = ''
    for line in printed.splitlines():
        if 'TES bias sweep' in line:
            bias_line = line

    assert bias_line != ''
    assert '-80' in bias_line
    assert '-5.5' in bias_line


def test_dry_run_prints_a_vector_built_from_min_max_step(
        tmp_path, capsys):
    """
    The config documents min/max/step as an alternative to an explicit
    vector. Reading tes_bias_vect straight out of the config would
    print a vector that is never used in that mode.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Pytest fixture directory for writing the modified config file.
    capsys : pytest fixture
        Captures stdout and stderr produced during the test.

    Returns
    -------
    None
    """
    config_path = _write_config_variant(
        tmp_path,
        [('use_tes_bias_vect = true', 'use_tes_bias_vect = false'),
         ('tes_bias_vect = 80,60,40,30,20,15,12,10,8,7,6,5.5,5,4.5,4,'
          '3.5,3,2.5,2,1.5,1,0.5,0',
          'tes_bias_vect = 80,60,40\n'
          'tes_bias_max = 20\n'
          'tes_bias_t = 10\n'
          'tes_bias_sc = 5\n'
          'tes_bias_min = 0\n'
          'tes_bias_step_n = 5\n'
          'tes_bias_step_t = 2\n'
          'tes_bias_step_sc = 1')]
    )

    sweep = _make_dry_sweep(config_file=config_path)
    sweep.run()

    printed = capsys.readouterr().out
    bias_line = ''
    for line in printed.splitlines():
        if 'TES bias sweep' in line:
            bias_line = line

    assert bias_line != ''

    # the unused explicit vector must not be what got printed
    assert '60' not in bias_line
    assert '20' in bias_line


def test_dry_run_reports_an_unusable_bias_vector_without_crashing(
        tmp_path, capsys):
    """
    Dry run is the mode advertised as making no hardware contact and
    being safe to run at any time. A malformed bias vector must come
    back as a diagnostic naming the problem, not as a bare traceback
    out of an argparse script.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Pytest fixture directory for writing the modified config file.
    capsys : pytest fixture
        Captures stdout and stderr produced during the test.

    Returns
    -------
    None
    """
    config_path = _write_config_variant(
        tmp_path,
        [('tes_bias_vect = 80,60,40,30,20,15,12,10,8,7,6,5.5,5,4.5,4,'
          '3.5,3,2.5,2,1.5,1,0.5,0',
          'tes_bias_vect = 80,60,forty,20')]
    )

    sweep = _make_dry_sweep(config_file=config_path)
    sweep.run()

    printed = capsys.readouterr().out
    assert 'DRY RUN' in printed
    assert 'forty' in printed

    # the rest of the plan still printed, the dry run did not abort
    assert 'Temperature setpoints' in printed


def test_startup_reminder_keeps_the_pid_precondition(capsys):
    """
    The PID settings are set by hand before the run and this script
    never touches them. The runtime banner is what the operator reads
    at the moment they start a multi hour sweep, so the precondition
    has to survive there and not only in the argparse help.

    Parameters
    ----------
    capsys : pytest fixture
        Captures stdout and stderr produced during the test.

    Returns
    -------
    None
    """
    sweep, instrument = _sweep_with_fake_instrument()
    sweep._dry_run = False

    sweep._instantiate_drivers = lambda: None
    sweep._build_iv_sequencer = lambda: _FakeIvSequencer()
    sweep._create_output_directory = lambda: None
    sweep._save_diagnostics = lambda: None
    sweep._temperature_sweep.heater_to_zero = lambda: None
    sweep.run_single_step = (
        lambda temperature_mk=None, step_index=None: dict()
    )

    sweep.run()

    printed = capsys.readouterr().out
    assert 'PID' in printed

    # and the bracketing precondition the reminder was reworded to
    assert 'bracket' in printed


def test_warns_when_the_bias_vector_does_not_end_at_zero(
        tmp_path, capsys):
    """
    Between temperature steps the swept TES is left wherever the IV
    sweep ended, which is by design. If the vector does not end at 0
    that leaves it dissipating into the absorber for the whole settle
    of the next setpoint, which is exactly the heat load the sweep
    zeroes every other channel to avoid. Nothing can detect that
    offline, so it is called out at startup.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Pytest fixture directory for writing the modified config file.
    capsys : pytest fixture
        Captures stdout and stderr produced during the test.

    Returns
    -------
    None
    """
    config_path = _write_config_variant(
        tmp_path,
        [('tes_bias_vect = 80,60,40,30,20,15,12,10,8,7,6,5.5,5,4.5,4,'
          '3.5,3,2.5,2,1.5,1,0.5,0',
          'tes_bias_vect = 80,60,40,30,20,10,5,2')],
        name='gta_nonzero_end.ini'
    )

    sweep = GtaSweep(
        sequencer_file=config_path,
        setup_file=SETUP_FILE,
        dry_run=True,
    )
    sweep.run()

    printed = capsys.readouterr().out
    assert 'WARNING' in printed
    assert 'does not end at 0' in printed


def test_no_warning_when_the_bias_vector_ends_at_zero(capsys):
    """
    The shipped example config ends its vector at 0, which leaves the
    swept TES cold during the temperature transition. That must not
    produce the warning, otherwise the warning stops meaning anything.

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
    assert 'does not end at 0' not in printed


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
        self.relocks = list()

    # units the real Control accepts, which it validates before doing
    # anything. A fake that ignored the unit would let a uA/A mixup
    # through silently, and the real driver scales by 1e6 between them
    UNITS = ['uA', 'muA', 'A', 'mV']

    def get_tes_bias(self, detector_channel=None, unit=None):
        """
        Return the bias currently recorded for a channel.

        Parameters
        ----------
        detector_channel : str or None
            Detector channel name to read.
        unit : str or None
            Unit of the returned bias. Required, matching the real
            Control.get_tes_bias, which raises when it is missing.

        Returns
        -------
        bias : float
            The bias currently recorded for the channel [uA].
        """
        if unit is None or unit not in self.UNITS:
            raise ValueError('ERROR: TES bias unit required!')

        return self.biases[detector_channel]

    def set_tes_bias(self, bias, unit=None, detector_channel=None):
        """
        Record a bias write for a channel.

        Mirrors the real Control.set_tes_bias: the unit is validated
        before anything is written, and a bias given in A is scaled to
        uA, so a caller passing the wrong unit records a value that is
        wrong by a factor of a million rather than passing silently.

        Parameters
        ----------
        bias : float
            The bias value to write.
        unit : str or None
            Unit of the bias. Required, and one of UNITS.
        detector_channel : str or None
            Detector channel name to write to.

        Returns
        -------
        success : bool
            True, mimicking a successful hardware write.
        """
        if unit is None or unit not in self.UNITS:
            raise ValueError('ERROR: TES bias unit required!')

        if unit == 'A':
            bias = 1e6 * bias

        self.biases[detector_channel] = bias
        self.writes.append((detector_channel, bias))
        return True

    def relock(self, detector_channel=None):
        """
        Record a relock, along with the bias the channel was at.

        The bias is recorded because relocking a TES only works well
        while the device is in transition, so a test needs to see the
        bias at the moment of the relock and not merely that a relock
        happened at some point. The real Control.relock returns
        nothing, so neither does this.

        Parameters
        ----------
        detector_channel : str or None
            Detector channel name to relock.

        Returns
        -------
        None
        """
        self.relocks.append(
            (detector_channel, self.biases[detector_channel])
        )
        self.writes.append((detector_channel, 'relock'))


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


def test_zero_other_channels_aborts_when_a_write_reports_failure():
    """
    The real Control.set_tes_bias never raises when the hardware
    refuses a write: it returns None when no TES controller is
    available and False when the write itself failed. A channel that
    silently stays biased keeps dissipating power into the absorber
    for the whole sweep, which contaminates every recorded datapoint,
    so a falsy return must stop the run.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    sweep, instrument = _sweep_with_fake_instrument()
    sweep.capture_initial_biases()

    failing_channel = sweep._zero_channels[0]
    original_set = instrument.set_tes_bias

    def silently_failing_set(bias, unit=None, detector_channel=None):
        """
        Return False for one channel without raising, the way the real
        driver reports a refused write.

        Parameters
        ----------
        bias : float
            The bias value to write.
        unit : str or None
            Unit of the bias.
        detector_channel : str or None
            Detector channel name to write to.

        Returns
        -------
        success : bool
            False for the failing channel, True otherwise.
        """
        if detector_channel == failing_channel:
            return False
        return original_set(bias, unit=unit,
                            detector_channel=detector_channel)

    instrument.set_tes_bias = silently_failing_set

    with pytest.raises(RuntimeError, match='could not be set to 0'):
        sweep.zero_other_channels()


def test_zero_other_channels_aborts_when_no_controller_is_available():
    """
    Control.set_tes_bias returns None, not False, when there is no TES
    controller at all. That path must be treated as a failure too,
    otherwise a run with no controller zeroes nothing and reports
    success.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    sweep, instrument = _sweep_with_fake_instrument()
    sweep.capture_initial_biases()

    def no_controller_set(bias, unit=None, detector_channel=None):
        """
        Return None for every channel, the way the real driver behaves
        when no TES controller is available.

        Parameters
        ----------
        bias : float
            The bias value to write.
        unit : str or None
            Unit of the bias.
        detector_channel : str or None
            Detector channel name to write to.

        Returns
        -------
        None
        """
        return None

    instrument.set_tes_bias = no_controller_set

    with pytest.raises(RuntimeError, match='could not be set to 0'):
        sweep.zero_other_channels()


def test_restore_reports_an_error_when_a_write_reports_failure(capsys):
    """
    A restore that did not reach the hardware must not print the
    success message. The operator's only confirmation that the safe
    shutdown worked is what this prints, so reporting success on a
    refused write is worse than saying nothing.

    Parameters
    ----------
    capsys : pytest fixture
        Captures stdout and stderr produced during the test.

    Returns
    -------
    None
    """
    sweep, instrument = _sweep_with_fake_instrument()
    sweep.capture_initial_biases()
    sweep.zero_other_channels()

    failing_channel = sweep._zero_channels[0]
    original_set = instrument.set_tes_bias

    def silently_failing_set(bias, unit=None, detector_channel=None):
        """
        Return False for one channel without raising, the way the real
        driver reports a refused write.

        Parameters
        ----------
        bias : float
            The bias value to write.
        unit : str or None
            Unit of the bias.
        detector_channel : str or None
            Detector channel name to write to.

        Returns
        -------
        success : bool
            False for the failing channel, True otherwise.
        """
        if detector_channel == failing_channel:
            return False
        return original_set(bias, unit=unit,
                            detector_channel=detector_channel)

    instrument.set_tes_bias = silently_failing_set
    capsys.readouterr()

    sweep.restore_initial_biases()

    printed = capsys.readouterr().out
    failing_lines = list()
    for line in printed.splitlines():
        if failing_channel in line:
            failing_lines.append(line)

    assert len(failing_lines) > 0
    for line in failing_lines:
        assert 'ERROR' in line
        assert 'set back to its original' not in line


def test_capture_initial_biases_rejects_a_non_finite_bias():
    """
    Control._get_sensor_val returns NaN when it cannot identify the
    TES controller, and float(NaN) succeeds. Committing that would
    set the completeness flag and later write NaN back to the
    hardware while printing it as the original value, so a non-finite
    reading must fail the capture instead.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    sweep, instrument = _sweep_with_fake_instrument()
    instrument.biases[sweep._zero_channels[0]] = float('nan')

    with pytest.raises(ValueError, match='not a finite value'):
        sweep.capture_initial_biases()

    assert sweep._initial_biases_ua == dict()
    assert sweep._biases_captured is False


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

    with pytest.raises(RuntimeError, match='instrument not responding'):
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

    def __init__(self, run_result=True):
        """
        Set up a fake IV sequencer with a fixed group name and raw
        data path, and an empty log of run comment suffixes.

        Parameters
        ----------
        run_result : bool or None
            Value that _run_iv_didv returns. Defaults to True, which
            is what the real IV_dIdV._run_iv_didv returns on its
            success path. It returns False when a data taking run
            failed or a TES bias could not be applied. Anything else,
            None included, means the contract was broken and is
            treated as a failure by run_single_step.

        Returns
        -------
        None
        """
        self.instrument_control = None
        self.run_comment_suffix = ''
        self.runs = list()
        self.group_name = 'iv_I1_D20260728_T160000'
        self.raw_data_path = '/data/run74/raw/iv_I1_D20260728_T160000'
        self.run_result = run_result

    def _run_iv_didv(self):
        """
        Record the current run comment suffix and report the
        configured result.

        Parameters
        ----------
        None

        Returns
        -------
        success : bool or None
            The run_result this fake was constructed with.
        """
        self.runs.append(self.run_comment_suffix)
        return self.run_result


def test_run_single_step_treats_an_unknown_iv_result_as_failure(
        tmp_path, capsys):
    """
    _run_iv_didv returns True on success and False on failure. Any
    other value means its contract was broken, most likely by an
    early return added later, and must not be recorded in the science
    CSV as a good datapoint. Scoring it as a failure is the safe
    reading: a point wrongly flagged is discarded offline, a bad point
    wrongly trusted is fitted.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Pytest fixture directory used as the automation output root.
    capsys : pytest fixture
        Captures stdout and stderr produced during the test.

    Returns
    -------
    None
    """
    sweep, instrument = _sweep_with_fake_instrument()
    sweep._base_automation_data_path = str(tmp_path)
    sweep._create_output_directory()

    sweep._temperature_sweep.set_setpoint = (
        lambda temperature_mk=None: None
    )
    sweep._temperature_sweep.wait_for_temperature = (
        lambda temperature_mk=None: (True, [40.0])
    )
    sweep._temperature_sweep.measure_temperature = lambda: {
        'temperature_k': 0.040,
        'temperature_err_k': 0.0002,
        'fit_ok': True,
        'nb_samples': 50,
        'samples': [0.040],
    }

    sweep._iv_sequencer = _FakeIvSequencer(run_result=None)

    row = sweep.run_single_step(temperature_mk=40.0, step_index=0)

    assert row['iv_success'] is False
    assert 'WARNING' in capsys.readouterr().out


def test_run_single_step_writes_every_row_key_to_csv(tmp_path):
    """
    Test that run_single_step returns a row with exactly the declared
    CSV columns, correctly populated, and that the CSV on disk gains
    one row per call rather than being overwritten.

    Reading the CSV back (rather than only asserting on the returned
    dict) is what catches a regression such as _append_datapoint
    opening the file in write mode instead of append mode: that bug
    would silently discard every earlier step's row while every
    in-memory assertion on the latest row still passed.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Pytest fixture directory for writing the CSV file.

    Returns
    -------
    None
    """
    sweep, instrument = _sweep_with_fake_instrument()
    sweep._dry_run = False
    sweep.capture_initial_biases()

    temperatures = [0.0402, 0.0399, 0.0399, 0.0396]

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

    row_0 = sweep.run_single_step(temperature_mk=40.0, step_index=0)
    row_1 = sweep.run_single_step(temperature_mk=39.0, step_index=1)

    # every declared column is present, none extra
    assert set(row_0.keys()) == set(GtaSweep.CSV_COLUMNS)

    assert row_0['temperature_setpoint_mk'] == pytest.approx(40.0)
    assert row_0['mc_temperature_before_mk'] == pytest.approx(40.2)
    assert row_0['mc_temperature_after_mk'] == pytest.approx(39.9)
    assert row_0['temperature_drift_mk'] == pytest.approx(-0.3)
    assert row_0['temperature_ok'] is True
    assert row_0['tes_channel'] == sweep._tes_channel
    assert row_0['iv_group_name'] == 'iv_I1_D20260728_T160000'
    assert row_0['iv_success'] is True

    with open(sweep._csv_path, 'r', newline='') as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == GtaSweep.CSV_COLUMNS
        written_rows = list(reader)

    assert len(written_rows) == 2
    assert written_rows[0]['step'] == str(row_0['step'])
    assert written_rows[1]['step'] == str(row_1['step'])


def test_run_single_step_records_a_genuine_iv_failure(capsys):
    """
    Test that a data-taking failure reported by _run_iv_didv is
    recorded as iv_success = False and announced with a WARNING, not
    silently swallowed by the None-guard.

    _run_iv_didv returns False (not None) on a real data-taking
    error, so this pins the guard from the opposite side of
    test_run_single_step_writes_every_row_key_to_csv: that test's
    fake returns None (the real success path) and expects True here,
    this one returns False (the real failure path) and expects False.
    Together they mean deleting the guard, or inverting it, breaks
    one test or the other.

    Parameters
    ----------
    capsys : pytest fixture
        Captures stdout and stderr produced during the test.

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

    sweep._iv_sequencer = _FakeIvSequencer(run_result=False)
    sweep._csv_path = None

    row = sweep.run_single_step(temperature_mk=40.0, step_index=0)

    assert row['iv_success'] is False

    printed = capsys.readouterr().out
    assert 'WARNING' in printed
    assert 'reported a data-taking failure' in printed


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
    assert iv_sequencer.runs[0] == ', Gta step 0, T_set = 40 mK'


def test_run_single_step_records_a_timed_out_setpoint():
    """
    Test that a temperature timeout flags the row but still takes the
    IV sweep, since the recorded temperature is the measured one, not
    the setpoint.

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

    with pytest.raises(RuntimeError, match='instrument fell over'):
        sweep.run()

    for channel, bias in initial.items():
        assert instrument.biases[channel] == pytest.approx(bias)


def test_run_captures_biases_before_zeroing_them(tmp_path):
    """
    run() must capture every pre-run TES bias before it zeroes any of
    them. Reversed, the capture would record 0 uA as "the pre-run
    value" and shutdown would restore every TES to zero, silently
    discarding the bias points the operator set by hand, with nothing
    raised and nothing logged as wrong.

    This drives the whole of run() without pre-capturing, because
    calling capture_initial_biases() first is exactly what hides the
    ordering: the second-capture guard would short-circuit the capture
    inside run() and the reversal would leave no trace.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Pytest fixture directory used as the automation output root.

    Returns
    -------
    None
    """
    sweep, instrument = _sweep_with_fake_instrument()
    sweep._dry_run = False
    sweep._base_automation_data_path = str(tmp_path)

    starting_biases = dict(instrument.biases)
    assert sweep._biases_captured is False

    sweep._instantiate_drivers = lambda: None
    sweep._build_iv_sequencer = lambda: _FakeIvSequencer()
    sweep._temperature_sweep.heater_to_zero = lambda: None
    sweep._temperature_sweep.set_setpoint = (
        lambda temperature_mk=None: None
    )
    sweep._temperature_sweep.wait_for_temperature = (
        lambda temperature_mk=None: (True, [40.0])
    )
    sweep._temperature_sweep.measure_temperature = lambda: {
        'temperature_k': 0.040,
        'temperature_err_k': 0.0002,
        'fit_ok': True,
        'nb_samples': 50,
        'samples': [0.040],
    }

    sweep.run()

    # every channel is back at the bias it started at, not at 0
    for channel, bias in starting_biases.items():
        assert instrument.biases[channel] == pytest.approx(bias)

    # and the captured values are the real starting ones
    for channel, bias in starting_biases.items():
        assert sweep._initial_biases_ua[channel] == pytest.approx(bias)

    # the zeroing did happen, so this is not passing by doing nothing
    zeroed = list()
    for channel, bias in instrument.writes:
        if bias == 0:
            zeroed.append(channel)
    assert sorted(set(zeroed)) == sorted(sweep._zero_channels)


def test_shutdown_saves_diagnostics_even_when_a_restore_raises(
        tmp_path, capsys):
    """
    A restore that raises must not cost the diagnostics. They hold the
    temperature histories for the whole run, which is the only record
    of what the fridge actually did, and an unguarded raise here would
    also replace whatever exception was already propagating out of
    run()'s finally.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Pytest fixture directory used as the automation output root.
    capsys : pytest fixture
        Captures stdout and stderr produced during the test.

    Returns
    -------
    None
    """
    sweep, instrument = _sweep_with_fake_instrument()
    sweep._base_automation_data_path = str(tmp_path)
    sweep._create_output_directory()
    sweep.capture_initial_biases()

    def exploding_restore():
        """
        Raise unconditionally, standing in for a restore that fails in
        a way the per-channel handler does not catch.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        raise RuntimeError('restore fell over')

    sweep.restore_initial_biases = exploding_restore
    sweep._temperature_sweep.heater_to_zero = lambda: None

    sweep.shutdown()

    diagnostics_path = os.path.join(
        sweep._output_path, 'gta_sweep_diagnostics.p'
    )
    assert os.path.isfile(diagnostics_path)
    assert 'ERROR' in capsys.readouterr().out


def test_run_does_not_zero_a_bias_before_setup_succeeds():
    """
    A bad [iv_didv] config or a full disk must be discovered before
    any TES is driven out of transition. Zeroing first means the
    operator's devices are disturbed, and may need the SQUIDs
    relocking, to learn something that was knowable without touching
    the hardware at all.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    sweep, instrument = _sweep_with_fake_instrument()
    sweep._dry_run = False

    sweep._instantiate_drivers = lambda: None
    sweep._temperature_sweep.heater_to_zero = lambda: None
    sweep._save_diagnostics = lambda: None

    def failing_build():
        """
        Raise the way a malformed IV config would at construction.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        raise ValueError('bad iv config')

    sweep._build_iv_sequencer = failing_build

    with pytest.raises(ValueError, match='bad iv config'):
        sweep.run()

    # nothing was ever driven to 0
    for channel, bias in instrument.writes:
        assert bias != 0


def test_run_restores_biases_on_keyboard_interrupt():
    """
    A multi hour temperature sweep is far more likely to end with
    Ctrl-C than with an exception, so that path has to restore the
    biases and exit cleanly rather than propagate a traceback.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    sweep, instrument = _sweep_with_fake_instrument()
    sweep._dry_run = False
    starting_biases = dict(instrument.biases)

    sweep._instantiate_drivers = lambda: None
    sweep._build_iv_sequencer = lambda: _FakeIvSequencer()
    sweep._create_output_directory = lambda: None
    sweep._save_diagnostics = lambda: None
    sweep._temperature_sweep.heater_to_zero = lambda: None

    def interrupted_step(temperature_mk=None, step_index=None):
        """
        Raise KeyboardInterrupt, standing in for the operator pressing
        Ctrl-C partway through the sweep.

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
        raise KeyboardInterrupt()

    sweep.run_single_step = interrupted_step

    sweep.run()

    for channel, bias in starting_biases.items():
        assert instrument.biases[channel] == pytest.approx(bias)


def test_restore_keeps_going_when_interrupted_again():
    """
    A second Ctrl-C during shutdown must not strand the channels that
    have not been restored yet. KeyboardInterrupt is a BaseException,
    so a handler catching Exception lets it escape mid loop and leaves
    the remaining channels wherever the sweep put them.

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

    interrupting_channel = sweep._zero_channels[0]
    original_set = instrument.set_tes_bias
    interrupted = {'done': False}

    def interrupt_once(bias, unit=None, detector_channel=None):
        """
        Raise KeyboardInterrupt the first time one channel is written,
        then behave normally, standing in for a second Ctrl-C landing
        during the restore loop.

        Parameters
        ----------
        bias : float
            The bias value to write.
        unit : str or None
            Unit of the bias.
        detector_channel : str or None
            Detector channel name to write to.

        Returns
        -------
        success : bool
            True once the interrupt has already been raised.
        """
        if (detector_channel == interrupting_channel
                and not interrupted['done']):
            interrupted['done'] = True
            raise KeyboardInterrupt()
        return original_set(bias, unit=unit,
                            detector_channel=detector_channel)

    instrument.set_tes_bias = interrupt_once

    with pytest.raises(KeyboardInterrupt):
        sweep.restore_initial_biases()

    # every channel other than the interrupted one is back at its
    # pre-run bias, not left at 0
    for channel, bias in initial.items():
        if channel == interrupting_channel:
            continue
        assert instrument.biases[channel] == pytest.approx(bias)


def test_run_writes_the_whole_output_set_end_to_end(tmp_path):
    """
    Drive run() from end to end and check every artifact the sweep
    exists to produce: one CSV row per temperature setpoint, the
    config copy, the operator comment and the diagnostics pickle.

    Each of these is written by a single unguarded call inside run(),
    so without this the sweep could complete having silently recorded
    nothing at all.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Pytest fixture directory used as the automation output root.

    Returns
    -------
    None
    """
    sweep = GtaSweep(
        sequencer_file='pytesdaq/config/gta_sweep.ini.example',
        setup_file=SETUP_FILE,
        comment='Gta run for review',
        dry_run=True,
    )

    channels = [sweep._tes_channel] + sweep._zero_channels
    biases = dict()
    for index, channel in enumerate(channels):
        biases[channel] = 10.0 + index
    instrument = _FakeBiasInstrument(biases)
    sweep._instrument = instrument
    sweep._temperature_sweep.instrument = instrument

    sweep._dry_run = False
    sweep._base_automation_data_path = str(tmp_path)

    sweep._instantiate_drivers = lambda: None
    sweep._build_iv_sequencer = lambda: _FakeIvSequencer()
    sweep._temperature_sweep.heater_to_zero = lambda: None
    sweep._temperature_sweep.set_setpoint = (
        lambda temperature_mk=None: None
    )
    sweep._temperature_sweep.wait_for_temperature = (
        lambda temperature_mk=None: (True, [40.0])
    )
    sweep._temperature_sweep.measure_temperature = lambda: {
        'temperature_k': 0.040,
        'temperature_err_k': 0.0002,
        'fit_ok': True,
        'nb_samples': 50,
        'samples': [0.040],
    }

    nb_setpoints = len(sweep._temperature_sweep.temperature_list_mk)

    sweep.run()

    # one CSV row per temperature setpoint, with the declared header
    with open(sweep._csv_path, 'r', newline='') as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == GtaSweep.CSV_COLUMNS
        rows = list(reader)

    assert len(rows) == nb_setpoints

    # the config copy, so the run is reproducible
    assert os.path.isfile(
        os.path.join(sweep._output_path, 'gta_sweep.ini')
    )

    # the operator comment
    comment_path = os.path.join(sweep._output_path, 'comment.txt')
    assert os.path.isfile(comment_path)
    with open(comment_path, 'r') as f:
        assert 'Gta run for review' in f.read()

    # the diagnostics pickle, holding the temperature histories
    diagnostics_path = os.path.join(
        sweep._output_path, 'gta_sweep_diagnostics.p'
    )
    assert os.path.isfile(diagnostics_path)
    with open(diagnostics_path, 'rb') as f:
        diagnostics = pickle.load(f)
    assert len(diagnostics['steps']) == nb_setpoints


def test_restore_without_capture_touches_nothing(capsys):
    """
    A run that dies before capture_initial_biases must leave every
    bias alone. Writing a remembered value that was never read would
    put the TESs somewhere the operator never set them.

    Parameters
    ----------
    capsys : pytest fixture
        Captures stdout and stderr produced during the test.

    Returns
    -------
    None
    """
    sweep, instrument = _sweep_with_fake_instrument()
    assert sweep._biases_captured is False

    capsys.readouterr()
    sweep.restore_initial_biases()

    assert instrument.writes == []
    assert 'unknown' in capsys.readouterr().out


def test_rejects_a_negative_post_settle_wait(tmp_path):
    """
    A negative dwell is a config typo, and time.sleep would reject it
    hours into the run rather than at startup.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Pytest fixture directory for writing the modified config file.

    Returns
    -------
    None
    """
    config_path = _write_config_variant(
        tmp_path,
        [('post_temperature_settle_wait_s = 0',
          'post_temperature_settle_wait_s = -5')],
        name='gta_negative_dwell.ini'
    )

    with pytest.raises(ValueError, match='must not be negative'):
        GtaSweep(
            sequencer_file=config_path,
            setup_file=SETUP_FILE,
            dry_run=True,
        )


def test_shutdown_restores_biases_even_when_the_heater_fails(capsys):
    """
    A heater that will not accept a setpoint must not cost the bias
    restore. They are independent safety actions and the biases are
    the one that leaves devices dissipating if it is skipped.

    Parameters
    ----------
    capsys : pytest fixture
        Captures stdout and stderr produced during the test.

    Returns
    -------
    None
    """
    sweep, instrument = _sweep_with_fake_instrument()
    initial = dict(sweep.capture_initial_biases())
    sweep.zero_other_channels()

    def exploding_heater():
        """
        Raise unconditionally, standing in for a heater controller
        that is not responding.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        raise RuntimeError('heater not responding')

    sweep._temperature_sweep.heater_to_zero = exploding_heater
    sweep._save_diagnostics = lambda: None

    sweep.shutdown()

    for channel, bias in initial.items():
        assert instrument.biases[channel] == pytest.approx(bias)

    assert 'ERROR' in capsys.readouterr().out


def test_shutdown_without_an_instrument_touches_nothing():
    """
    A failure before the drivers were built leaves no instrument to
    talk to. shutdown() still runs from run()'s finally, so it has to
    cope rather than raise AttributeError on None and mask whatever
    actually went wrong.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    sweep = _make_dry_sweep()
    sweep._instrument = None

    sweep.shutdown()

    assert sweep._biases_captured is False


def test_create_output_directory_writes_csv_header_and_config_copy(
        tmp_path):
    """
    Test that _create_output_directory writes an empty CSV with the
    declared header and copies the sequencer config file into the
    timestamped output directory.

    Nothing else covers the artifact this feature exists to produce:
    the join table between raw IV series and bath temperature. This
    exercises the method directly rather than through the full run(),
    against a real (dry-run) sweep and the example config file.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Pytest fixture directory used as the automation data root.

    Returns
    -------
    None
    """
    sweep = _make_dry_sweep()
    sweep._base_automation_data_path = str(tmp_path)

    sweep._create_output_directory()

    with open(sweep._csv_path, 'r', newline='') as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == GtaSweep.CSV_COLUMNS
        assert list(reader) == []

    config_copy_path = sweep._output_path + '/gta_sweep.ini'
    assert os.path.isfile(config_copy_path)


def test_relock_all_channels_covers_every_tes_channel_once():
    """
    Test that relock_all_channels relocks the swept channel and every
    zeroed channel exactly once, and never touches a channel that is
    not a TES.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    sweep, instrument = _sweep_with_fake_instrument()

    sweep.relock_all_channels()

    relocked_channels = [channel for channel, bias in instrument.relocks]
    expected_channels = [sweep._tes_channel] + sweep._zero_channels

    assert sorted(relocked_channels) == sorted(expected_channels)

    for channel in sweep._non_tes_channels:
        assert channel not in relocked_channels


def test_prepare_detectors_for_iv_relocks_in_transition():
    """
    Test that every channel is relocked while it sits at its standard
    pre-run bias point, not at 0 uA.

    This is the whole reason the standard bias is restored before the
    relock: a TES sitting superconducting at 0 uA is much harder to
    pull back into lock than one sitting in transition. Asserting only
    that a relock happened would still pass if the relock were done
    after the re-zeroing, which is the failure mode this guards.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    sweep, instrument = _sweep_with_fake_instrument()
    initial = dict(sweep.capture_initial_biases())

    # the state the sweep is really in between temperature steps: the
    # other channels zeroed, the swept channel left superconducting at
    # the last point of the previous IV bias vector
    sweep.zero_other_channels()
    instrument.set_tes_bias(
        bias=0, unit='uA', detector_channel=sweep._tes_channel
    )

    sweep.prepare_detectors_for_iv()

    for channel, bias_at_relock in instrument.relocks:
        assert bias_at_relock == pytest.approx(initial[channel])


def test_prepare_detectors_for_iv_leaves_only_the_swept_channel_biased():
    """
    Test that after the relock the swept channel is back at its
    standard bias point and every other TES channel is at 0 uA again.

    A channel left biased after the relock would dissipate into the
    absorber for the whole IV sweep, which is exactly what zeroing
    exists to prevent.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    sweep, instrument = _sweep_with_fake_instrument()
    initial = dict(sweep.capture_initial_biases())

    sweep.prepare_detectors_for_iv()

    assert instrument.biases[sweep._tes_channel] == pytest.approx(
        initial[sweep._tes_channel]
    )

    for channel in sweep._zero_channels:
        assert instrument.biases[channel] == 0


def test_run_single_step_relocks_before_taking_any_iv_data():
    """
    Test that a temperature step relocks the detectors before the IV
    sweep runs, not after it.

    Relocking after the sweep would leave the whole IV curve taken
    with a TES that had lost lock when the bath temperature changed,
    which is the failure this feature exists to fix and which nothing
    in the recorded data flags afterwards.

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

    relocks_at_iv_time = list()

    class _RelockWatchingIvSequencer(_FakeIvSequencer):
        """
        Fake IV sequencer that snapshots the relock log at the moment
        the sweep starts.
        """

        def _run_iv_didv(self):
            """
            Record how many relocks had happened before this sweep,
            then behave like the plain fake.

            Parameters
            ----------
            None

            Returns
            -------
            success : bool or None
                The run_result this fake was constructed with.
            """
            relocks_at_iv_time.append(len(instrument.relocks))
            return super()._run_iv_didv()

    sweep._iv_sequencer = _RelockWatchingIvSequencer()
    sweep._csv_path = None

    sweep.run_single_step(temperature_mk=40.0, step_index=0)

    nb_tes_channels = 1 + len(sweep._zero_channels)
    assert relocks_at_iv_time == [nb_tes_channels]


def test_run_relocks_at_every_temperature_step(tmp_path):
    """
    Test that the relock happens at every temperature step of a full
    run, not only at the first one.

    The reported symptom was that only the first sweep produced good
    data, so a relock that ran once at startup would look correct in
    every single-step test and still leave the run broken.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Pytest fixture directory used as the automation output root.

    Returns
    -------
    None
    """
    sweep, instrument = _sweep_with_fake_instrument()
    sweep._dry_run = False
    sweep._base_automation_data_path = str(tmp_path)

    sweep._instantiate_drivers = lambda: None
    sweep._build_iv_sequencer = lambda: _FakeIvSequencer()
    sweep._temperature_sweep.heater_to_zero = lambda: None
    sweep._temperature_sweep.set_setpoint = (
        lambda temperature_mk=None: None
    )
    sweep._temperature_sweep.wait_for_temperature = (
        lambda temperature_mk=None: (True, [40.0])
    )
    sweep._temperature_sweep.measure_temperature = lambda: {
        'temperature_k': 0.040, 'temperature_err_k': 0.0002,
        'fit_ok': True, 'nb_samples': 50, 'samples': [0.040]}

    nb_setpoints = len(sweep._temperature_sweep.temperature_list_mk)
    nb_tes_channels = 1 + len(sweep._zero_channels)

    sweep.run()

    # one relock per TES channel per setpoint, plus the shutdown relock
    assert len(instrument.relocks) == (
        nb_tes_channels * (nb_setpoints + 1)
    )


def test_shutdown_relocks_after_restoring_the_standard_biases():
    """
    Test that shutdown relocks every TES channel, and does it after
    the biases are restored so the devices are handed back in
    transition rather than superconducting at the last point of the IV
    bias vector.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    sweep, instrument = _sweep_with_fake_instrument()
    initial = dict(sweep.capture_initial_biases())

    # the state the sweep really ends in: the swept channel left at the
    # last point of the IV bias vector, the others at 0 uA
    sweep.zero_other_channels()
    instrument.set_tes_bias(
        bias=0, unit='uA', detector_channel=sweep._tes_channel
    )

    sweep._temperature_sweep.heater_to_zero = lambda: None

    sweep.shutdown()

    assert len(instrument.relocks) == 1 + len(sweep._zero_channels)
    for channel, bias_at_relock in instrument.relocks:
        assert bias_at_relock == pytest.approx(initial[channel])


def test_shutdown_saves_diagnostics_even_when_the_relock_fails(
        tmp_path, capsys):
    """
    Test that a relock failure at shutdown is reported but does not
    stop the heater from being zeroed, the biases from being restored
    or the diagnostics from being written.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Pytest fixture directory used as the automation output root.
    capsys : pytest fixture
        Captures stdout and stderr produced during the test.

    Returns
    -------
    None
    """
    sweep, instrument = _sweep_with_fake_instrument()
    sweep._base_automation_data_path = str(tmp_path)
    sweep._create_output_directory()

    initial = dict(sweep.capture_initial_biases())
    sweep.zero_other_channels()

    def exploding_relock(detector_channel=None):
        """
        Raise the way a dead SQUID controller connection would.

        Parameters
        ----------
        detector_channel : str or None
            Detector channel name, unused.

        Returns
        -------
        None
        """
        raise RuntimeError('SQUID controller unreachable')

    instrument.relock = exploding_relock

    heater_calls = list()
    sweep._temperature_sweep.heater_to_zero = (
        lambda: heater_calls.append(True)
    )

    sweep.shutdown()

    assert heater_calls == [True]
    for channel, bias in initial.items():
        assert instrument.biases[channel] == pytest.approx(bias)

    diagnostics_path = os.path.join(
        sweep._output_path, 'gta_sweep_diagnostics.p'
    )
    assert os.path.isfile(diagnostics_path)
    assert 'ERROR relocking' in capsys.readouterr().out
