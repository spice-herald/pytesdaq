import time
import pandas as pd
from pytesdaq.instruments.communication import InstrumentComm


    
class MACRTModule(InstrumentComm):
    """
    MMR3: Module de Mesure de Résistances 3 voies (thermometers control)
    MGC3: Module Générateur de Courant 3 voies (heaters control)
    """

    def __init__(self, module_type, module_name, ip_address, module_number=None,
                 protocol='udp', verbose=True):
        super().__init__(protocol=protocol, termination='\n', raise_errors=True,
                         verbose=verbose)
        
        # debug
        self._debug = True
        
      
        # port/IP address
        self._ip_address = ip_address
        
        port = 12000
        if protocol=='tcp':
            port = 11000
        port += int(ip_address.split('.')[-1])
        
        self.set_address(ip_address=ip_address, port=port, recv_port=12000)


        
        # module name and type
        self._module_name = module_name
        self._module_number =  module_number
        self._module_type = module_type.upper()
        if self._module_type not in ['MMR3', 'MGC3']:
            raise ValueError('ERROR: Module type should be MMR3 or MGC3')


        # module identity
        self._module_identity = None
        try:
            result  = self.query('*IDN', coding='ascii')
            self._module_identity = result[0:result.rfind('_')]
        except:
            raise ValueError('ERROR: Unable to get module identification!')


        if self._verbose:
            print('INFO: Creating module "' + self._module_identity
                  + '" (' + self._ip_address + ')')
        
        
        # Measure/Control parameters      
        if self._module_type == 'MMR3':
            self._parameters = [([('period', True), ('DtADC', True), ('temperature', False)], False),
                                ([('R', False), ('range', False), ('X', False),
                                  ('status', False), ('avg', True),
                                  ('range_mode', True), ('range_mode_I', True),
                                  ('range_I', True), ('range_U', True),
                                  ('I', True), ('offset', False)], True)]
            
        if self._module_type == 'MGC3':
            self._parameters = [([('temperature', False)], False),
                                ([('onoff', True), ('setpoint', True), ('measure', False),
                                  ('P', True),  ('I', True), ('D', True),
                                  ('pmax', True), ('R', True), ('S', False),
                                  ('status', False), ('name', True), ('channel', True)], True),
                                ([('I', True), ('status', False)], True),
                                ([('U', False), ('TTL_1', True), ('TTL_2', True)], False)]
            
        # command
        self._get_cmd = self._module_type + 'GET {param_idx}'
        self._set_cmd = self._module_type + 'SET {param_idx} {value}'
        
        

        # channels
        self._channel_table = None
        self._channel_list = None
        self._channel_names = None
        self._channel_numbers = None
        self._channel_properties = ['module_name', 'module_type', 'module_number',
                                    'module_address', 'channel_index', 'channel_number',
                                    'channel_name', 'device_type', 'device_serial']
        
        
    @property
    def type(self):
        return self._module_type

    @property
    def name(self):
        return self._module_name

    @property
    def identity(self):
        return self._module_identity
      
    @property
    def number(self):
        return self._module_number

    @property
    def ip_address(self):
        return self._ip_address


    @property
    def channel_names(self):
        return self._channel_names

    @property
    def channel_numbers(self):
        return self._channel_numbers


    def add_channels(self, channel_indices, channel_names, channel_numbers=None,
                     device_types=None, device_serials=None, replace=False):
        """`
        Add channel
        
        Parameters
        ----------
               

        Return
        ----------

        """
        

        # convert arguments to list
        if not isinstance(channel_indices, list):
            channel_indices = [channel_indices]
        nb_channels = len(channel_indices)
            
        if not isinstance(channel_names, list):
            channel_names = [channel_names]

        if channel_numbers is None:
            channel_numbers = [None]*nb_channels
        elif not isinstance(channel_numbers, list):
            channel_numbers = [channel_numbers]

        if device_types is None:
            device_types = [None]*nb_channels
        elif not isinstance(device_types, list):
            device_types = [device_types]

        if device_serials is None:
            device_serials = [None]*nb_channels
        elif not isinstance(device_serials, list):
            device_serials = [device_serials]
        
            
        # check length
        if not all(param_len==nb_channels for param_len in [len(channel_names), len(channel_numbers),
                                                            len(device_types), len(device_serials)]):
            raise ValueError('ERROR in add_channels: all the parameters should have same length!')

        
        # initialize list if needed:
        if self._channel_list is None:
            self._channel_list = list()
            self._channel_names = list()
            self._channel_numbers = list()

            
        # loop channels and add to list
        for ichan in range(len(channel_indices)):

            #  build list of channel properties
            channel_index = None
            channel_properties = [self._module_name, self._module_type, self._module_number ,
                                  self._ip_address, channel_indices[ichan], channel_numbers[ichan],
                                  channel_names[ichan], device_types[ichan], device_serials[ichan]]
            
            # check if channel exist
            channel_index = None
            for ind in range(len(self._channel_list)):
                if self._channel_list[ind][0]==channel_indices[ichan]:
                    channel_index = ind

            if channel_index is None:
                self._channel_list.append(channel_properties)
                self._channel_names.append(channel_names[ichan])
                self._channel_numbers.append(channel_numbers[ichan])
            else:
                if replace:
                    self._channel_list[channel_index] = channel_properties
                    self._channel_names[han_index] = channel_names[ichan]
                    self._channel_numbers[channel_index] = channel_numbers[ichan]
                else:
                    raise ValueError('ERROR: channel ' + str(channel_indices[ichan])
                                     + ' already exists!')
                

        # rebuild table
        self._channel_table = pd.DataFrame(self._channel_list, columns=self._channel_properties)




        
        
    def print_info(self):
        """
        """
        print('Module ' + self._module_type + ': ' + self._module_name
              + ' (' + self._ip_address + ')')
        if self._channel_table is not None:
            print('Channel Table:')
            print(self._channel_table.to_string(index=False))
        else:
            print('No Channels available')

                
    def get_info(self):
        """
        """
        return self._channel_table


    
    def get_channel_index(self, channel_name=None, channel_number=None):
        """
        Get channel index (0,1, or 2) 
        """

        
        # query string
        query_string = str()
        if channel_name is not None:
            query_string = 'channel_name == @channel_name'
        elif channel_number is not None:
            query_string = 'channel_number == @channel_number'
        else:
            raise ValueError('ERROR: channel name or number needs to be provided!')

        # query
        channel_index = self._channel_table.query(query_string)['channel_index'].values
        
        # check length
        if len(channel_index)>1:
            raise ValueError('ERROR: Multiple channel numbers found for same name or global channel number')
        elif len(channel_index)==1:
            channel_index = channel_index[0]
        else:
            raise ValueError('ERROR: No device found. Please check setup with info()!')
           

        return channel_index

    
        

    def get(self, param_name, channel_index=None, channel_number=None, channel_name=None):
        """
        Read parameter
        
        Parameters
        ----------
               

        Return
        ----------

        """

        # get index paramter
        idx = self._extract_param_index(param_name, channel_index, channel_number, channel_name)

        # build command
        cmd = self._get_cmd.format(param_idx=idx)

        if self._debug:
            print('DEBUG: Query command = "' + str(cmd) + '"')
            
        # get
        param_val = self.query(cmd, coding='ascii')


        
        return param_val



    

    def set(self, param_name, param_val, channel_index=None, channel_number=None,
            channel_name=None):
        
        """
        Read parameter
        
        Parameters
        ----------
               

        Return
        ----------

        """

        # check if parameter writable
        if not self._is_writable(param_name):
            print('WARNING: paramter "' + param_name + '" is not writable!')
            return
        
        
        # get index paramter
        idx = self._extract_param_index(param_name, channel_index, channel_number, channel_name)

        # build command
        cmd = self._set_cmd.format(param_idx=idx, value=param_val)

        if self._debug:
            print('DEBUG: Query command = "' + str(cmd) + '"')
         
        
        # set
        param_val = self.write(cmd, coding='ascii')

        return param_val
    

        

    def _extract_param_index(self, param_name, channel_index=None, channel_number=None,
                             channel_name=None):
        """
        Extract parameter index
        """
        
        
        # check if channel available
        if (self._channel_table is None and
            (channel_name is not None or channel_index is not None)):
            raise ValueError('ERROR: No channel available for the ' +
                             self._module_type + ' module!')

        
        # get channel number
        if channel_name is not None or channel_number is not None:
            channel_index = self.get_channel_index(channel_name=channel_name,
                                                   channel_number=channel_number)
        elif channel_index is None:
            raise ValueError('ERROR: A channel number needs to be provided!')

       
             
        # get property index
        param_idx = 0
        is_valid = False
        for items in self._parameters:
            idx = [x for x, y in enumerate(items[0]) if y[0] == param_name]
            if not idx:
                channel_mult = 3 if items[1] else 1
                param_idx += len(items[0])*channel_mult
                continue
            else:
                channel_mult = channel_index if items[1] else 0
                param_idx += channel_mult*len(items[0])
                param_idx += idx[0]
                is_valid = True
                break

        if not is_valid:
            raise ValueError('ERROR: No parameter "' + param_name +
                             '" found for ' + self._module_type + ' module ' + self._module_name)
        


        if self._debug:
            print('DEBUG: Parameter: ' + param_name)
            if channel_index is not None:
                print('DEBUG: Channel index: ' + str(channel_index))
            print('DEBUG: Command value: ' + str(param_idx))
            

        
        return param_idx
            


    
    def _is_writable(self, param_name):
        """
        Check if parameter is writable
        """
        param_found = False
        is_writable = False
        for items in self._parameters:
            for param in items[0]:
                if param[0]==param_name:
                    is_writable = param[1]
                    param_found = True
                    break


        if not param_found:
            print('WARNING: parameter "' + param_name + '" not found!')

        return is_writable
                
                    
             
                    
        
  
    


