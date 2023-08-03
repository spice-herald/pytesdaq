from  pytesdaq.instruments.keysight import KeysightDSOX1200



if __name__ == "__main__":
   
    visa_address = 'TCPIP0::131.243.51.193::hislip0::INSTR'

    
    # Instantiate instrument
    myinstrument = KeysightDSOX1200(visa_address)

    # get IDN
    idn = myinstrument.get_idn()
    print('Device name: ' + idn)


    # ------------------
    # Set square wave
    # ------------------
    
    # set square wave
    myinstrument.set_shape('square')
    
    # set amplitude Vpp
    myinstrument.set_amplitude(0.1)

    # set frequency
    myinstrument.set_frequency(50)

    # ------------------
    # Readback
    # ------------------
    
    amplitude = myinstrument.get_amplitude()
    print('Amplitude = ' + str(amplitude) + ' V')
    
    # get frequency
    frequency = myinstrument.get_frequency()
    print('Frequency = ' + str(frequency) + ' Hz')

    #get signal shape
    shape = myinstrument.get_shape()
    print('Shape = ' + shape )



    # enable output
    print('Enabling output')
    myinstrument.set_generator_onoff('on')


    myinstrument.close()



