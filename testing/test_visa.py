from pytesdaq.instruments.communication import InstrumentComm

if __name__ == "__main__":

    
    # VISA Address

    # TCP
    #visa_address = 'TCPIP::192.168.0.4::5025::SOCKET'

    # RS232
    #visa_address = 'COM1'

    # USB
    visa_address = 'USB0::0x0957::0x2507::MY58000409::0::INSTR'
    
    
    # Instantiate instrument
    myinstrument = InstrumentComm(visa_address, termination='\n')

    # Check device
    idn = myinstrument.get_idn()
    print('Device name: ' + idn)

    
    
