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
        #self._inst.clear()
        self.connect()

        # get idn
        self._device_idn = self.get_idn()



    def enable_output(self):
        """
        Enable source either voltage or current
        depending of the settings
        """
        command = ':OUTP ON'
        
        self.write(command)


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

    
    def set_source(self, source, fixed=True, autorange=False):
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
        self._inst.clear()
        
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

    def set_current_compliance(self,cmpl):
        """
        Set the complance limit of the supply in Amps

        Arguments:
        ---------
        cmpl : float
          cmpl limit

        Return
        ------
        None
        """
        
        if abs(cmpl) > 1:
            raise ValueError('ERROR: Max compliance set. Do not put this higher than 1mA!')

        command = ':SENS:CURR:PROT ' + str(cmpl)
        self.write(command)


    def set_current_measurement_range(self,Crange):
        """
        Set the measurment range limit of the supply in Amps

        Arguments:
        ---------
        range : float
          range limit

        Return
        ------
        None
        """
    

        command = ':SENS:CURR:RANG ' + str(Crange)
        print("Current measure set to fixed range")
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

        self._inst.clear()
        current = self.query(':SOUR:CURR?')
        return float(current)

    def measure_current(self):
        """
        Measure current 

        Arguments:
        ---------
        None

        Return
        ------
        current : float
        """

        #command = 'MEAS:CURR?'
        # the MEAS command will do the configuration at the same time. READ will keep existing scensing setting
        command = ':READ?'
        self.write(command)
        #print("measure_current::self.write(':READ?' !!!!!!!!!!!!")
        #time.sleep(0.2)

    def showARM_current(self):
        """
        Configure the device to show the current on the screen of the device
        
        Arguments:
        ---------
        None

        Return
        ------
        None
        """

        command = "DISP:FORM:ENAB ARM,CURR"
        self.write(command)

