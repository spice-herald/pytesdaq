import pytesdaq.config.settings as settings
import pytesdaq.instruments.control as instrument
from pytesdaq.instruments.lakeshore import Lakeshore
from pytesdaq.utils import connection_utils
import pprint as pprint
import pandas as pd


if __name__ == "__main__":

    # config
    config = settings.Config()
    lakeshore_setup = config.get_temperature_controller_setup('lakeshore')

    ip = None
    if 'ip' in lakeshore_setup['setup']:
        ip = lakeshore_setup['setup']['ip']

    port = None
    if 'port' in  lakeshore_setup['setup']:
        port = int(lakeshore_setup['setup']['port'])

    # instantiate
    myinstrument = Lakeshore(ip_address = ip, port=port)
    myinstrument.connect()
    
    # read ID
    id = myinstrument.serial_number
    print(id)


    resistance = myinstrument.get_resistance(channel_number=1)
    print(resistance)

    # channel status
    #myinstrument.enable_channel([11,12])
    #myinstrument.disable_channel(11)

    
    # close
    myinstrument.disconnect()
    
