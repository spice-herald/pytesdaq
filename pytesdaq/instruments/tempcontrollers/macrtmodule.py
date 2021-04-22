import time
import pandas as pd
from pytesdaq.instruments.communication import InstrumentComm


    
class MACRTModule(InstrumentComm):
    """
    MMR3: Module de Mesure de Résistances 3 voies (thermometers control)
    MGC3: Module Générateur de Courant 3 voies (heaters control)
    """

    def __init__(self, module_type, module_name, ip_address, module_num = None,
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
        self._module_num =  module_num
        self._module_type = module_type.upper()
        if self._module_type not in ['MMR3', 'MGC3']:
            raise ValueError('ERROR: Module type should be MMR3 or MGC3')


        # module identification
        self._module_idn = None
        try:
            result  = self.query('*IDN', coding='ascii')
            self._module_idn = result[0:result.rfind('_')]
        except:
            raise ValueError('ERROR: Unable to get module identification!')


        if self._verbose:
            print('INFO: Creating module "' + self._module_idn + '" (' + self._ip_address + ')')
        
        
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
        self._global_channel_nums = None
        self._channel_properties = ['module_name', 'module_type', 'module_num',
                                    'module_address', 'channel_num', 'global_channel_num',
                                    'channel_name', 'device_type', 'device_serial']
        
        
    @property
    def type(self):
        return self._module_type

    @property
    def name(self):
        return self._module_name

    @property
    def idn(self):
        return self._module_idn
      
    @property
    def num(self):
        return self._module_num

    @property
    def ip_address(self):
        return self._ip_address


    @property
    def channel_names(self):
        return self._channel_names

    @property
    def global_channel_nums(self):
        return self._global_channel_nums


    def add_channels(self, channel_nums, channel_names, global_channel_nums=None,
                     device_types=None, device_serials=None, replace=False):
        """`
        Add channel
        
        Parameters
        ----------
               

        Return
        ----------

        """
        

        # convert arguments to list
        if not isinstance(channel_nums, list):
            channel_nums = [channel_nums]
        nb_channels = len(channel_nums)
            
        if not isinstance(channel_names, list):
            channel_names = [channel_names]

        if global_channel_nums is None:
            global_channel_nums = [None]*nb_channels
        elif not isinstance(global_channel_nums, list):
            global_channel_nums = [global_channel_nums]

        if device_types is None:
            device_types = [None]*nb_channels
        elif not isinstance(device_types, list):
            device_types = [device_types]

        if device_serials is None:
            device_serials = [None]*nb_channels
        elif not isinstance(device_serials, list):
            device_serials = [device_serials]
        
            
        # check length
        if not all(param_len==nb_channels for param_len in [len(channel_names), len(global_channel_nums),
                                                        len(device_types), len(device_serials)]):
            raise ValueError('ERROR in add_channels: all the parameters should have same length!')

        
        # initialize list if needed:
        if self._channel_list is None:
            self._channel_list = list()
            self._channel_names = list()
            self._global_channel_nums = list()

            
        # loop channels and add to list
        for ichan in range(len(channel_nums)):

            #  build list of channel properties
            channel_index = None
            channel_properties = [self._module_name, self._module_type, self._module_num , self._ip_address,
                               channel_nums[ichan], global_channel_nums[ichan],
                               channel_names[ichan], device_types[ichan], device_serials[ichan]]
            
            # check if channel exist
            channel_index = None
            for ind in range(len(self._channel_list)):
                if self._channel_list[ind][0]==channel_nums[ichan]:
                    channel_index = ind

            if channel_index is None:
                self._channel_list.append(channel_properties)
                self._channel_names.append(channel_names[ichan])
                self._global_channel_nums.append(global_channel_nums[ichan])
            else:
                if replace:
                    self._channel_list[channel_index] = channel_properties
                    self._channel_names[han_index] = channel_names[ichan]
                    self._global_channel_nums[channel_index] = global_channel_nums[ichan]
                else:
                    raise ValueError('ERROR: channel ' + str(channel_nums[ichan]) + 'already exists!')
                

        # rebuild table
        self._channel_table = pd.DataFrame(self._channel_list, columns = self._channel_properties)




        
        
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

    def get_channel_num(self, channel_name=None, global_channel_num=None):
        """
        Get channel number (0,1, or 2) 
        """

        channel_num = None

        # get channel num
        if channel_name is not None:
            channel_num = self._channel_table.query('channel_name == @channel_name')['channel_num'].values
        elif global_channel_num is not None:
            channel_num = self._channel_table.query('global_channel_num == @global_channel_num')['channel_num'].values
            
        # check length
        if len(channel_num)>1:
            raise ValueError('ERROR: Multiple channel numbers found for same name or global channel number')
        elif len(channel_num)==1:
            channel_num = channel_num[0]
        else:
            raise ValueError('ERROR: No device found. Please check setup with info()!')
           

        return channel_num

    
        

    def get(self, param_name, channel_num=None, global_channel_num=None, channel_name=None):
        """
        Read parameter
        
        Parameters
        ----------
               

        Return
        ----------

        """

        # get index paramter
        idx = self._extract_param_index(param_name, channel_num, global_channel_num,channel_name)

        # build command
        cmd = self._get_cmd.format(param_idx=idx)

        if self._debug:
            print('DEBUG: Query command = "' + str(cmd) + '"')
            
        # get
        param_val = self.query(cmd, coding='ascii')


        
        return param_val



    

    def set(self, param_name, param_val, channel_num=None, global_channel_num=None,
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
        idx = self._extract_param_index(param_name, channel_num, global_channel_num, channel_name)

        # build command
        cmd = self._set_cmd.format(param_idx=idx, value=param_val)

        if self._debug:
            print('DEBUG: Query command = "' + str(cmd) + '"')
         
        
        # set
        param_val = self.write(cmd, coding='ascii')

        return param_val
    

        

    def _extract_param_index(self, param_name, channel_num=None, global_channel_num=None,
                             channel_name=None):
        """
        Extract parameter index
        """
        
        
        # check if channel available
        if (self._channel_table is None and
            (channel_name is not None or channel_num is not None)):
            raise ValueError('ERROR: No channel available for the ' +
                             self._module_type + ' module!')

        
        # get channel number
        if channel_name is not None or global_channel_num is not None:
            channel_num = self.get_channel_num(channel_name=channel_name,
                                               global_channel_num=global_channel_num)
        elif channel_num is None:
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
                channel_mult = channel_num if items[1] else 0
                param_idx += channel_mult*len(items[0])
                param_idx += idx[0]
                is_valid = True
                break

        if not is_valid:
            raise ValueError('ERROR: No parameter "' + param_name +
                             '" found for ' + self._module_type + ' module ' + self._module_name)
        


        if self._debug:
            print('DEBUG: Parameter: ' + param_name)
            if channel_num is not None:
                print('DEBUG: Channel index: ' + str(channel_num))
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
                
                    
             
                    
        
  
    


