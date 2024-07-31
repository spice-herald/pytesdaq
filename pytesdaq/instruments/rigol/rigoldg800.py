import time
from enum import Enum
from pytesdaq.instruments.communication import InstrumentComm


class RigolDG800(InstrumentComm):
    """
    Rigol DG800 series function generators management
        
    """

    def __init__(self, visa_address, visa_library='@py',
                 attenuation=1, raise_errors=True,
                 verbose=True):
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
        
        # signal generator attenuation
        self._attenuation = attenuation

    @property
    def device_idn(self):
        return self._device_idn 
    
    def set_shape(self, shape, source=1):
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
            print('Choice is "sine", "square","triangle", "ramp",'
                  '"dc","arb", "noise", or "pulse"') 
            if self._raise_errors:
                raise
            
        if shape == 'sine':
            shape = 'sin'

        # write to device
        command = f':SOUR{source}:FUNC:SHAP {shape}'
        self.write(command)
        

        
    def get_shape(self, source=1):
        """
        Get signal generator function

        Parameters
        ----------
        source: integer
           signal genertor output channel

        Returns: string
          Shape name (lower case): sine, square,triangle, ramp, 
          pulse, prbs, noise,arb,dc
 
        """

        # query from device
        command = f':SOUR{source}:FUNC:SHAP?'
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



    def set_amplitude(self, amplitude, source=1, unit='Vpp'):

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


        unit_list = ['V', 'Vpp', 'mV', 'mVpp', 'Vrms', 'dbm']

        if unit not in unit_list:
            print('ERROR: Unit not recognized!')
            print('Choice is "Vpp","mVpp","Vrms",or "dbm"')
            if self._raise_errors:
                raise
            else:
                return

        if unit == 'V':
            unit = 'Vpp'
        if unit == 'mV':
            unit = 'mVpp'

            
        if unit == 'mVpp':
            amplitude = float(amplitude)/1000
            unit = 'Vpp'

        # take into account  attenuation
        amplitude *= self._attenuation
            
        # set unit
        command = f':SOUR{source}:VOLT:UNIT {unit}'
        self.write(command)


        # set amplitude
        command = f':SOUR{source}:VOLT {amplitude}'
        self.write(command)
        

        
    def get_amplitude(self, source=1, unit='Vpp'):
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

        unit_list = ['V','Vpp','mV', 'mVpp','Vrms','dbm']

        if unit not in unit_list:
            print('ERROR: Unit not recognized!')
            print('Choice is "Vpp","mVpp","Vrms",or "dbm"')
            if self._raise_errors:
                raise
            else:
                return None

        if unit == 'V':
            unit = 'Vpp'
        if unit == 'mV':
            unit = 'mVpp'

        convert_mVpp = False
        if unit == 'mVpp':
            unit = 'Vpp'
            convert_mVpp = True
            
            
        # set unit
        command = f':SOUR{source}:VOLT:UNIT {unit}'
        self.write(command)
        
        # get amplitude
        command = f':SOUR{source}:VOLT?'
        amplitude = float(self.query(command))


        # attenuation
        amplitude /= self._attenuation
        
        if convert_mVpp:
            amplitude *= 1000

        return amplitude


    def set_offset(self, offset, source=1, unit='V'):

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


        unit_list = ['V', 'mV', 'Vpp','mVpp']

        if unit not in unit_list:
            print('ERROR: Unit not recognized!')
            print('Choice is "V","mV"')
            if self._raise_errors:
                raise
            else:
                return

        if unit == 'Vpp':
            unit = 'V'
        if unit == 'mVpp':
            unit = 'mV'
                     
        if unit == 'mV':
            offset = float(offset)/1000

        # take into account  attenuation
        offset *= self._attenuation
                   
        # set offset
        command = f':SOUR{source}:VOLT:OFFS {offset}'
        self.write(command)
        
    def get_offset(self, source=1, unit='V'):
        
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
        unit_list = ['V', 'mV', 'Vpp', 'mVpp']

        if unit not in unit_list:
            print('ERROR: Unit not recognized!')
            print('Choice is "V","mV"')
            if self._raise_errors:
                raise
            else:
                return
     
        if unit == 'Vpp':
            unit = 'V'
        if unit == 'mVpp':
            unit = 'mV'
            
        # query offset
        command = f':SOUR{source}:VOLT:OFFS?'
        offset = float(self.query(command))

        # attenuation
        offset /= self._attenuation
              
        if unit=='mV':
            offset *= 1000

        return offset

    
    def set_phase(self, phase, source=1):

        """
        Set signal phase
       
        Parameters
        ----------
        phase: float
          signal generator phase [degree]

        source: integer
           signal generator output channel

        """

        # set phase
        command = f':SOUR{source}:PHAS {phase}'
        self.write(command)


    def get_phase(self, source=1):

        """
        Get signal phase [degree]
       
        Parameters
        ----------
           source: integer
              signal generator output channel

        """

        # get phase 
        command = f':SOUR{source}:PHAS?'
        phase = float(self.query(command))
        return phase
    
    
    def set_frequency(self, frequency, source=1, unit='Hz'):

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
        command = f':SOUR{source}:FREQ {frequency}'
        self.write(command)
    
        
    def get_frequency(self, source=1, unit='Hz'):
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
        command = f':SOUR{source}:FREQ?'
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


        # set device
        command = f'OUTP{source} {output_onoff}'
        self.write(command)


        
        
    def get_ouptut_state(self, source=1):
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

        # query status
        command = f'OUTP{source}?'
        result = self.query(command)
        return result

    
        #on_off = None
        #if result == 0:
        #    on_off = 'off'
        #elif result == 1:
        #    on_off = 'on'
                    
        #return on_off
