import pytest

from pytesdaq.sequencer.iv_didv import IV_dIdV


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
