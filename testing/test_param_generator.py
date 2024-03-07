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

    print('')
    params = myinstrument._magnicon_inst.get_generator_params(controller_channel=3, generator_number=1)
    print('Sig Gen Params from Magnicon:', params)

    print('')
    amp_coerced, freq_coerced = myinstrument._magnicon_inst.set_generator_params(controller_channel=3,
        gen_num=1, phase_shift=180)
    print('Set generator phase shift to 180 with Magnicon.')
    params = myinstrument._magnicon_inst.get_generator_params(controller_channel=3, generator_number=1)
    print('Sig Gen Params from Magnicon:', params)

    print('')
    amp_coerced, freq_coerced = myinstrument._magnicon_inst.set_generator_params(controller_channel=3,
        gen_num=1, waveform='triangle')
    print('Set generator waveform to triangle with Magnicon.')
    params = myinstrument._magnicon_inst.get_generator_params(controller_channel=3, generator_number=1)
    print('Sig Gen Params from Magnicon:', params)

    print('')
    readback = myinstrument.set_signal_gen_params(tes_channel=3, signal_gen_num=1, source='feedback', frequency=120., current=100.)
    print('Set generator source to feedback (Ib), frequency to 120 Hz, and amplitude to 100 uA with Control.')
    params = myinstrument.get_signal_gen_params(tes_channel=3)
    print('Sig Gen Params from Control:', params)
    params = myinstrument._magnicon_inst.get_generator_params(controller_channel=3, generator_number=1)
    print('Sig Gen Params from Magnicon:', params)

    print('')
    amp_coerced, freq_coerced = myinstrument._magnicon_inst.set_generator_params(controller_channel=3,
        gen_num=1, freq_div=16, half_pp_offset='ON')
    print('Set generator frequency divider to 16 and half pp offset to "ON" with Magnicon.')
    params = myinstrument._magnicon_inst.get_generator_params(controller_channel=3, generator_number=1)
    print('Sig Gen Params from Magnicon:', params)

    print('')
    amp_coerced, freq_coerced = myinstrument._magnicon_inst.set_generator_params(controller_channel=3,
        gen_num=1, freq_div=0, gen_freq=50, pp_amplitude=90)
    print('Set generator frequency divider to 0 ("OFF"), frequency to 50 Hz, and amplitude to 90 uA with Magnicon.')
    params = myinstrument._magnicon_inst.get_generator_params(controller_channel=3, generator_number=1)
    print('Sig Gen Params from Magnicon:', params)

    print('')
    amp_coerced, freq_coerced = myinstrument._magnicon_inst.set_generator_params(controller_channel=3,
        gen_num=1, gen_freq=65, source='I', waveform='square', phase_shift=90, freq_div=8,
        half_pp_offset='OFF', pp_amplitude=75)
    print('Set generator parameters with Magnicon.')
    params = myinstrument._magnicon_inst.get_generator_params(controller_channel=3, generator_number=1)
    print('Sig Gen Params from Magnicon:', params)

#    readback = myinstrument.set_signal_gen_params(tes_channel=3, signal_gen_num=1, source='tes', current=100, frequency=65., shape='square', phase_shift=90, freq_div=8, half_pp_offset='OFF')

