import pytesdaq.config.settings as settings
import pytesdaq.instruments.control as instrument
import pytesdaq.instruments.magnicon as magnicon
from pytesdaq.utils import connection_utils
import pprint as pprint
import pandas as pd

if __name__ == "__main__":

    # config
    config = settings.Config()
    myconnections = config.get_adc_connections()



    # instantiate
    myinstrument = instrument.Control(dummy_mode=False, verbose=True)

    # --------------
    # Sig gen
    # --------------
    myinstrument.set_signal_gen_params(tes_channel=2, source='feedback',
                                       shape='triangle', frequency=110, amplitude=150)
    data = myinstrument.get_signal_gen_params(tes_channel=2)
    myinstrument.set_signal_gen_onoff('off',tes_channel=2)

    #data = myinstrument.get_signal_gen_onoff(tes_channel=2)
    print(data)
    #print(bias)


    
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
 #   bias = myinstrument.get_squid_bias(tes_channel=2)
   

    
    # Using detector_channel name
    #bias = myinstrument.get_tes_bias(detector_channel='G124_PBS1')
    
    # dummy mode -> all values = 1
#    print(bias)
