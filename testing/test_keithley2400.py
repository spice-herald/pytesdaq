import time
from pytesdaq.instruments.keithley import Keithley2400


if __name__ == "__main__":
    
    # connect
    keithley = Keithley2400('ASRL3::INSTR')
    #print("connected...")
    #time.sleep(10)
    
    
    
    # get IDN
    idn = keithley.get_idn()
    #print('Device name: ' + idn)
    #time.sleep(10)

    
    # ---------------------------
    # current source
    # ---------------------------
    print('Settings "voltage" source now')
    
    # set source
    #keithley.set_source('voltage')
    
    # set voltage to 0.1 volts
    #keithley.set_voltage(0.1)
    
    
    # readback
    #source  = keithley.get_source()
    #voltage = keithley.get_voltage()
    #print('Source is ' + source)
    #print('Voltage is ' + str(voltage) + ' Volts')


    #print('Settings "voltage" source in 2 seconds')
    #time.sleep(10)
    
    
    # ---------------------------
    # voltage source
    # ---------------------------
    # set source
    keithley.set_source('voltage',fixed=True,autorange=False)
    print("set_source")
    #time.sleep(10)
    keithley.set_current_compliance(1.1e-2)
    print("set_current_compliance")
    #time.sleep(10)
    keithley.set_current_measurement_range(1e-2)
    print("set_current_measurement_range")
    #time.sleep(10)
    
    # set current to 0.1 Volts
    keithley.set_voltage(0.8)
    print("set_voltage")
    #time.sleep(10)

    
    # readback
    source  = keithley.get_source()
    print("get_source")
    #time.sleep(10)
    voltage = keithley.get_voltage()
    print("get_voltage")
    #time.sleep(10)
    current = keithley.get_current() # the beeping step
    print("get_current")
    #time.sleep(10)
    print('Source is ' + source)
    print('Voltage is ' + str(voltage) + ' Volts')
    print('Current is' + str(current) + 'Amps')
    
    
    
    # enable output
    print('Enabling output 2 seconds!')
    #keithley.showARM_current()
    keithley.enable_output()
    print("enable_output")
    #time.sleep(10)
    keithley.measure_current() #the beeping step
    print("measure_current")
    #time.sleep(10)
    
    # Wait for a moment to stabilize (optional)
    #time.sleep(2)
   # print('disabling output')
    #keithley.disable_output()
    
    
    # close 
    keithley.close()
    print("close")
    #time.sleep(10)

    
