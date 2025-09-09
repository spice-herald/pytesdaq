from  pytesdaq.instruments.agilent import Agilent33500B
import sys
if __name__ == "__main__":

    #setpoint = float(sys.argv[1])
    
    # VISA Address
    #visa_address = 'USB0::2391::9991::MY62000634::0::INSTR'
    visa_address = 'TCPIP::192.168.10.1::inst0::INSTR'
    #visa_address = 'GPIB::10::INSTR'

    # Instantiate instrument
    myinstrument = Agilent33500B(visa_address, attenuation=1)

    # get IDN
    idn = myinstrument.get_idn()
    print('Device name: ' + idn)

    #myinstrument.set_shape('triangle')
    #get signal shape
    shape = myinstrument.get_shape()
    print('Shape = ' + shape )


    
    # set amplitude Vpp
    #myinstrument.set_amplitude(5)
    
    # get amplitude
    amplitude = myinstrument.get_amplitude()
    print('Amplitude = ' + str(amplitude*1000) + ' mVpp')

    # phase:
    # get amplitude
    #myinstrument.set_phase(50)
    phase = myinstrument.get_phase()
    print('Phase = ' + str(phase))


    # offset
    #myinstrument.set_offset(0.05)
    
    offset = myinstrument.get_offset()
    print('Offset = ' + str(offset*1e3) + ' mV')


    
    # set frequency
    #myinstrument.set_frequency(50)
    
    # get frequency
    frequency = myinstrument.get_frequency()
    print('Frequency = ' + str(frequency) + ' Hz')


   
    #resistance = myinstrument.get_load_resistance()
    #print(f'Load resistance: {resistance}')

    # myinstrument.set_load_resistance(2047)
    #myinstrument.set_shape('dc')

    # myinstrument.set_offset(setpoint) #V
    # myinstrument.set_generator_onoff('on')


