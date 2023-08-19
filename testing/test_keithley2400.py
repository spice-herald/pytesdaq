import time
from pytesdaq.instruments.keithley import Keithley2400


if __name__ == "__main__":
    
    # connect
    keithley = Keithley2400('ASRL3::INSTR')
    
    
    # get IDN
    idn = keithley.get_idn()
    print('Device name: ' + idn)

    
    # ---------------------------
    # current source
    # ---------------------------
    print('Settings "voltage" source now')
    
    # set source
    keithley.set_source('voltage')
    
    # set voltage to 0.1 volts
    keithley.set_voltage(0.1)
    
    
    # readback
    source  = keithley.get_source()
    voltage = keithley.get_voltage()
    print('Source is ' + source)
    print('Voltage is ' + str(voltage) + ' Volts')


    print('Settings "voltage" source in 2 seconds')
    time.sleep(2)
    
    
    # ---------------------------
    # voltage source
    # ---------------------------
    # set source
    keithley.set_source('voltage')
    keithley.set_current_compliance(1e-3)
    
    # set current to 0.1 Volts
    keithley.set_voltage(0.1)
    
    
    # readback
    source  = keithley.get_source()
    voltage = keithley.get_voltage()
    print('Source is ' + source)
    print('Voltage is ' + str(voltage) + ' Volts')
    
    
    
    # enable output
    print('Enabling output 2 seconds!')
    keithley.showARM_current()
    keithley.enable_output()
    keithley.measure_current()
    
    # Wait for a moment to stabilize (optional)
    #time.sleep(2)
    
   # print('disabling output')
    #keithley.disable_output()
    
    
    # close 
    keithley.close()
    
