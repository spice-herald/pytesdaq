import time
from enum import Enum
from pytesdaq.instruments.communication import InstrumentComm


class KeysightDSOX1200(InstrumentComm):
    """
    Keysight DSOX1200 series ocilloscope
        
    """

    def __init__(self, visa_address, visa_library=None,
                 attenuation=1, raise_errors=True,
                 verbose=True):
        super().__init__(visa_address=visa_address, termination='\n',
                         visa_library=visa_library,
                         raise_errors=raise_errors,
                         verbose=verbose)
        """
        Keysight DSOX1200
        """

        # connect to instrument
        self.connect()

        # get idn
        self._device_idn = self.get_idn()

        # signal generator attenuation
        self._attenuation = attenuation
        
        
    def set_shape(self, shape, **kwargs):
        """
        Set signal shape

        
        Parameters
        ----------
        shape: string

          'sinusoid' or 'sine'
          'square'
          'ramp'
          'dc'
          'pulse'
          'noise'
         

        SCPI Names
        -----------
        {SINusoid|SQUare|RAMP|PULSe|NOISe|DC},
       
        """

        function_list = ['sinusoid', 'sine', 'square','ramp', 'dc',
                         'noise', 'pulse']

        
        if shape not in function_list:

            print('ERROR: Function type not recognized!')
            print('Choice is "sine", "square", "ramp", "dc",'
                  '"noise", or "pulse"') 
            if self._raise_errors:
                raise
            
        if shape == 'sine':
            shape = 'sin'

        # write to device
        command = ':WGEN:FUNC ' + shape
        self.write(command)
        

        
    def get_shape(self, **kwargs):
        """
        Get signal generator function

        Parameters
        ----------
        None

        Return:
        -------

        Returns: string
          Shape name (lower case): sine, square,triangle, 
          ramp, pulse, prbs, noise,arb,dc
 
        """

        # query from device
        command = 'WGEN:FUNC?'
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



    def set_amplitude(self, amplitude, **kwargs):

        """
        Set signal amplitude in Volts
       
        Parameters
        ----------
        amplitude: float
          signal generator amplitude [Volts]

        Return:
        ------
        None
        """
            
        # take into account  attenuation
        amplitude *= self._attenuation
        
        
        # set amplitude
        command = ':WGEN:VOLT ' + str(amplitude)
        self.write(command)
        

        
    def get_amplitude(self, **kwargs):
        """
        Get signal amplitude in volts
       
        Parameters
        ----------
        None 
        
        Returns
        -------
        
        amplitude: float
          amplitude in volts

        """


        # get amplitude
        command = ':WGEN:VOLT?'
        amplitude = float(self.query(command))


        # attenuation
        amplitude /= self._attenuation

        
        return amplitude



    
    def set_offset(self, offset, **kwargs):

        """
        Set signal offset in volts
       
        Parameters
        ----------
        offset: float
          signal generator offset [Volts]

        Return
        ------
        None

        """

        # set offset
        command = 'WGEN:VOLT:OFFS ' + str(offset)
        self.write(command)



        
    def get_offset(self, **kwargs):
        
        """
        Get signal offset
       
        Parameters
        ----------
        None
        

        Returns
        -------
        
        offset: float
          offset [volts]

        """

        # query offset
        command = ':WGEN:VOLT:OFFS?'
        offset = float(self.query(command))

        return offset


          
    
    def set_frequency(self, frequency, **kwargs):

        """
        Set signal frequency in Hz
       
        Parameters
        ----------
        frequency: float
          signal generator frequency [Hz]

        Return
        ------
        None
        """

            
        # set frequency
        command = ':WGEN:FREQ ' + str(frequency)
        self.write(command)
        

        
    def get_frequency(self, **kwargs):
        """
        Get signal frequency
       
        Parameters
        ----------
        None

        
        Returns
        -------
        
        frequency: float
          frequency in Hz

        """

        # get frequency
        command = ':WGEN:FREQ?'
        frequency = float(self.query(command))
        

        return frequency

    


    def set_generator_onoff(self, output_onoff, **kwargs):
        """
        Set generator output on/off
        
        Parameters
        ----------
        output_onoff: string or int
           "on"=1 or "off"=0

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
        command = ':WGEN:OUTP ' + output_onoff
        self.write(command)


        
        
    def get_generator_onoff(self, **kwargs):
        """
        Is generator output on/off?
        
        Parameters
        ----------
        None


        Returns
        -------
        string "on" or "off"
        
        """

        # query status
        command = ':WGEN:OUTP?'
        result = int(self.query(command))
        
        on_off = None
        if result == 0:
            on_off = 'off'
        elif result == 1:
            on_off = 'on'
                    
        return on_off

    
