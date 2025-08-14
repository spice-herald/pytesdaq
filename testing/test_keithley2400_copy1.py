import time
from pytesdaq.instruments.keithley import Keithley2400


if __name__ == "__main__":
    
    # connect
    keithley = Keithley2400('ASRL2::INSTR')
    print("connected...")
    #time.sleep(10)
    
    
    
    # get IDN
    idn = keithley.get_idn()
    print('Device name: ' + idn)
    #time.sleep(10)

    
    # ---------------------------
    # current source
    # ---------------------------
    print('Settings "current" source now')
    
    # set source
    keithley.set_source('current', fixed=True, autorange=True)
    
    keithley.set_current_compliance(1e-1)

    keithley.write(':SENS:VOLT:PROT 15')


    # set voltage to 0.1 volts
    #keithley.seit_voltage(0.1)
    
    
    # readback
    #source  = keithley.get_source()
    #voltage = keithley.get_voltage()
    #print('Source is ' + source)
    #print('Voltage is ' + str(voltage) + ' Volts')


    #print('Settings "voltage" source in 2 seconds')
    #time.sleep(10)
    
    print('setting current to 1.0mA')
    keithley.set_current(0.0010)
    
    # ---------------------------
    # voltage source
    # ---------------------------
    # set source
    #keithley.set_source('voltage',fixed=True,autorange=False)
   # print("set_source")
    #time.sleep(10)
    #keithley.set_current_compliance(1.1e-2)
   # print("set_current_compliance")
    #time.sleep(10)
    #keithley.set_current_measurement_range(1e-2)
   # print("set_current_measurement_range")
    time.sleep(3)
    
    # set current to 0.1 Volts
    #keithley.set_voltage(0.8)
   # print("set_voltage")
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
    
    time.sleep(4)
    
    # enable output
    print('Enabling output 2 seconds!')
   # keithley.showARM_current()
    keithley.enable_output()
    print("enable_output")
    time.sleep(2)
   # keithley.measure_current() #the beeping step
   # print("measure_current")
    time.sleep(3)
    
    # Wait for a moment to stabilize (optional)
    time.sleep(2)
    print('disabling output')
    keithley.disable_output()
    
    
    print('setting current to 11uA')

    
    # keithley.set_source('current', fixed=True, autorange=False)

    keithley.set_current(11e-6)

    keithley.enable_output()
    time.sleep(2)
    keithley.measure_current()
    time.sleep(4)
    keithley.disable_output()

    '''
    #source  = keithley.get_source()
    #print("get_source")
   # voltage = keithley.get_voltage()
   # print("get_voltage")
   # current = keithley.get_current() # the beeping step
   # print("get_current")
   # print('Source is ' + source)
   # print('Voltage is ' + str(voltage) + ' Volts')
   # print('Current is' + str(current) + 'Amps')

    time.sleep(4)

    # enable output
    print('Enabling output 2 seconds!')
    keithley.enable_output()
    print("enable_output")
    time.sleep(2)
    keithley.measure_current() #the beeping step
    print("measure_current")
    time.sleep(3)


    # Wait for a moment to stabilize (optional)
    time.sleep(2)
    print('disabling output')
    keithley.disable_output()

    '''

    # close 
    keithley.close()
    print("close")
    #time.sleep(10)

    
