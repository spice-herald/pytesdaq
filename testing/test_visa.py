from pytesdaq.instruments.communication import InstrumentComm

if __name__ == "__main__":

    
    # VISA Address

    # TCP
    visa_address = 'TCPIP::131.243.51.117::inst0::INSTR'
    #visa_address = 'TCPIP::K-33509B-00505::5025::SOCKET'
    # RS232
    #visa_address = 'COM1'

    # GPIB
    #visa_address = 'GPIB0::9::INSTR'

    # USB
    #visa_address = 'USB0::0x0957::0x2507::MY58000409::0::INSTR'
    
    
    # Instantiate instrument
    myinstrument = InstrumentComm(visa_address, termination='\n')

    # Check device
    idn = myinstrument.get_idn()
    print('Device name: ' + idn)

    
    
