import pytesdaq.config.settings as settings
import pytesdaq.instruments.control as instrument
import pytesdaq.instruments.magnicon as magnicon
from pytesdaq.utils import connection_utils
import pprint as pprint
from IPython.core.display import HTML
import pandas as pd


config = settings.Config()
myconnections = config.get_adc_connections()
test = config.get_adc_setup('adc1')
print(test)


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
#bias = myinstrument.get_preamp_total_gain(tes_channel=1)

# Using detector_channel name
#bias = myinstrument.get_tes_bias(detector_channel='G124_PBS1')


# normalization
#norm = myinstrument.get_output_total_gain(tes_channel=1)
#norm = myinstrument.get_open_loop_preamp_norm(tes_channel=1)
#norm = abs(myinstrument.get_open_loop_full_norm(tes_channel=1))
#norm = myinstrument.get_volts_to_amps_close_loop_norm(tes_channel=1)
#print(norm)


data = myinstrument.read_all(tes_channel_list=[1,2,3,4])
# dummy mode -> all values = 1
print(data)

