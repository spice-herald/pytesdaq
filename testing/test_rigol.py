import sys
#sys.path.insert(0, '/home/mwilliams/pytesdaq')
from pytesdaq.instruments.rigol import RigolDG800
import pyvisa

if __name__ == "__main__":

    
    # VISA Address
    visa_address = 'USB0::0x1AB1::1603::DG8A211800738::INSTR'
    #visa_address = 'TCPIP:192.168.001.102::INSTR'

    # instantiate and connect
    myinstrument = RigolDG800(visa_address)
    print(f'\nDevice name: {myinstrument.device_idn}')
    

    # channel
    source = 1

    # read current paramters
    
    shape = myinstrument.get_shape(source=source)
    voltage_low =  myinstrument.get_amplitude(source=source, unit='Vpp', level='low')
    voltage_high =  myinstrument.get_amplitude(source=source, unit='Vpp', level='high')
    frequency = myinstrument.get_frequency(source=source, unit='Hz')
    phase = myinstrument.get_phase(source=source)
    offset = myinstrument.get_offset(source=source, unit='V')
    output_state = myinstrument.get_generator_onoff(source=source)

    print(f'Shape = {shape}')
    print(f'Voltgage HIGH = {voltage_high} Vpp')
    print(f'Voltgage LOW = {voltage_low} Vpp')
    print(f'Frequency = {frequency} Hz')
    print(f'Phase = {phase} degrees')
    print(f'Offset = {offset} V')
    print(f'Output State = {output_state }')

    # test write
    myinstrument.set_amplitude(0.21, source=source, unit='Vpp', level='low')
    myinstrument.set_amplitude(0.22, source=source, unit='Vpp', level='high')
    myinstrument.set_offset(0.1, source=source, unit='V')
    myinstrument.set_shape('square', source=source)
    myinstrument.set_phase(10, source=source)
    myinstrument.set_frequency(200, source=source)


    # read back
    shape = myinstrument.get_shape(source=source)
    voltage_low =  myinstrument.get_amplitude(source=source, unit='Vpp', level='low')
    voltage_high =  myinstrument.get_amplitude(source=source, unit='Vpp', level='high')
    frequency = myinstrument.get_frequency(source=source, unit='Hz')
    phase = myinstrument.get_phase(source=source)
    offset = myinstrument.get_offset(source=source, unit='V')

    print(f'\nRead back:')
    print(f'Shape = {shape}')
    print(f'Voltgage HIGH = {voltage_high} Vpp')
    print(f'Voltgage LOW = {voltage_low} Vpp')
    print(f'Frequency = {frequency} Hz')
    print(f'Phase = {phase} degrees')
    print(f'Offset = {offset} V')

    
    # set signal gen output on
    myinstrument.set_generator_onoff('on', source=source)
    output_state = myinstrument.get_generator_onoff(source=source)
    print(f'Output State = {output_state }')

    # turn off
    myinstrument.set_generator_onoff('off', source=source)
    output_state = myinstrument.get_generator_onoff(source=source)
    print(f'Output State = {output_state }')
