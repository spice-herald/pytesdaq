import time
from enum import Enum
from pytesdaq.instruments.visa_instruments import VisaInstrument


_MAX_NB_CHANNELS = 16
_DWELL_MIN = 1
_DWELL_MAX = 200
_PAUSE_MIN = 3
_PAUSE_MAX = 200




class LakeshoreTempController(VisaInstrument):
    """
    Lakeshore Temperature Controller 
    """

    def __init__(self,resource_address, raise_errors=True, verbose=True):
        super().__init__(resource_address, termination='\n', raise_errors=raise_errors,
                         verbose=verbose)
        


        
    def get_channel_setup(self, chan_nums):
        """
        Get current channel setup

        
        Parameters
        ----------
        chan_nums: int or list
           0 = all channels
           1-16 = specific channel
        

        Return
        ----------

        setup: dictionary       
        """

        # initialize
        output = dict()

        
        # check input
        if chan_num not in list(range(0,17)):
            print('ERROR: Channel number should be 1-16')
            if self._raise_errors:
                raise
            else:
                return output

        

        #  list of channels
        chan_list = list()
        if chan_num == 0:
            chan_list = list(range(1,17))
        else:
            chan_list.append(chan_num)


        for chan in chan_list:

            # intialize
            output_chan = dict()

            # input_channel parameter (INSET)
            command = 'INSET? ' + str(chan)
            data = self._query(command)
            data_list = self._get_comma_separated_list(data)
            output_chan['enabled'] = bool(int(data_list[0]))
            output_chan['dwell_time'] = int(data_list[1])
            output_chan['pause_time'] = int(data_list[2])
            output_chan['curve_number'] = int(data_list[3])
            output_chan['tempco'] = int(data_list[4])

            # input channel setup (INTYPE)
            command = 'INTYPE? ' + str(chan)
            data = self._query(command)
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


    
    
    def set_channel(self, chan_nums, enable=True, disable_other=False,
                    dwell_time=None, pause_time=None, curve_number=None,
                    tempco=None, excitation_mode=None, excitation_range=None,
                    autorange=None, resistance_range=None, cs_shunt_enabled=None,
                    reading_units=None):
        """
        Setup channel

        
        Parameters
        ----------
        chan_nums: int  or list
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
        
        # check channels  
        if isinstance(chan_nums, int):
            chan_nums = [chan_nums]

        if 0 in chan_nums:
            chan_nums = list(range(1,_MAX_NB_CHANNELS+1))


        # loop all channels
        for chan in range(1, _MAX_NB_CHANNELS+1):
       
            # selected channel
            if chan in chan_nums:

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
                self._write(command)


                # input channel parameter
                command_list = [int(enable), dwell_time, pause_time, curve_number, tempco]          
                command = 'INSET ' + str(chan)
                for param in command_list:
                    command += ',' + str(param)
                self._write(command)

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
                self._write(command)
                                
            
 
    def enable_channel(self, chan_nums,  disable_other=False):
        
        """
        Enable input channel (s) and (optionally) disable all other channels.
        Use 'set_channel()' to change channel setup.
         
        Parameters
        ----------
        chan_nums: int or list
           channel number(s) 1-16
        disable_other: bool
           False (Default): No change other channels
           True: disable all other channels
        """


        # check input
        if isinstance(chan_nums, int):
            chan_nums = [chan_nums]


        # enable channels
        self.set_channel(chan_nums, enable=True, disable_other=disable_other)

     
                         
    def disable_channel(self, chan_nums):    
        """
        Disable input channel
        
        Parameters
        ----------
        chan_nums: int or list
           channel number (s)  (1-16)

        """
        
        # check channel input
        if isinstance(chan_nums, int):
            chan_nums = [chan_nums]

        # enable channels
        self.set_channel(chan_nums, enable=False)



        
            
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

    

            
    def select_channel(self, chan_num, autoscan=True):
        """
        Specified which channel to switch the scanner to

        Arguments:
        ----------
        chan_num: int
           Channel number (1-16)
        autoscan: bool (optional)
           False: Autoscan feature off
           True: Autoscan feature on (Default)
        """

        # check channel
        if chan_num not in list(range(1,17)):
            print('ERROR: channel number should be between 1-16')
            if self._raise_errors:
                raise
            else:
                return
        
        command = 'SCAN ' + str(chan) + ',' + str(int(autoscan))
        self._write(command)
        


        
        
    def start_scan(self, chan_num=None):
        """
        Start scanning by selecting first channel. At least one channel 
        should be enabled!

        Arguments:
        ----------
        chan_num: int  (optional)
           Firt channel number to be scanned (1-16)
           Default: first channel
        """

        self._scan_start_stop(True, chan_num=chan_num)


        
    def stop_scan(self, chan_num=None):
        """
        Stop scanning, keeping channels enabled
         
        Arguments:
        ----------
        chan_num: int  (optional)
           Selected channel  number (1-16)
           Default: first channel
        """

        self._scan_start_stop(False, chan_num=chan_num)
        
        

        
        
        
    def _scan_start_stop(self, enabled, chan_num=None):
        """
        Start/Stop scanning and select channel
        
        Arguments:
        ----------
        chan_num: int  (optional)
           Channel number selected
           Default: first channel
        """


        # find channel enabled
        chan_list = self.get_channel_enabled_list()


        if not chan_list:
            if self._verbose:
                print('WARNING: No channel has been enabled!')
            return
        elif chan_num is not None and chan_num not in chan_list:
            if self._verbose:
                print('ERROR: Selected channel (' + str(chan_num) + ') not enabled!')
                if self._raise_errors:
                    raise
                else:
                    return

        first_chan = chan_list[0]
        if chan_num is not None:
            first_chan = chan_num

        # select first channel and enable scanning
        self.select_channel(first_chan,autoscan=enabled)
        
        
    

            
            
  
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




