from  pytesdaq.instruments.keysight import KeysightFuncGenerator
if __name__ == "__main__":

    
    # VISA Address
    #visa_address = 'GPIB0::9::INSTR'
    # visa_address = 'COM1'
    visa_address = 'TCPIP0::169.254.5.21::inst0::INSTR'
    
    # Instantiate instrument
    myinstrument = KeysightFuncGenerator(visa_address)

    # get IDN
    idn = myinstrument.get_idn()
    print('Device name: ' + idn)

    # set amplitude Vpp
    myinstrument.set_amplitude(0.2)
    
    # get amplitude
    amplitude = myinstrument.get_amplitude()
    print('Amplitude = ' + str(amplitude*1000) + ' mVpp')


    # set frequency
    myinstrument.set_frequency(50)
    
    # get frequency
    frequency = myinstrument.get_frequency()
    print('Frequency = ' + str(frequency) + ' Hz')

    #get signal shape
    shape = myinstrument.get_shape()
    print('Shape = ' + shape )

