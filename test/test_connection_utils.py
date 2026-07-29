from pytesdaq.utils import connection_utils


def test_explicit_tes_field_marks_a_real_tes_channel():
    # a connection line that declares "tes:" is a front end board TES
    name_val_list, name_list, val_list = (
        connection_utils.extract_adc_connection(
            'detector:GaAs_800x200, tes:A, controller:feb1_A'
        )
    )
    result = dict(zip(name_list, val_list))
    assert result['is_tes_channel'] is True
    assert result['tes_channel'] == 'A'


def test_missing_tes_field_is_not_a_tes_channel():
    # the TTL input has no "tes:" field, so it must never be biased
    name_val_list, name_list, val_list = (
        connection_utils.extract_adc_connection(
            'detector:rigolTTL, controller:ttl_ttl'
        )
    )
    result = dict(zip(name_list, val_list))
    assert result['is_tes_channel'] is False


def test_missing_tes_field_still_falls_back_to_controller_channel():
    # the synthesized tes_channel is unchanged, so existing callers
    # that index on tes_channel keep working
    name_val_list, name_list, val_list = (
        connection_utils.extract_adc_connection(
            'detector:AccelerometerX, controller:accelerometer_X'
        )
    )
    result = dict(zip(name_list, val_list))
    assert result['tes_channel'] == 'X'
    assert result['is_tes_channel'] is False


def test_connection_table_from_setup_file_has_the_column():
    import pytesdaq.config.settings as settings

    config = settings.Config(setup_file='pytesdaq/config/setup.ini')
    connection_table = config.get_adc_connections()

    assert 'is_tes_channel' in connection_table.columns
    assert connection_table['is_tes_channel'].any()
