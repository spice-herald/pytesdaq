from pytesdaq.instruments.rigol import RigolDG800

if __name__ == "__main__":

    
    # VISA Address
    visa_address = 'USB0::0x1AB1::1603::DG8A204201623::INSTR'

    # instantiate and connect
    myinstrument = RigolDG800(visa_address)
    print(f'\nDevice name: {myinstrument.device_idn}')

    # channel
    source = 1

    # read current paramters
    
    shape = myinstrument.get_shape(source=source)
    voltage =  myinstrument.get_amplitude(source=source, unit='Vpp')
    frequency = myinstrument.get_frequency(source=source, unit='Hz')
    phase = myinstrument.get_frequency(source=source)
    offset = myinstrument.get_offset(source=source, unit='V')


    print(f'Shape = {shape}')
    print(f'Amplitude = {voltage} Vpp')
    print(f'Frequency = {frequency} Hz')
    print(f'Phase = {phase} degrees')
    print(f'Offset = {offset} V')


    # test write
    myinstrument.set_amplitude(0.2, source=source, unit='Vpp')
    myinstrument.set_offset(0.1, source=source, unit='V')
    myinstrument.set_shape('square', source=source)
    myinstrument.set_phase(10, source=source)
    myinstrument.set_frequency(200, source=source)




    # read back
    shape = myinstrument.get_shape(source=source)
    voltage =  myinstrument.get_amplitude(source=source, unit='Vpp')
    frequency = myinstrument.get_frequency(source=source, unit='Hz')
    phase = myinstrument.get_frequency(source=source)
    offset = myinstrument.get_offset(source=source, unit='V')


    print(f'Shape = {shape}')
    print(f'Amplitude = {voltage} Vpp')
    print(f'Frequency = {frequency} Hz')
    print(f'Phase = {phase} degrees')
    print(f'Offset = {offset} V')

    
