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
    #print(mag_control_info)
    mag_conn_info = config.get_magnicon_connection_info()
    #print(mag_conn_info)



    # instantiate
    myinstrument = instrument.Control(dummy_mode=False,verbose=True)


    # ------------
    # Set TES bias
    # ------------
    # using channel number 
    #myinstrument.set_tes_bias(20, tes_channel=1)
    
    # using detector name_channel
    #myinstrument.set_tes_bias(20, detector_channel='G124_PAS2')
    
    # ------------
    # Get TES bias
    # ------------
    # using channel number 
#    bias = myinstrument.get_tes_bias(tes_channel=2)
#    print(myinstrument.read_all(tes_channel_list=[2]))
    bias = myinstrument.get_squid_bias(tes_channel=2)
    print('Bias', bias)
    readback = myinstrument.set_squid_bias(30., tes_channel=2)
    print('Readback', readback)
    bias = myinstrument.get_squid_bias(tes_channel=2)
    print('Bias', bias)

    
    # Using detector_channel name
    #bias = myinstrument.get_tes_bias(detector_channel='G124_PBS1')
    
    # dummy mode -> all values = 1
#    print(bias)
