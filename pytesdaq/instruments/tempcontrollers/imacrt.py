import time
from enum import Enum
from .macrtmodule import MACRTModule
from pytesdaq.instruments.communication import InstrumentComm



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
        
        


    def setup_modules_from_config(setup_file=None):
        """
        Setup modules from config
        """
        pass
        
        
    def add_module(self, module_type, module_name, module_ip, module_num=None,
                   channel_nums=None, global_channel_nums=None, channel_names=None,
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
        module = MACRTModule(module_type, module_name, module_ip, module_num,
                             protocol=self._protocol, verbose=self._verbose)
        

        # add channels
        if channel_nums is not None:
            module.add_channels(channel_nums=channel_nums, channel_names=channel_names,
                                global_channel_nums=global_channel_nums,
                                device_types=device_types, device_serials=device_serials,
                                replace=replace)
            
        # append to list
        self._module_list.append(module)
        


        
        
    def add_module_channels(self, module_name=None, module_num=None, module_ip=None,
                            channel_nums=None, channel_names=None, global_channel_nums=None,
                            device_types=None, device_serials=None, replace=False):
        
        """
        """

        # get module
        module = self.get_module(module_name=module_name, module_num=module_num,
                                 module_ip=module_ip)

        if module is not None:
            module.add_channels(channel_nums=channel_nums, channel_names=channel_names,
                                global_channel_nums=global_channel_nums,
                                device_types=device_types, device_serials=device_serials,
                                replace=replace)
    


            
        
    def scan_modules(self, broadcast_address):
        """
        """
        #response = self.scan('0 1', 8001, broadcast_address)
        print('NOT WORKING :-(')
        return

            

    def get_module(self, module_name=None, module_num=None, module_ip=None,
                   channel_name=None, global_channel_num=None):
        """
        """
        
        module_output = None

        # check if module list exist
        if self._module_list is None:
            print('WARNING: No modules available!')
            return None
  
        # loop modules
        nb_modules = 0
        for module in self._module_list:
            if ((module_name is not None and module.name == module_name)  
                or (module_num is not None and module.num == module_num)
                or (module_ip is not None  and module.ip_address==module_ip)
                or (channel_name is not None and channel_name in module.channel_names)
                or (global_channel_num is not None
                    and global_channel_num in module.global_channel_nums)):
                module_output = module
                nb_modules += 1

                
        # display warning
        if nb_modules==0:
            raise ValueError('ERROR: No module found!')
        elif nb_modules>1:
            raise ValueError('ERROR: Multiple modules found! Check module info.')

        return module_output
                

     

    
    
    def get_temperature(self, channel_name=None, global_channel_num=None,
                        manual_conversion=False):    
        """
        """
        
        # get module
        module = self.get_module(channel_name=channel_name,
                                 global_channel_num=global_channel_num)


        
        # get temperature (or resistance if manual conversion)
        param_name = 'X'
        if manual_conversion:
            param_name = 'R'
            
        result = module.get(param_name,
                            channel_name=channel_name,
                            global_channel_num=global_channel_num)
        
        
        # Manual conversion resistance to temperature
        if manual_conversion:
            print('WARNING: Conversion not implemented, returning resistance!')

        temperature = float(result)
        
        return temperature



    
    
    def set_temperature(self, temperature,
                        channel_name=None, global_channel_num=None,
                        heater_channel_name=None, heater_global_channel_num=None):
        """
        Set temperature
        """
        
        
        # get heater module
        heater_module = self.get_module(channel_name=heater_channel_name,
                                        global_channel_num=heater_global_channel_num)
        
        
        # set temperature
        heater_module.set('setpoint', temperature,
                          channel_name=heater_channel_name,
                          global_channel_num=heater_global_channel_num)
        
            



        
    def set_PID(self, on=False, P=None, I=None, D=None,
                channel_name=None, global_channel_num=None,
                heater_channel_name=None, heater_global_channel_num=None):
        """
        Set PID 
        """

       
            
        # get heater module
        heater_module = self.get_module(channel_name=heater_channel_name,
                                        global_channel_num=heater_global_channel_num)
        

        if P is not None:
            heater_module.set('P', P,
                              channel_name=heater_channel_name,
                              global_channel_num=heater_global_channel_num)
            
        if I is not None:
            heater_module.set('I', I,
                              channel_name=heater_channel_name,
                              global_channel_num=heater_global_channel_num)
            
        if D is not None:
            heater_module.set('D', D,
                              channel_name=heater_channel_name,
                              global_channel_num=heater_global_channel_num)

        


        # set thermometer channel
        if channel_name is not None or global_channel_num is not None:
            thermometer_module = self.get_module(channel_name=channel_name,
                                                 global_channel_num=global_channel_num)
            module_idn = thermometer_module.idn
            channel_num = thermometer_module.get_channel_num(channel_name=channel_name,
                                                             global_channel_num=global_channel_num)

            heater_module.set('name', module_idn,
                              channel_name=heater_channel_name,
                              global_channel_num=heater_global_channel_num)

            heater_module.set('channel', channel_num,
                              channel_name=heater_channel_name,
                              global_channel_num=heater_global_channel_num)
            
