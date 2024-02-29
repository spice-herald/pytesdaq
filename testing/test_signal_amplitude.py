import pytesdaq.config.settings as settings
import pytesdaq.instruments.control as instrument
import pytesdaq.instruments.magnicon as magnicon
from pytesdaq.utils import connection_utils
import pprint as pprint
import pandas as pd

if __name__ == "__main__":

    # config
    config = settings.Config()
    mag_control_info = config.get_magnicon_controller_info()
    print(mag_control_info)
    mag_conn_info = config.get_magnicon_connection_info()
    print(mag_conn_info)

    # instantiate
    myinstrument = instrument.Control(dummy_mode=False,verbose=True)

    # ------------
    # Get TES bias
    # ------------
    # using channel number 
    print('')
    bias = myinstrument.get_squid_bias(tes_channel=3)
    print('Get SQUID Bias from Control: %.1f uA' % bias)
    squid_bias = 30.
    readback = myinstrument.set_squid_bias(squid_bias, tes_channel=3)
    print('We have set SQUID Bias to %.1f uA; Readback:' % squid_bias, readback)
    bias = myinstrument.get_squid_bias(tes_channel=3)
    print('Get SQUID Bias from Control: %.1f uA' % bias)

    print('')
    params = myinstrument.get_signal_gen_params(tes_channel=3)
    print('Sig Gen Params from Control:')
    print(params)
    params = myinstrument._magnicon_inst.get_generator_params(controller_channel=3, generator_number=1)
    print('Sig Gen Params from Magnicon:')
    print(params)

    print('')
    amp_coerced, freq_coerced = myinstrument._magnicon_inst.set_generator_params(controller_channel=3,
        gen_num=1, gen_freq=120, source='I', waveform='sawtoothpos', phase_shift=0, freq_div=0, half_pp_offset='OFF', pp_amplitude=75)
    print('We have set some new generator parameters with Magnicon. ' +
        'Coerced amplitude: %.1f uA, Coerced frequency: %.1f Hz' % (amp_coerced, freq_coerced))
    params = myinstrument.get_signal_gen_params(tes_channel=3)
    print('Sig Gen Params from Control:')
    print(params)
    params = myinstrument._magnicon_inst.get_generator_params(controller_channel=3, generator_number=1)
    print('Sig Gen Params from Magnicon:')
    print(params)

    print('')
    readback = myinstrument.set_signal_gen_params(tes_channel=3, source='tes', signal_gen_num=1, current=100, frequency=65., shape='square',
        phase_shift=90, freq_div=8, half_pp_offset='OFF')
    print('We have set some new generator parameters with Control. Readback:', readback)
    params = myinstrument.get_signal_gen_params(tes_channel=3)
    print('Sig Gen Params from Control:')
    print(params)
    params = myinstrument._magnicon_inst.get_generator_params(controller_channel=3, generator_number=1)
    print('Sig Gen Params from Magnicon:')
    print(params)


