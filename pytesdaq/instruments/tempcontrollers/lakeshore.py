import time
from lakeshore import Model372



# lakeshore constants
_MAX_NB_CHANNELS = 16
_DWELL_MIN = 1
_DWELL_MAX = 200
_PAUSE_MIN = 3
_PAUSE_MAX = 200




class Lakeshore():
    """
    Lakeshore Temperature Controller 
    """

    def __init__(self, model_number=372, ip_address=None, port=None, baud_rate=57600,
                 raise_errors=True, verbose=True):


        # verbose
        self._debug = False
        self._verbose = verbose
        self._raise_errors = raise_errors

        
        # Initialize instrument
        self._inst = None
        self._model_number = model_number
        self._serial_number = None
        self._firmware_version = None
        
        # Connection setup
        self._ip_address =  ip_address
        self._connection_type = None
        self._baud_rate = baud_rate
        self._tcp_port = None
        self._com_port = None

        if self._ip_address is None:
            self._connection_type = 'usb'
            self._com_port = port
        else:
            self._connection_type = 'tcp'
            self._tcp_port = port
        

        # channel maps
        self._channel_map = None
    
        
         
    @property
    def model_number(self):
        return self._model_number

    @property
    def serial_number(self):
        return self._serial_number
      
    @property
    def ip_address(self):
        return self._ip_address

    @property
    def port(self):
        if self._connection_type == 'usb':
            return self._com_port
        elif self._connection_type == 'tcp':
            return self._tcp_port
        else:
            return None


        
    def connect(self):
        """
        Open connection
        """

        
        try:
            if self._model_number==372:
                self._inst = Model372(baud_rate=self._baud_rate,
                                      ip_address=self._ip_address,
                                      tcp_port=self._tcp_port,
                                      com_port=self._com_port)

        except:
            print('ERROR: Unable to connect to lakeshore!')
            if self._raise_errors:
                raise
            else:
                return 


        # properties
        self._serial_number = self._inst.serial_number
        self._firmware_version = self._inst.firmware_version

            
        if self._verbose:
            connection_info = 
            print('Lakeshore ' + str(self._model_number) + ' connected!')

            
    def disconnect(self):
        """
        Close connection
        """

        if self._inst  is not None:
            if self._connection_type == 'usb':
                self._inst.disconnect_usb()
            else:
                self._inst.disconnect_tcp()
    
        if self._verbose:
            print('Lakeshore ' + str(self._model_number) + ' disconnected!')
                

    def set_channel_names(self, channel_numbers, channel_names):
        """
        Channel name map
        """

        # convert to list if needed
        if not isinstance(channel_numbers):
            channel_numbers = [channel_numbers]
            
        if not isinstance(channel_names):
            channel_names = [channel_names]

            
        if len(channel_numbers) != len(channel_names):
            raise ValueError('ERROR: channel number and names should be same length!')


        if self._channel_map is None:
            self._channel_map = dict()

        for ichan in range(len(channel_numbers)):
            self._channel_map[channel_names[ichan]] = channel_numbers[ichan]
            

            
        
    def get_channel_setup(self, channel_numbers=None, channel_names=None):
        """
        Get current channel setup

        
        Parameters
        ----------
        channel_numbers: int or list
            1-16 = specific channel
        
        Return
        ----------

        setup: dictionary       
        """


        if channel_names is not None:
            channel_numbers = self._extract_channel_numbers(channel_names)
            
        if not isinstance(channel_numbers, list):
            channel_numbers  = [channel_numbers]
            
            

        
        # initialize output
        output = dict()


        # loop channels and get setup
        for chan in channel_numbers:

            # intialize
            output_chan = dict()

            # input_channel parameter (INSET)
            command = 'INSET? ' + str(chan)
            data = self._inst.query(command)
            data_list = self._get_comma_separated_list(data)
            output_chan['enabled'] = bool(int(data_list[0]))
            output_chan['dwell_time'] = int(data_list[1])
            output_chan['pause_time'] = int(data_list[2])
            output_chan['curve_number'] = int(data_list[3])
            output_chan['tempco'] = int(data_list[4])

            # input channel setup (INTYPE)
            command = 'INTYPE? ' + str(chan)
            data = self._inst.query(command)
            data_list = self._get_comma_separated_list(data)

            if int(data_list[0]) == 0:
               output_chan['excitation_mode'] = 'voltage'
            else:
                output_chan['excitation_mode'] = 'current'
                
            output_chan['excitation_range'] = int(data_list[1])
            output_chan['autorange'] = int(data_list[2])                                
            output_chan['resistance_range'] = int(data_list[3])
            output_chan['cs_shunt_enabled'] = bool(int(data_list[4]))

            if int(data_list[5]) == 1:
                output_chan['reading_units'] = 'kelvin'
            else:
                output_chan['reading_units'] = 'ohms'
        
            # add to ouput
            output[chan] = output_chan
            
        
        return output




    
    def get_temperature(self, channel_number=None, channel_name=None,
                        manual_conversion=False):
        
        """
        Get temperature
        """
        

        # get channel number if channel names provided
        if channel_name is not None:
            channel_number = self._extract_channel_number(channel_name)

        # query temperature
        query_command = 'RDGK? ' + str(channel_number)
        temperature = float(self._inst.query(query_command))

        return temperature
        

    def get_resistance(self, channel_number=None, channel_name=None,
                       manual_conversion=False):
        
        """
        Get resistance
        """
        

        # get channel number if channel names provided
        if channel_name is not None:
            channel_number = self._extract_channel_number(channel_name)

        # query resistance
        query_command = 'RDGR? ' + str(channel_number)
        resistance = float(self._inst.query(query_command))

        return resistance
        


    
    def set_temperature(self, channel_number=None, channel_name=None,
                        heater_channel_number=None, heater_channel_name=None):
        """
        Set temperature
        """

        
        return


    

    

    
    def set_channel(self, channel_numbers=None, channel_names=None,
                    enable=True, disable_other=False,
                    dwell_time=None, pause_time=None, curve_number=None,
                    tempco=None, excitation_mode=None, excitation_range=None,
                    autorange=None, resistance_range=None, cs_shunt_enabled=None,
                    reading_units=None):
        """
        Setup channel

        
        Parameters
        ----------
        channel_numbers: int  or list
           0 = all channels 
           1-16 = specific channel
        enable: bool
           True/False = enable/disable channel 
        disable_other: bool
           False (Default): No change other channels
           True: disable all other channels
        dwell_time: int (optional)
           The dwell time in seconds (1-200s)
        pause_time: int (optional)
           The pause time in seconds (3-200s)
        curve_number: int (optional)
           Specifies which curve the channel uses:
                0 = no curve
                1-59 = standard / user curve
        tempco: int (optional)
           Set the temperature coefficient if no curve selected
                1 = negative
                2 = positive
        excitation_mode: str
           Sensor exitation mode: 'voltage' or  'current' 
        excitation_range: int
           Input exitation range number: see table
        resistance_range: int
           Input resistance range number: see table
        autorange: int
           Auto range: 0=off, 1=autorange current, 2=ROX 102B autorange 
        cs_shunt_enabled: bool
           False = current source not shunted, excitation on
           True  = current source shunted, excitation off
        reading_units: str
           Preferred units parameter for sensor readings: 'kelvin' or 'ohms'
       
        """


        # extract channel numbers if names provided
        if channel_names is not None:
            channel_numbers = self._extract_channel_numbers(channel_names)
            
        if not isinstance(channel_numbers, list):
            channel_numbers  = [channel_numbers]
            
          
        # loop all channels
        for chan in range(1, _MAX_NB_CHANNELS+1):
       
            # selected channel
            if chan in channel_numbers:

                current_setup = self.get_channel_setup(chan)[chan]
                
                # fill value if needed
                if dwell_time is None:
                    dwell_time = current_setup['dwell_time']
                if pause_time is None:
                    pause_time = current_setup['pause_time']
                if curve_number is None:
                    curve_number = current_setup['curve_number']
                if tempco is None:
                    tempco = current_setup['tempco']
                if excitation_mode is None:
                    excitation_mode = current_setup['excitation_mode']
                if excitation_range is None:
                    excitation_range = current_setup['excitation_range']
                if resistance_range is None:
                    resistance_range = current_setup['resistance_range']
                if autorange is None:
                    autorange = current_setup['autorange']
                if cs_shunt_enabled is None:
                    cs_shunt_enabled = current_setup['cs_shunt_enabled']
                if reading_units is None:
                    reading_units = current_setup['excitation_mode']

                    
                # convert
                if excitation_mode == 'voltage':
                    excitation_mode = 0
                else:
                    excitation_mode = 1
                
                if reading_units == 'kelvin':
                    reading_units = 1
                else:
                    reading_units = 2


                    
                # input setup
                command_list = [excitation_mode, excitation_range, int(autorange),
                                resistance_range, int(cs_shunt_enabled), reading_units]

                command = 'INTYPE ' + str(chan)
                for param in command_list:
                    command += ',' + str(param)
                self._inst.command(command)


                # input channel parameter
                command_list = [int(enable), dwell_time, pause_time, curve_number, tempco]          
                command = 'INSET ' + str(chan)
                for param in command_list:
                    command += ',' + str(param)
                self._inst.command(command)

            elif disable_other:

                # let's first read setting
                current_setup = self.get_channel_setup(chan)[chan]

                # build command
                command_list = [0, current_setup['dwell_time'], current_setup['pause_time'],
                                current_setup['curve_number'], current_setup['tempco']]          
                command = 'INSET ' + str(chan)
                for param in command_list:
                    command += ',' + str(param)

                # write
                self._inst.command(command)
                                
            
 
    def enable_channel(self, channel_numbers=None, channel_names=None, disable_other=False):
        
        """
        Enable input channel (s) and (optionally) disable all other channels.
        Use 'set_channel()' to change channel setup.
         
        Parameters
        ----------
        channel_numbers: int or list
           channel number(s) 1-16
        disable_other: bool
           False (Default): No change other channels
           True: disable all other channels
        """

        # extract channel numbers if names provided
        if channel_names is not None:
            channel_numbers = self._extract_channel_numbers(channel_names)
            
        if not isinstance(channel_numbers, list):
            channel_numbers  = [channel_numbers]
            
          

        # enable channels
        self.set_channel(channel_numbers, enable=True, disable_other=disable_other)

     
                         
    def disable_channel(self, channel_numbers=None, channel_names=None):    
        """
        Disable input channel
        
        Parameters
        ----------
        channel_numbers: int or list
           channel number (s)  (1-16)

        """

        # extract channel numbers if names provided
        if channel_names is not None:
            channel_numbers = self._extract_channel_numbers(channel_names)
            
        if not isinstance(channel_numbers, list):
            channel_numbers  = [channel_numbers]
            
          

        # enable channels
        self.set_channel(channel_numbers, enable=False, disable_other=disable_other)

     


        
        # check channel input
        if isinstance(channel_numbers, int):
            channel_numbers = [channel_numbers]

        # enable channels
        self.set_channel(channel_numbers, enable=False)



        
            
    def get_channel_enabled_list(self):
        """
        Get list of channels that have been enabled
        
        Arguments:
        ----------
        None

        Return:
        -------
        list [int]
           List of channels (1-16)
        
        """

        # initialize output
        chan_list = list()

        
        # get channel info dictionary
        data_dict = get_channel_setup(0)

        # loop and check if channel enabled
        for chan,info in data_dict.items():
            if info['enabled']:
                chan_list.append(chan)

        return chan_list

    

            
    def select_channel(self, channel_number=None, channel_name=None, autoscan=True):
        """
        Specified which channel to switch the scanner to

        Arguments:
        ----------
        channel_number: int
           Channel number (1-16)
        autoscan: bool (optional)
           False: Autoscan feature off
           True: Autoscan feature on (Default)
        """
        
        # get channel number if channel names provided
        if channel_name is not None:
            channel_number = self._extract_channel_number(channel_name)

        # check channel
        if channel_number not in list(range(1,17)):
            print('ERROR: channel number should be between 1-16')
            if self._raise_errors:
                raise
            else:
                return
        
        command = 'SCAN ' + str(channe_number) + ',' + str(int(autoscan))
        self._inst.command(command)
        


        
        
    def start_scan(self, channel_number=None, channel_name=None):
        """
        Start scanning by selecting first channel. At least one channel 
        should be enabled!

        Arguments:
        ----------
        chan_num: int  (optional)
           Firt channel number to be scanned (1-16)
           Default: first channel
        """

        self._scan_start_stop(True, channel_number=channel_number,
                              channel_name=channel_name)


        
    def stop_scan(self, channel_number=None, channel_name=None):
        """
        Stop scanning, keeping channels enabled
         
        Arguments:
        ----------
        chan_num: int  (optional)
           Selected channel  number (1-16)
           Default: first channel
        """
        
        self._scan_start_stop(False, channel_number=channel_number,
                              channel_name=channel_name)

        
        

        
        
        
    def _scan_start_stop(self, enabled, channel_number=None, channel_name=None):
        """
        Start/Stop scanning and select channel
        
        Arguments:
        ----------
        chan_num: int  (optional)
           Channel number selected
           Default: first channel
        """


        # get channel number if channel names provided
        if channel_name is not None:
            channel_number = self._extract_channel_number(channel_name)


            

        
        # find channel enabled
        channel_list = self.get_channel_enabled_list()


        if not channel_list:
            if self._verbose:
                print('WARNING: No channel has been enabled!')
            return
        elif channel_number is not None and channel_number not in chan_list:
            if self._verbose:
                print('ERROR: Selected channel (' + str(channel_number) + ') not enabled!')
                if self._raise_errors:
                    raise
                else:
                    return

        first_chan = chan_list[0]
        if channel_number is not None:
            first_chan = channel_number

        # select first channel and enable scanning
        self.select_channel(channel_number=first_chan, autoscan=enabled)
        
        
    

            
            
  
    def _get_comma_separated_list(self, data):
        """
        Get list for comman separated parameters
     
        Argruments:
        ----------
        data: str
        

        Returns:
        --------
        list of arguments

        """

        data = str(data)
                
        if data.strip() == '':
            return []
    
        return [s.strip() for s in data.split(',')]




    def _extract_channel_numbers(self, channel_names):
        """ 
        Get channel numbers
        """


        if not isinstance(channel_names, list):
            channel_names = [channel_names]

        
        channel_numbers = list()
        for chan in channel_names:
            if chan in self._channel_map:
                channel_numbers.append(self._channel_map[chan])
            else:
                raise ValueError('ERROR: no channel "' + chan + '" found!')

        if len(channel_numbers)==1:
            channel_numbers = channel_numbers[0]

        return channel_numbers
                    
