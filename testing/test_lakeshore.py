import pytesdaq.config.settings as settings
import pytesdaq.instruments.control as instrument
import pytesdaq.instruments.tempcontrollers as tempcontrollers
from pytesdaq.utils import connection_utils
import pprint as pprint
import pandas as pd

if __name__ == "__main__":

    # config
    config = settings.Config()
    address = config.get_temperature_controller_address('lakeshore')


    # instantiate
    myinstrument = tempcontrollers.LakeshoreTempController(address)

    
    # read ID
    id = myinstrument.get_idn()
    print(id)


    # channel status
    myinstrument.enable_channel([11,12])
    myinstrument.disable_channel(11)

    
    # close
    myinstrument.close()
    
