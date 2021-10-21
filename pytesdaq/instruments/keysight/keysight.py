import time
from enum import Enum
from pytesdaq.instruments.communication import InstrumentComm


class KeysightFuncGenerator(InstrumentComm):
    """
    Keysight function generators management
    """

    def __init__(self, visa_address, visa_library=None, raise_errors=True, verbose=True):
        super().__init__(visa_address=visa_address, termination='\n',
                         visa_library=visa_library,
                         raise_errors=raise_errors,
                         verbose=verbose)
        """
        Keysight
        """

        # connect to instrument
        self.connect()

        # get idn
        self._device_idn = self.get_idn()


        # model 3312
        self._is_model_3312 = False
        if '3312' in self._device_idn:
             self._is_model_3312 = True
        
        # is generator on 
        self._generator_onoff = 'off'
        

        
        
    def set_shape(self, shape,source=1):
        """
        Set signal shape

        
        Parameters
        ----------
        shape: string

          'sinusoid' or 'sine':
          'square':
          'triangle': 
          'ramp': 
          'dc': 
          'arb':
          'noise':
          'pulse':

        source: integer
           signal genertor output channel
        

        SCPI Names
        -----------
        {SINusoid|SQUare|TRIangle|RAMP|PULSe|PRBS|NOISe|ARB|DC},
       
        """

        function_list = ['sinusoid', 'sine', 'square','triangle', 'ramp', 'dc',
                         'arb', 'noise', 'pulse']

        
        if shape not in function_list:

            print('ERROR: Function type not recognized!')
            print('Choice is "sine", "square","triangle", "ramp", "dc","arb", "noise", or "pulse"') 
            if self._raise_errors:
                raise
            
        if shape == 'sine':
            shape = 'sin'

        # write to device
        command = 'SOUR' + str(source) + ':FUNC ' + shape
        self.write(command)
        

        
    def get_shape(self, source=1):
        """
        Get signal generator function

        Parameters
        ----------
        source: integer
           signal genertor output channel

        Returns: string
          Shape name (lower case): sine, square,triangle, ramp, pulse, prbs, noise,arb,dc
 
        """

        # query from device
        command = 'SOUR' + str(source) + ':FUNC?'
        shape = self.query(command)
        shape = shape.lower()

        if shape == 'squ':
            shape = 'square'
        
        if shape == 'tri':
            shape = 'triangle'

        if shape == 'sin':
            shape = 'sine'

        if shape == 'puls':
            shape =  'pulse'

        if shape == 'nois':
            shapew = 'noise'
            
        return shape



    def set_amplitude(self, amplitude, unit='Vpp', source=1):

        """
        Set signal amplitude
       
        Parameters
        ----------
        amplitude: float
          signal generator amplitude

        unit: string
          amplitude unit: 'Vpp','mVpp','Vrms','dbm'

        source: integer
           signal genertor output channel

        
        NOTE: SCPI Names  = {VPP|VRMS|DBM}
        """


        unit_list = ['Vpp', 'mVpp', 'Vrms', 'dbm']

        if unit not in unit_list:
            print('ERROR: Unit not recognized!')
            print('Choice is "Vpp","mVpp","Vrms",or "dbm"')
            if self._raise_errors:
                raise
            else:
                return
                     
        if unit == 'mVpp':
            amplitude = float(amplitude)/1000
            unit = 'Vpp'
            
            
        # set unit
        command = 'SOUR' + str(source) + ':VOLT:UNIT ' + unit
        self.write(command)


        # set amplitude
        command = 'SOUR' + str(source) + ':VOLT ' + str(amplitude)
        self.write(command)
        

        
    def get_amplitude(self, unit='Vpp', source=1):
        """
        Get signal amplitude
       
        Parameters
        ----------
        unit: string
          amplitude unit: 'Vpp','mVpp','Vrms','dbm'

        source: integer
           signal genertor output channel

        
        Returns
        -------
        
        amplitude: float
          amplitude with unit based on "unit" parameter

        """

        unit_list = ['Vpp','mVpp','Vrms','dbm']

        if unit not in unit_list:
            print('ERROR: Unit not recognized!')
            print('Choice is "Vpp","mVpp","Vrms",or "dbm"')
            if self._raise_errors:
                raise
            else:
                return None


        convert_mVpp = False
        if unit == 'mVpp':
            unit = 'Vpp'
            convert_mVpp = True
            
            
         # set unit
        command = 'SOUR' + str(source) + ':VOLT:UNIT ' + unit
        self.write(command)


        # get amplitude
        command = 'SOUR' + str(source) + ':VOLT?'
        amplitude = float(self.query(command))

        if convert_mVpp:
            amplitude *= 1000

        return amplitude


    def set_offset(self, offset, unit='V', source=1):

        """
        Set signal offset
       
        Parameters
        ----------
        offset: float
          signal generator offset

        unit: string
          offset unit: 'V','mV'

        source: integer
           signal genertor output channel

        """


        unit_list = ['V', 'mV']

        if unit not in unit_list:
            print('ERROR: Unit not recognized!')
            print('Choice is "V","mV"')
            if self._raise_errors:
                raise
            else:
                return
                     
        if unit == 'mV':
            offset = float(offset)/1000
            
     
        # set offset
        command = 'SOUR' + str(source) + ':VOLT:OFFS ' + str(offset)
        self.write(command)



        
    def get_offset(self, unit='V', source=1):
        
        """
        Get signal offset
       
        Parameters
        ----------
       
        unit: string
          offset unit: 'V','mV'

        source: integer
           signal genertor output channel

        Returns
        -------
        
        offset: float
          offset with unit based on "unit" parameter


        """


        unit_list = ['V', 'mV']

        if unit not in unit_list:
            print('ERROR: Unit not recognized!')
            print('Choice is "V","mV"')
            if self._raise_errors:
                raise
            else:
                return
         
        # query offset
        command = 'SOUR' + str(source) + ':VOLT:OFFS?'
        offset = float(self.query(command))

        if unit=='mV':
            offset *= 1000

        return offset


          
    
    def set_frequency(self,frequency,unit='Hz',source=1):

        """
        Set signal frequency
       
        Parameters
        ----------
        frequency: float
          signal generator frequency

        unit: string
          frequency unit: 'Hz','kHz','MHz'

        source: integer
           signal generator output channel

        """


        unit_list = ['Hz','kHz','MHz']

        if unit not in unit_list:
            print('ERROR: Unit not recognized!')
            print('Choice is "Hz", "kHz", or "MHz"')
            if self._raise_errors:
                raise
            else:
                return


        frequency = float(frequency)
        if unit == 'kHz':
            frequency *= 1000
        elif unit=='MHz':
            frequency *= 1e6
            
        # set frequency
        command = 'SOUR' + str(source) + ':FREQ ' + str(frequency)
        self.write(command)
        

        
    def get_frequency(self, unit='Hz', source=1):
        """
        Get signal frequency
       
        Parameters
        ----------
        unit: string
          frequency unit: 'Hz','kHz','MHz'

        source: integer
           signal genertor output channel

        
        Returns
        -------
        
        frequency: float
          frequency with unit based on "unit" parameter

        """

        unit_list = ['Hz','kHz','MHz']

        if unit not in unit_list:
            print('ERROR: Unit not recognized!')
            print('Choice is "Hz", "kHz", or "MHz"')
            if self._raise_errors:
                raise
            else:
                return None

        # get frequency
        command = 'SOUR' + str(source) + ':FREQ?'
        frequency = float(self.query(command))
        

        if unit == 'kHz':
            frequency /= 1000
        elif unit == 'MHz':
            frequency /= 1e6

        return frequency

    


    def set_generator_onoff(self, output_onoff, source=1):
        """
        Set generator output on/off
        
        Parameters
        ----------
        output_onoff: string or int
           "on"=1 or "off"=0

        source: integer
           signal generator output channel

        """

        # check input
        if isinstance(output_onoff, int):
            if output_onoff==0:
                output_onoff = 'off'
            else:
                output_onoff = 'on'
            
        output_onoff = output_onoff.lower()

        if output_onoff != 'on' and output_onoff != 'off':
            print('ERROR: Argument should be "on" or "off"')
            if self._raise_errors:
                raise
            else:
                return None


        # Keysight 3312: unable to turn on/off so keep track of status internally 
        if  self._is_model_3312:
            self._generator_onoff = output_onoff
            return


        # set device
        command = 'OUTP' + str(source) + ' ' + output_onoff
        self.write(command)


        
        
    def get_generator_onoff(self, source=1):
        """
        Is generator output on/off?
        
        Parameters
        ----------
        source: integer
           signal generator output channel


        Returns
        -------
        string "on" or "off"
        
        """

        if  self._is_model_3312:
            return self._generator_onoff

        # query status
        command = 'OUTP' + str(source) + '?'
        result = int(self.query(command))
        
        on_off = None
        if result == 0:
            on_off = 'off'
        elif result == 1:
            on_off = 'on'
                    
        return on_off
