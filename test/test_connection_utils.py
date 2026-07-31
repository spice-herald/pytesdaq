import os

from pytesdaq.utils import connection_utils
import pytesdaq.config.settings as settings
from pytesdaq.io import hdf5

# committed test fixture, so the suite runs on a fresh clone
SETUP_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'fixtures',
    'setup_test.ini'
)


def test_explicit_tes_field_marks_a_real_tes_channel():
    """
    Mark a connection line as a real TES channel when it declares a
    "tes:" field, since a connection line that declares "tes:" is a
    front end board TES.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    name_val_list, name_list, val_list = (
        connection_utils.extract_adc_connection(
            'detector:GaAs_800x200, tes:A, controller:feb1_A'
        )
    )
    result = dict(zip(name_list, val_list))
    assert result['is_tes_channel'] is True
    assert result['tes_channel'] == 'A'


def test_missing_tes_field_is_not_a_tes_channel():
    """
    Mark a connection line without a "tes:" field as not a TES
    channel, since the TTL input has no "tes:" field and must never be
    biased.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    name_val_list, name_list, val_list = (
        connection_utils.extract_adc_connection(
            'detector:rigolTTL, controller:ttl_ttl'
        )
    )
    result = dict(zip(name_list, val_list))
    assert result['is_tes_channel'] is False


def test_missing_tes_field_still_falls_back_to_controller_channel():
    """
    Fall back to the controller channel for tes_channel when no
    "tes:" field is present, since the synthesized tes_channel is
    unchanged and existing callers that index on tes_channel keep
    working.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    name_val_list, name_list, val_list = (
        connection_utils.extract_adc_connection(
            'detector:AccelerometerX, controller:accelerometer_X'
        )
    )
    result = dict(zip(name_list, val_list))
    assert result['tes_channel'] == 'X'
    assert result['is_tes_channel'] is False


def test_connection_table_from_setup_file_has_the_column():
    """
    Verify that the connection table built from the setup file
    includes the is_tes_channel column, with at least one TES channel
    marked True.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """

    config = settings.Config(setup_file=SETUP_FILE)
    connection_table = config.get_adc_connections()

    assert 'is_tes_channel' in connection_table.columns
    assert connection_table['is_tes_channel'].any()


def test_connection_table_from_raw_data_does_not_claim_tes_status():
    """
    A connection table rebuilt from raw data metadata cannot know
    which channels were real TES channels.

    The synthesized "tes:" token is written into the metadata for
    every channel, TTL and accelerometer included, so re-parsing it
    would report is_tes_channel True for all of them. Reporting True
    there would invite a caller to bias an accelerometer readout, so
    the column reports None instead: unknown, not yes.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    metadata = {
        'adc_list': ['adc1'],
        'groups': {
            'adc1': {
                'connection0': ['detector:TestTES_A', 'tes:A',
                                'controller:feb1_A'],
                'connection4': ['detector:rigolTTL', 'tes:ttl',
                                'controller:ttl_ttl'],
            }
        }
    }

    table = hdf5.H5Reader().get_connection_table(metadata=metadata)

    for value in table['is_tes_channel']:
        assert value is None
