import time
from lakeshore import Model372
import pandas as pd
import os
import stat
from pytesdaq.config import settings


# lakeshore constants
_MAX_NB_CHANNELS = 16
_MAX_NB_HEATER_CHANNELS = 3
_DWELL_MIN = 1
_DWELL_MAX = 200
_PAUSE_MIN = 3
_PAUSE_MAX = 200




class Lakeshore():
    """
    Lakeshore Temperature Controller 
    """

    def __init__(self, instrument_name='lakeshore', model_number=None,
                 ip_address=None, tcp_port=None, com_port=None,
                 baud_rate=57600, raise_errors=True, verbose=True):

      
        # instrument name and number
        self._instrument_name = instrument_name
        self._instrument_number = None
        if self._instrument_name[9:]:
            self._instrument_number = int(self._instrument_name[9:])

        
        # verbose

        self._debug = True
        self._verbose = verbose
        self._raise_errors = raise_errors

        
        # Initialize instrument
        self._inst = None
        self._model_number = model_number
        self._serial_number = None
        self._firmware_version = None
             
        # Initialize connection setup
        self._ip_address =  ip_address
        self._baud_rate = baud_rate
        self._tcp_port = tcp_port
        self._com_port = com_port
              

        # channel properties
        self._channel_properties = ['instrument_name', 'module_name', 'module_type', 'module_number',
                                    'module_address', 'channel_number', 'global_channel_number',
                                    'channel_name', 'device_type', 'device_serial']
        # resistance channels
        self._resistance_channel_table = None
        self._resistance_channel_property_list = None
        self._resistance_channel_names = None
        self._resistance_global_channel_numbers = None

        # heater channels
        self._heater_channel_table = None
        self._heater_channel_property_list = None
        self._heater_channel_names = None
        self._heater_global_channel_numbers = None

        
        
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
    def tcp_port(self):
        return self._tcp_port
        
    @property
    def com_port(self):
        return self._com_port
    

    @property
    def resistance_channel_names(self):
        return self._resistance_channel_names

    @property
    def resistance_global_channel_numbers(self):
        return self._resistance_global_channel_numbers

    @property
    def heater_channel_names(self):
        return self._heater_channel_names

    @property
    def heater_global_channel_numbers(self):
        return self._heater_global_channel_numbers





    def get_channel_table(self, channel_type=None):
        """
        Return pandas table
        """

        if channel_type=='resistance':
            return self._resistance_channel_table
        elif channel_type=='heater':
            return self._heater_channel_table
        elif channel_type is None:
            tables = list()
            if self._resistance_channel_table is not None:
                tables.append(self._resistance_channel_table)
            if self._heater_channel_table is not None:
                tables.append(self._heater_channel_table)
            return pd.concat(tables)
        else:
            raise ValueError('ERROR: channel type should be "resistance", "heater" or None!')
        
    

    def setup_instrument_from_config(self, setup_file):
        """
        Setup lakeshore
        """

        if setup_file is None or not os.path.isfile(setup_file):
            raise ValueError('ERROR: Setup file not found!')
        
        # get configuration
        config = settings.Config(setup_file=setup_file)
        lakeshore_setup = config.get_temperature_controller_setup(self._instrument_name)
     
        # loop modules and extract information
        try:

            # connection setup
            setup_dict = lakeshore_setup['setup']
         
            for key,item in setup_dict.items():

                # module information
                if 'model' in setup_dict:
                    self._model_number = int(setup_dict['model'])
                else:
                    raise ValueError('ERROR: Missing lakeshore model number in setup file!')
                if 'ip' in setup_dict:
                    self._ip_address = setup_dict['ip']
                    if 'tcp_port' in setup_dict:
                        self._tcp_port = int(setup_dict['tcp_port'])
                    else:
                        raise ValueError('ERROR: Missing lakeshore TCP port in setup file!')
                if 'com_port' in setup_dict:
                    self._com_port = setup_dict['com_port']
        
                if 'baud_rate' in setup_dict:
                    self._baud_rate = setup_dict['baud_rate']

                    
            # channel setup
            for chan_type in ['resistance', 'heater']:
                for chan in range(0,_MAX_NB_CHANNELS+1):
                    # parameter name
                    item_name = 'chan' + str(chan)
                    if chan_type=='heater':
                        item_name = 'heater' + str(chan)

                    # check if available
                    if item_name in lakeshore_setup:
                        chan_dict = lakeshore_setup[item_name]
                        
                        chan_name = None
                        if 'name' in chan_dict:
                            chan_name = chan_dict['name']
                        chan_number = None
                        if 'global_number' in chan_dict:
                            chan_number = int(chan_dict['global_number'])
                        device_type = None
                        if 'type' in chan_dict:
                            device_type = chan_dict['type']
                        device_serial = None
                        if 'serial' in chan_dict:
                            device_serial = chan_dict['serial']
                            
                        self.set_channel_names(channel_numbers=chan,
                                               channel_names=chan_name,
                                               global_channel_numbers=chan_number,
                                               device_types=device_type,
                                               device_serials=device_serial,
                                               channel_type=chan_type)
        except:
            raise ValueError('ERROR: Lakeshore setup file has unknown format!')


        
        
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
            print('INFO: Lakeshore ' + str(self._model_number) + ' connected!')



            
    
    def disconnect(self):
        """
        Close connection
        """

        if self._inst  is not None:
            if self._ip_address is None:
                self._inst.disconnect_usb()
            else:
                self._inst.disconnect_tcp()
    
        if self._verbose:
            print('INFO: Lakeshore ' + str(self._model_number) + ' disconnected!')
                



            
    def set_channel_names(self, channel_numbers, channel_names,
                          global_channel_numbers=None, channel_type='resistance',
                          device_types=None, device_serials=None,
                          replace=False):
        """
        Channel name map
        """

        # convert to list if needed
        if not isinstance(channel_numbers, list):
            channel_numbers = [channel_numbers]
        nb_channels = len(channel_numbers)
        
        if global_channel_numbers is None:
            global_channel_numbers = channel_numbers  
        elif not isinstance(global_channel_numbers, list):
            global_channel_numbers = [global_channel_numbers]
            
        if not isinstance(channel_names, list):
            channel_names = [channel_names]


        if device_types is None:
            device_types = [None]*nb_channels
        elif not isinstance(device_types, list):
            device_types = [device_types]

        if device_serials is None:
            device_serials = [None]*nb_channels
        elif not isinstance(device_serials, list):
            device_serials = [device_serials]
        

            
        if (len(channel_numbers) != len(channel_names) or
            len(global_channel_numbers) != len(channel_names)):
            raise ValueError('ERROR: channel numbers and names should be same length!')



        # Resistance/thermometer channels
        if channel_type=='resistance':

            # initialize if needed
            if self._resistance_channel_property_list is None:
                self._resistance_channel_property_list = list()
                self._resistance_channel_names = list()
                self._resistance_global_channel_numbers = list()

                
            # loop channels and add to list
            for ichan in range(len(channel_numbers)):

                # build property value list
                channel_property_values = [self._instrument_name,
                                           'ls-'+str(self._model_number), None, self._instrument_number, 
                                           self._ip_address, channel_numbers[ichan],
                                           global_channel_numbers[ichan], channel_names[ichan],
                                           device_types[ichan], device_serials[ichan]]


                
                # check if channel exist
                channel_index = None
                for ind in range(len(self._resistance_channel_property_list)):
                    if self._resistance_channel_property_list[ind][4]==channel_numbers[ichan]:
                        channel_index = ind

                if channel_index is None:
                    self._resistance_channel_property_list.append(channel_property_values)
                    self._resistance_channel_names.append(channel_names[ichan])
                    self._resistance_global_channel_numbers.append(global_channel_numbers[ichan])
                else:
                    if replace:
                        self._resistance_channel_property_list[channel_index] = channel_property_values
                        self._resistance_channel_names[channel_index] = channel_names[ichan]
                        self._resistance_global_channel_numbers[channel_index] = global_channel_numbers[ichan]
                    else:
                        raise ValueError('ERROR: Resistance channel ' + str(channel_numbers[ichan])
                                         + ' already exists!')
                

            # rebuild table
            self._resistance_channel_table = pd.DataFrame(self._resistance_channel_property_list,
                                                          columns=self._channel_properties)
            
                
        # heater channels
        if channel_type=='heater':

            # initialize if needed
            if self._heater_channel_property_list is None:
                self._heater_channel_property_list = list()
                self._heater_channel_names = list()
                self._heater_global_channel_numbers = list()

                
            # loop channels and add to list
            for ichan in range(len(channel_numbers)):

                # build property value list
                channel_property_values = [self._instrument_name,
                                           'ls-'+str(self._model_number), None, self._instrument_number, 
                                           self._ip_address, channel_numbers[ichan],
                                           global_channel_numbers[ichan], channel_names[ichan],
                                           device_types[ichan], device_serials[ichan]]


                
                # check if channel exist
                channel_index = None
                for ind in range(len(self._heater_channel_property_list)):
                    if self._heater_channel_property_list[ind][4]==channel_numbers[ichan]:
                        channel_index = ind

                if channel_index is None:
                    self._heater_channel_property_list.append(channel_property_values)
                    self._heater_channel_names.append(channel_names[ichan])
                    self._heater_global_channel_numbers.append(global_channel_numbers[ichan])
                else:
                    if replace:
                        self._heater_channel_property_list[channel_index] = channel_property_values
                        self._heater_channel_names[channel_index] = channel_names[ichan]
                        self._heater_global_channel_numbers[channel_index] = global_channel_numbers[ichan]
                    else:
                        raise ValueError('ERROR: Heater channel ' + str(channel_numbers[ichan])
                                         + ' already exists!')
                

            # rebuild table
            self._heater_channel_table = pd.DataFrame(self._heater_channel_property_list,
                                                          columns=self._channel_properties)
                

          



    def get_channel_parameters(self, channel_numbers=None, channel_names=None,
                               global_channel_numbers=None):
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


        if channel_names is not None or global_channel_numbers is not None:
            channel_numbers = self._extract_channel_numbers(channel_names=channel_names,
                                                            global_channel_numbers=global_channel_numbers)

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
                        global_channel_number=None,
                        manual_conversion=False):
        
        """
        Get temperature
        """
        

        # get channel number if channel name or global_channel_number provided
        if channel_name is not None or global_channel_number is not None:
            channel_number = self._extract_channel_numbers(channel_names=channel_name,
                                                           global_channel_numbers=global_channel_number)
            if len(channel_number)==1:
                channel_number = channel_number[0]
            else:
                raise ValueError('ERROR: Unable to extract channel number!')
                

        # query temperature
        query_command = 'RDGK? ' + str(channel_number)
        temperature = float(self._inst.query(query_command))

        return temperature
        

    def get_resistance(self, channel_number=None, channel_name=None,
                       global_channel_number=None):
        
        """
        Get resistance
        """
        
        # get channel number if channel name or global_channel_number provided
        if channel_name is not None or global_channel_number is not None:
            channel_number = self._extract_channel_numbers(channel_names=channel_name,
                                                           global_channel_numbers=global_channel_number)
            if len(channel_number)==1:
                channel_number = channel_number[0]
            else:
                raise ValueError('ERROR: Unable to extract channel number!')
            

        # query resistance
        query_command = 'RDGR? ' + str(channel_number)
        resistance = float(self._inst.query(query_command))

        return resistance

    

    def get_pid_control(self, heater_channel_number=None,
                        heater_channel_name=None,
                        heater_global_channel_number=None):
        """
        Get control setup
        """


        # get heater channel number
        if heater_channel_name is not None or heater_global_channel_number is not None:
            heater_channel_number = self._extract_channel_numbers(channel_names=heater_channel_name,
                                                                  global_channel_numbers=heater_global_channel_number,
                                                                  channel_type='heater')
            
            if len(heater_channel_number)==1:
                heater_channel_number = heater_channel_number[0]
            else:
                raise ValueError('ERROR: Unable to extract channel number!')
            

        # initialize output 
        output = dict()
        output['heater_channel_number'] =  heater_channel_number
        if heater_channel_name is not None:
            output['heater_channel_name']  = heater_channel_name
        if heater_global_channel_number is not None:
            output['heater_global_channel_number'] = heater_global_channel_number 
        
        # Output mode
        query_command = 'OUTMODE? ' + str(heater_channel_number)
        result = self._inst.query(query_command)
        result_split = result.split(',')

        mode = int(result_split[0])
        output['mode'] = mode
        output['pid_enabled'] = False
        mode_string = 'off'
        if mode==1:
            mode_string = 'monitor_out'
        elif mode==2:
            mode_string = 'manual'
        elif mode==3:
            mode_string = 'zone'
        elif mode==4:
            mode_string = 'still'
        elif mode==5:
            mode_string = 'closed_loop'
            output['pid_enabled'] = True
        elif mode==6:
            mode_string = 'warm_up'

        
        output['mode_description'] = mode_string
        output['input_channel_number'] =  result_split[1]
        output['powerup_enable'] =  int(result_split[2])
        output['polarity'] = int(result_split[3])
        output['filter'] = int(result_split[4])
        output['delay'] =int(result_split[5])
        
        # PID parameters
        query_command = 'PID? ' + str(heater_channel_number)
        result = self._inst.query(query_command)
        result_split = result.split(',')
        output['P'] = float(result_split[0])
        output['I'] = float(result_split[1])
        output['D'] = float(result_split[2])
        
                
        # Setpoint
        query_command = 'SETP? ' + str(heater_channel_number)
        result = self._inst.query(query_command)
        result_split = result.split(',')
        output['setpoint'] =  result_split[0]



        # done
        return output

        

    

    def set_pid_control(self, on=None,
                        heater_channel_number=None, heater_channel_name=None,
                        heater_global_channel_number=None,
                        P=None, I=None, D=None,
                        channel_number=None, channel_name=None, global_channel_number=None):
        """
        PID control
        """

        # get input and heater channel numbers
        if (channel_number is None and
            (channel_name is not None or global_channel_number is not None)):
            channel_number = self._extract_channel_numbers(
                channel_names=channel_name,
                global_channel_numbers=global_channel_number,
                channel_type='resistance')

        if (heater_channel_number is None and
            (heater_channel_name is not None or heater_global_channel_number is not None)):
            heater_channel_number = self._extract_channel_numbers(
                channel_names=heater_channel_name,
                global_channel_numbers=heater_global_channel_number,
                channel_type='heater')


        if heater_channel_number is None:
            raise ValueError('ERROR: heater channel number or name is required!')

        

        
        # get current state
        pid_control_params = self.get_pid_control(heater_channel_number=heater_channel_number)


        
        # Set PID parameter
        if P is not None or I is not None or D is not None:
            if P is None:
                P = pid_control_params['P']
            if I is None:
                I = pid_control_params['I']
            if D is None:
                D = pid_control_params['D']
                
            write_command = 'PID ' + str(heater_channel_number)
            write_command += ',' + str(P) + ',' + str(int(I)) + ',' + str(int(D))
            if self._debug:
                print('DEBUG: Write command to lakeshore =  ' + write_command)
            self._inst.command(write_command)


        # Set input channel and turn on
        if on is not None or channel_number is not None:
            
            # mode 
            mode = pid_control_params['mode']
            if type(on)==bool:
                if on:
                    mode = 5
                else:
                    mode = 0

            # input channel
            input_channel_number = pid_control_params['input_channel_number']
            if channel_number is not None:
                input_channel_number = channel_number


            # write
            write_command = 'OUTMODE '  + str(heater_channel_number)
            write_command += ',' + str(mode) + ',' + str(input_channel_number)
            write_command += ',' + str(pid_control_params['powerup_enable'])
            write_command += ',' + str(pid_control_params['polarity'])
            write_command += ',' + str(pid_control_params['filter'])
            write_command += ',' + str(pid_control_params['delay'])
 
            
            if self._debug:
                print('DEBUG: Write command to lakeshore =  ' + write_command)

            self._inst.command(write_command)

   
        
    
    
    def set_temperature(self,  temperature,
                        heater_channel_number=None,
                        heater_channel_name=None,
                        heater_global_channel_number=None,
                        channel_number=None,
                        channel_name=None,
                        global_channel_number=None,
                        wait_temperature_reached=False,
                        wait_cycle_time=30,
                        wait_stable_time=300,
                        max_wait_time=1200,
                        tolerance=0.2):
        """
        Set temperature
        """


        # get  heater channel
        if (heater_channel_number is None and
            (heater_channel_name is not None or heater_global_channel_number is not None)):
            heater_channel_number = self._extract_channel_numbers(
                channel_names=heater_channel_name,
                global_channel_numbers=heater_global_channel_number,
                channel_type='heater')

        if heater_channel_number is None:
            raise ValueError('ERROR: heater channel number or name is required!')

        # get input channel number
        if (channel_number is None and
            (channel_name is not None or global_channel_number is not None)):
            channel_number = self._extract_channel_numbers(
                channel_names=channel_name,
                global_channel_numbers=global_channel_number,
                channel_type='resistance')

        if channel_number is None:
            raise ValueError('ERROR: thermometer channel number or name is required!')


        # check PID control
        pid_control_params = self.get_pid_control(heater_channel_number=heater_channel_number)
        if not pid_control_params['pid_enabled']:
            raise ValueError('ERROR: PID Control not enabled! Use "set_pid_control" function" to setup PID.')

        if pid_control_params['input_channel_number'] != channel_number:
            if self._verbose:
                print('WARNING: PID input channel not accurate. Setting input channel number = '
                      + str(channel_number) + '!')
            self.set_pid_control(heater_channel_number=heater_channel_number,
                                 channel_number=channel_number)
            

        # check input parameters
        channel_params = self.get_channel_parameters(channel_number=channel_number)
        if not channel_params['enabled']:
            error_msg = 'ERROR: Input thermometer channel not enabled! '
            error_msg += 'Use "enable_channels" function" to enable channel.'
            raise ValueError(error_msg)

        # reading units
        if channel_params['reading_units'] != 'kelvin':
            error_msg = 'ERROR: Input thermometer reading unit is not "kelvin"! '
            error_msg += 'Use "set_channel_parameters" function" to setup channel.'
            raise ValueError(error_msg)

        # channel enabled
        channel_enable_list = self.get_channel_enabled_list()
        if len(channel_enable_list)>1:
            print('WARNING: Multiple channels enabled. The PID control will be affected!')
            print('Disabling all channels except input thermometer...')
            self.enable_channels(channel_numbers=channel_number,
                                 disable_other=True)
            
             
        # set point
        write_command = 'SETP ' + str(heater_channel_number)
        write_command += ',' + str(temperature)
        
        if self._debug:
            print('DEBUG: Write command to lakeshore =  ' + write_command)  
        self._inst.command(write_command)


        # wait time
        if wait_temperature_reached:

            # number of cycles
            nb_cycles = int(round(max_wait_time/wait_cycle_time))
            if nb_cycles<1:
                nb_cycles = 1

            # initialize stable time
            time_stable = time.perf_counter()
                
            # loop cycle
            for icycle in range(nb_cycles):

                # current time and temperature
                time_now = time.perf_counter()
                temperature_now = self.get_temperature(channel_number=channel_number)

                # check tolerance
                if abs(temperature_now-temperature)/temperature_now > tolerance:
                    # reset stable time 
                    time_stable =  time_now

                if time_stable-time_now > wait_stable_time:
                    if self._verbose:
                        print('INFO: Temperature ' + str(temperature_now*1000) + 'mK reached!')
                    break
                
            # re-enable channels
            self.enable_channels(channel_numbers=channel_enable_list,
                                 disable_other=True)
            
            
            


    

    

    
    def set_channel_parameters(self, channel_numbers=None, channel_names=None,
                               global_channel_numbers=None,
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

        # extract channel numbers if names or global numbers provided
        if channel_names is not None or global_channel_numbers is not None:
            channel_numbers = self._extract_channel_numbers(channel_names=channel_names,
                                                            global_channel_numbers=global_channel_numbers)

        if not isinstance(channel_numbers, list):
            channel_numbers  = [channel_numbers]
            
            
          
        # loop all channels
        for chan in range(1, _MAX_NB_CHANNELS+1):
       
            # selected channel
            if chan in channel_numbers:

                current_setup = self.get_channel_parameters(channel_numbers=chan)[chan]
                
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
                current_setup = self.get_channel_parameters(channel_numbers=chan)[chan]

                # build command
                command_list = [0, current_setup['dwell_time'], current_setup['pause_time'],
                                current_setup['curve_number'], current_setup['tempco']]          
                command = 'INSET ' + str(chan)
                for param in command_list:
                    command += ',' + str(param)

                # write
                self._inst.command(command)
                                
            
 
    def enable_channels(self, channel_numbers=None, channel_names=None,
                        global_channel_numbers=None,
                        disable_other=False):
        
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

        
        # extract channel numbers if names or global numbers provided
        if channel_names is not None or global_channel_numbers is not None:
            channel_numbers = self._extract_channel_numbers(channel_names=channel_names,
                                                            global_channel_numbers=global_channel_numbers)

        if not isinstance(channel_numbers, list):
            channel_numbers  = [channel_numbers]
                   

        # enable channels
        self.set_channel_parameters(channel_numbers=channel_numbers,
                                    enable=True, disable_other=disable_other)



        
                         
    def disable_channels(self, channel_numbers=None, channel_names=None,
                        global_channel_numbers=None):    
        """
        Disable input channel
        
        Parameters
        ----------
        channel_numbers: int or list
           channel number (s)  (1-16)

        """

        # extract channel numbers if names or global numbers provided
        if channel_names is not None or global_channel_numbers is not None:
            channel_numbers = self._extract_channel_numbers(channel_names=channel_names,
                                                            global_channel_numbers=global_channel_numbers)

        if not isinstance(channel_numbers, list):
            channel_numbers  = [channel_numbers]
                   


        # enable channels
        self.set_channel_parameters(channel_numbers=channel_numbers,
                                    enable=False)

     


        
            
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
        data_dict = self.get_channel_parameters(channel_numbers=list(range(1,17)))

        # loop and check if channel enabled
        for chan,info in data_dict.items():
            if info['enabled']:
                chan_list.append(chan)

        return chan_list

    

            
    def select_channel(self, channel_number=None, channel_name=None,
                       global_channel_number=None, autoscan=False):
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

        # get channel number if channel name or global_channel_number provided
        if channel_name is not None or global_channel_number is not None:
            channel_number = self._extract_channel_numbers(channel_names=channel_name,
                                                           global_channel_numbers=global_channel_number)
            if len(channel_number)==1:
                channel_number = channel_number[0]
            else:
                raise ValueError('ERROR: Unable to extract channel number!')
        

        # check channel
        if channel_number not in list(range(1,17)):
            print('ERROR: channel number should be between 1-16')
            if self._raise_errors:
                raise
            else:
                return
        
        command = 'SCAN ' + str(channe_number) + ',' + str(int(autoscan))
        self._inst.command(command)
        


        
        
    def start_scan(self, channel_number=None, channel_name=None, global_channel_number=None):
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
                              channel_name=channel_name,
                              global_channel_number=global_channel_number)


        
    def stop_scan(self, channel_number=None, channel_name=None, global_channel_number=None):
        """
        Stop scanning, keeping channels enabled
         
        Arguments:
        ----------
        chan_num: int  (optional)
           Selected channel  number (1-16)
           Default: first channel
        """
        
        self._scan_start_stop(False, channel_number=channel_number,
                              channel_name=channel_name,
                              global_channel_number=global_channel_number)

                
        
        
    def _scan_start_stop(self, enabled, channel_number=None, channel_name=None,
                         global_channel_number=None):
        """
        Start/Stop scanning and select channel
        
        Arguments:
        ----------
        chan_num: int  (optional)
           Channel number selected
           Default: first channel
        """

        # get channel number if channel name or global_channel_number provided
        if channel_name is not None or global_channel_number is not None:
            channel_number = self._extract_channel_numbers(channel_names=channel_name,
                                                           global_channel_numbers=global_channel_number)
            if len(channel_number)==1:
                channel_number = channel_number[0]
            else:
                raise ValueError('ERROR: Unable to extract channel number!')
        

        
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




    def _extract_channel_numbers(self, channel_names=None,
                                 global_channel_numbers=None,
                                 channel_type='resistance'):
        """ 
        Get channel numbers
        """

        

        # get table
        channel_table = self._resistance_channel_table
        if channel_type=='heater':
            channel_table = self._heater_channel_table
            
        
        channel_numbers = list()
        if channel_names is not None:

            # convert to list
            if not isinstance(channel_names, list):
                channel_names = [channel_names]

            # loop
            for chan in channel_names:
                channel_number = channel_table.query('channel_name == @chan')['channel_number'].values
                if len(channel_number)>1:
                    raise ValueError('ERROR: Multiple channel numbers found for "' + chan + '"!')
                elif len(channel_number)==1:
                    channel_number = channel_number[0]
                else:
                    raise ValueError('ERROR: No channel found for "' + chan + '"!')

                # append to list
                channel_numbers.append(channel_number)
                

        elif global_channel_numbers is not None:

            # convert to list
            if not isinstance(global_channel_numbers, list):
                global_channel_numbers = [global_channel_numbers]

            # loop
            for chan in global_channel_numbers:
                channel_number = channel_table.query('global_channel_number == @chan')['channel_number'].values
                if len(channel_number)>1:
                    raise ValueError('ERROR: Multiple channel numbers found for global channel number "'
                                     + str(chan) + '"!')
                elif len(channel_number)==1:
                    channel_number = channel_number[0]
                else:
                    raise ValueError('ERROR: No channel found for global channel number "'
                                     + str(chan) + '"!')
                # append to list
                channel_numbers.append(channel_number)
     
        return channel_numbers
                    

