import time
from enum import Enum
from .macrtmodule import MACRTModule
from pytesdaq.instruments.communication import InstrumentComm
from pytesdaq.config import settings
import os
import stat


class MACRT(InstrumentComm):
    """
    MARCT: Module Autonome pour le Contrôle et la Régulation de Température
    """
    
    def __init__(self, protocol='udp', timeout=2, verbose=True):
        super().__init__(protocol=protocol, termination='\n', raise_errors=True,
                         verbose=verbose)


        self._protocol = protocol
        self._verbose = verbose
        self._timeout = timeout


        # module list
        self._module_list = None
        
        


    def setup_modules_from_config(self, setup_file):
        """
        Setup modules from config
        """

        if not os.path.isfile(setup_file):
            raise ValueError('ERROR: Setup file not found!')
        
        # instantiate config
        config = settings.Config(setup_file=setup_file)
        
        # get setup dictionary
        macrt_setup = config.get_temperature_controller_setup('macrt')

        # loop modules and extract information
        try:
            modules = macrt_setup['modules']
           
            for key,item in modules.items():
            
                # module information
                module_number = int(key[6:])
                module_name = item
                module_setup = macrt_setup[module_name+'_setup']
            
                module_type = None
                if 'type' in module_setup:
                    module_type =  module_setup['type'].upper()
                module_ip = None
                if 'ip' in module_setup:
                    module_ip = module_setup['ip']

                                          
                # add module
                self.add_module(module_type=module_type,
                                module_name=module_name,
                                module_ip=module_ip,
                                module_number=module_number)


                # add channels
                for ichan in range(0,3):
                    item_name = module_name + '_chan' + str(ichan)
                    if item_name in macrt_setup:
                        chan_dict = macrt_setup[item_name]
                        chan_name = None
                        if 'name' in chan_dict:
                            chan_name = chan_dict['name']
                        chan_number = None
                        if 'number' in chan_dict:
                            chan_number = chan_dict['number']
                        device_type = None
                        if 'type' in chan_dict:
                            device_type = chan_dict['type']
                        device_serial = None
                        if 'serial' in chan_dict:
                            device_serial = chan_dict['serial']
                            
                        self.add_module_channels(module_name=module_name,
                                                 channel_indices=ichan,
                                                 channel_names=chan_name,
                                                 channel_numbers=chan_number,
                                                 device_types=device_type,
                                                 device_serials=device_serial)
                    
        except:
            raise ValueError('ERROR: MACRT setup file has unknown format!')



        
    def add_module(self, module_type, module_name, module_ip, module_number=None,
                   channel_indices=None, channel_numbers=None, channel_names=None,
                   device_types=None, device_serials=None, replace=False):
        """
        Add MACRT modules
        
        Argument
        """        
        # initialize / check if module already exit
        if self._module_list is None:
            self._module_list = list()
        else:
            pass
            
            
        # instanciate module
        module = MACRTModule(module_type, module_name, module_ip, module_number,
                             protocol=self._protocol, verbose=self._verbose)
        

        # add channels
        if channel_indices is not None:
            module.add_channels(channel_indices=channel_indices, channel_names=channel_names,
                                channel_numbers=channel_numbers,
                                device_types=device_types, device_serials=device_serials,
                                replace=replace)
            
        # append to list
        self._module_list.append(module)
        


        
        
    def add_module_channels(self, module_name=None, module_number=None, module_ip=None,
                            channel_indices=None, channel_names=None, channel_numbers=None,
                            device_types=None, device_serials=None, replace=False):
        
        """
        """

        # get module
        module = self.get_module(module_name=module_name, module_number=module_number,
                                 module_ip=module_ip)

        if module is not None:
            module.add_channels(channel_indices=channel_indices, channel_names=channel_names,
                                channel_numbers=channel_numbers,
                                device_types=device_types, device_serials=device_serials,
                                replace=replace)
    


            
        
    def scan_modules(self, broadcast_address):
        """
        """
        #response = self.scan('0 1', 8001, broadcast_address)
        print('NOT WORKING :-(')
        return

            

    def get_module(self, module_name=None, module_number=None, module_ip=None,
                   module_type=None, channel_name=None, channel_number=None):
        """
        """
        
        module_output = None

        # check if module list exist
        if self._module_list is None:
            print('WARNING: No modules available!')
            return None

        # use upper case for module type
        if module_type is not None:
            module_type = module_type.upper()
            
            # loop modules
        nb_modules = 0
        for module in self._module_list:
            
            if ((module_name is not None and module.name == module_name)  
                or (module_number is not None and module.number == module_number)
                or (module_ip is not None  and module.ip_address == module_ip)
                or (module_type is not None and module.type == module_type)
                or (channel_name is not None and channel_name in module.channel_names)
                or (channel_number is not None
                    and channel_number in module.channel_numbers)):
                
                # module type
                if (module_type is not None and module.type != module_type):
                    continue
                else:
                    module_output = module
                    nb_modules += 1
                    
                
        # display warning
        if nb_modules==0:
            raise ValueError('ERROR: No module found!')
        elif nb_modules>1:
            raise ValueError('ERROR: Multiple modules found! Check module info.')

        return module_output
                

     

    
    
    def get_temperature(self, channel_name=None, channel_number=None,
                        manual_conversion=False):    
        """
        """
        
        # get module
        module = self.get_module(channel_name=channel_name,
                                 channel_number=channel_number,
                                 module_type='MMR3')
        

        
        # get temperature (or resistance if manual conversion)
        param_name = 'X'
        if manual_conversion:
            param_name = 'R'
            
        result = module.get(param_name,
                            channel_name=channel_name,
                            channel_number=channel_number)
        
        
        # Manual conversion resistance to temperature
        if manual_conversion:
            print('WARNING: Conversion not implemented, returning resistance!')

        temperature = float(result)
        
        return temperature



    
    def get_resistance(self, channel_name=None, channel_number=None):    
        """
        """
        
        # get module
        module = self.get_module(channel_name=channel_name,
                                 channel_number=channel_number,
                                 module_type='MMR3')
        
        # get parameter
        result = module.get('R',
                            channel_name=channel_name,
                            channel_number=channel_number)
        
        resistance = float(result)
        
        return resistance
    
    
    

    
    
    def set_temperature(self, temperature,
                        channel_name=None, channel_number=None,
                        heater_channel_name=None, heater_channel_number=None):
        """
        Set temperature
        """
        
        # set PID
        self.set_PID(on=True,
                     channel_name=channel_name,
                     channel_number=channel_number,
                     heater_channel_name=heater_channel_name,
                     heater_channel_number=heater_channel_number)
        


        
        # get heater module
        heater_module = self.get_module(channel_name=heater_channel_name,
                                        channel_number=heater_channel_number,
                                        module_type='MGC3')
        
        
        # set temperature
        heater_module.set('setpoint', temperature,
                          channel_name=heater_channel_name,
                          channel_number=heater_channel_number)
        
    



        
    def set_PID(self, on=False, P=None, I=None, D=None,
                channel_name=None, channel_number=None,
                heater_channel_name=None, heater_channel_number=None):
        """
        Set PID 
        """

       
            
        # get heater module
        heater_module = self.get_module(channel_name=heater_channel_name,
                                        channel_number=heater_channel_number,
                                        module_type='MGC3')
        
        
        if P is not None:
            heater_module.set('P', P,
                              channel_name=heater_channel_name,
                              channel_number=heater_channel_number)
            
        if I is not None:
            heater_module.set('I', I,
                              channel_name=heater_channel_name,
                              channel_number=heater_channel_number)
            
        if D is not None:
            heater_module.set('D', D,
                              channel_name=heater_channel_name,
                              channel_number=heater_channel_number)

        


        # set thermometer channel
        if channel_name is not None or channel_number is not None:
            
            resistance_module = self.get_module(channel_name=channel_name,
                                                channel_number=channel_number,
                                                module_type='MMR3')
           
            channel_index = resistance_module.get_channel_index(channel_name=channel_name,
                                                                channel_number=channel_number)

            module_identity = resistance_module.identity

            heater_module.set('name', module_identity,
                              channel_name=heater_channel_name,
                              channel_number=heater_channel_number)

            heater_module.set('channel', channel_index,
                              channel_name=heater_channel_name,
                              channel_number=heater_channel_number)
            
