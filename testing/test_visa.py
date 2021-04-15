from pytesdaq.instruments.visa_instruments import VisaInstrument


if __name__ == "__main__":

    
    # VISA Address

    # TCP
    visa_address = 'TCPIP::192.168.0.4::5025::SOCKET'

    # RS232
    #visa_address = 'COM1'

    
    # Instantiate instrument
    myinstrument = VisaInstrument(visa_address, termination='\n')

    # Check device
    idn = myinstrument.get_idn()
    print('Device name: ' + idn)

    
    
