from  pytesdaq.instruments.agilent import Agilent33500B
if __name__ == "__main__":

    
    # VISA Address
    # visa_address = 'GPIB::10::INSTR'
    # visa_address = 'COM1'
    # visa_address = 'TCPIP::192.168.0.7::1234::SOCKET'
    visa_address = 'TCPIP0::169.254.5.21::inst0::INSTR'
    visa_address = 'TCPIP::131.243.51.117::inst0::INSTR'
    visa_address = 'TCPIP::131.243.51.234::inst0::INSTR'
    
    # Instantiate instrument
    myinstrument = Agilent33500B(visa_address, attenuation=1)

    # get IDN
    idn = myinstrument.get_idn()
    print('Device name: ' + idn)

    # set amplitude Vpp
    myinstrument.set_amplitude(0.005)
    
    # get amplitude
    amplitude = myinstrument.get_amplitude()
    print('Amplitude = ' + str(amplitude*1000) + ' mVpp')


    # set frequency
    myinstrument.set_frequency(500)
    
    # get frequency
    frequency = myinstrument.get_frequency()
    print('Frequency = ' + str(frequency) + ' Hz')

    #get signal shape
    shape = myinstrument.get_shape()
    print('Shape = ' + shape )

    myinstrument.set_generator_onoff(0)
