import time
from pytesdaq.instruments.keithley import Keithley2400


if __name__ == "__main__":
    
    # connect
    keithley = Keithley2400('ASRL6::INSTR')
    
    
    # get IDN
    idn = myinstrument.get_idn()
    print('Device name: ' + idn)

    
    # ---------------------------
    # current source
    # ---------------------------
    print('Settings "current" source now')
    
    # set source
    keithley.set_source('current')
    
    # set current to 0.1 Amps
    keithley.set_current(0.1)
    
    
    # readback
    source  = keithley.get_source()
    current = keithley.get_current()
    print('Source is ' + source)
    print('Current is ' + current + ' Amps')


    print('Settings "voltage" source in 2 seconds')
    time.sleep(2)
    
    
    # ---------------------------
    # voltage source
    # ---------------------------
    # set source
    keithley.set_source('voltage')
    
    # set current to 0.1 Volts
    keithley.set_voltage(0.1)
    
    
    # readback
    source  = keithley.get_source()
    current = keithley.get_voltage()
    print('Source is ' + source)
    print('Voltage is ' + current + ' Volts')
    
    
    
    # enable output
    print('Enabling output 2 seconds!')
    keithley.enable_ouput()
    
    # Wait for a moment to stabilize (optional)
    time.sleep(2)
    
    print('disabling output')
    keithley.disable_output()
    
    
    # close 
    keithley.close()
    
