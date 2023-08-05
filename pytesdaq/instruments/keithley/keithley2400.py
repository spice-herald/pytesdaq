import time
from enum import Enum
from pytesdaq.instruments.communication import InstrumentComm


class Keithley2400(InstrumentComm):
    """
    Keithley 2400 Series signal source
        
    """

    def __init__(self, visa_address, visa_library=None,
                 raise_errors=True, verbose=True):
        
        super().__init__(visa_address=visa_address, termination='\n',
                         visa_library=visa_library,
                         raise_errors=raise_errors,
                         verbose=verbose)
        """
        Intialize Keithley 2400

        """

        # connect to instrument
        self.connect()

        # get idn
        self._device_idn = self.get_idn()



    def enable_output(self):
        """
        Enable source either voltage or current
        depending of the settings
        """

        self.write('OUTPUT ON')


    def disable_output(self):
        """
        Enable source either voltage or current
        depending of the settings
        """

        self.write('OUTPUT OFF')


    def get_source(self):
        """
        Get source 'current' or 'voltage'
        
        Arguments:
        ---------
        None

        Return
        ------
        
        source : string
         "current" or "voltage"
        
        """

        command = ':SOUR:FUNC?'
        source = self.query(command)

        if source == 'CURR':
            return 'current'
        elif  source == 'VOLT':
            return 'voltage'
        else:
            return source

    
    def set_source(self, source, fixed=True, autorange=True):
        """
        Set source: 'current' or 'voltage'

        
        Parameters
        ----------
        
        source : string
           'current' or 'voltage'
        
        fixed : boolean (optional)
          if True (default), set ot fixed

        auto_range : boolean (optional)
          if True (default) , set autorange
        
        """


        # check argument
        if (source != 'current' and source != 'voltage'):
            raise ValueError('ERROR: argument "current" or '
                             '"voltage" expected')
        
        # build command
        command = ':SOUR:FUNC '
        if source == 'current':
            command += 'CURR'
        elif source == 'voltage':
            command += 'VOLT'

        # write
        self.write(command)
        
        # set fixed / autorange
        if source == 'current':
            if fixed:
                self.write(':SOUR:CURR:MODE FIXED')
            if autorange:
                self.write(':SOUR:CURR:RANG:AUTO 1')
                
        elif source == 'voltage':
            
            if fixed:
                self.write(':SOUR:VOLT:MODE FIXED')
            if autorange:
                self.write(':SOUR:VOLT:RANG:AUTO 1')
                


    def set_voltage(self, voltage):
        """
        Set voltage (in Volts)
        

        Arguments:
        ---------
        voltage : float 
          output voltage 
        
        Return
        ------
        None

        """


        # check if within range (? Not sure range)
        if abs(voltage)>20:
            raise ValueError('ERROR: Maximum voltage allowed is 20V')


        command = ':SOUR:VOLT:LEV ' + str(voltage)
        self.write(command)
        

    def get_voltage(self):
        """
        Get voltage 

        Arguments:
        ---------
        None

        Return
        ------
        voltage : float
        """


        voltage = self.query(':SOUR:VOLT?')
        return float(voltage)



    def set_current(self, current):
        """
        Set current  (in Amps)
        

        Arguments:
        ---------
        current : float 
          output current
        
        Return
        ------
        None

        """


        # check if within range (? Not sure range)
        if abs(current)>1:
            raise ValueError('ERROR: Maximum current allowed is 1Amps')


        command = ':SOUR:CURR:LEV ' + str(current)
        self.write(command)
        

    def get_current(self):
        """
        Get current 

        Arguments:
        ---------
        None

        Return
        ------
        current : float
        """


        current = self.query(':SOUR:CURR?')
        return float(current)
