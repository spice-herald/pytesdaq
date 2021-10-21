import time
from enum import Enum
from .macrtmodule import MACRTModule
from pytesdaq.instruments.communication import InstrumentComm
from pytesdaq.config import settings
import os
import stat
import pandas as pd

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
        
        
    @property
    def protocol(self):
        return self._protocol


    
    def setup_instrument_from_config(self, setup_file):
        """
        Setup modules from config
        """
        if setup_file is None or not os.path.isfile(setup_file):
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
                chan_list = list(range(1,4))
                if module_type == 'MGC3':
                    chan_list = list(range(0,3))
                
                for chan in chan_list:
                    item_name = module_name + '_chan' + str(chan)
                    if item_name in macrt_setup:
                        chan_dict = macrt_setup[item_name]
                        chan_name = None
                        if 'name' in chan_dict:
                            chan_name = chan_dict['name']
                        chan_number = None
                        if 'global_number' in chan_dict:
                            chan_number = chan_dict['global_number']
                        device_type = None
                        if 'type' in chan_dict:
                            device_type = chan_dict['type']
                        device_serial = None
                        if 'serial' in chan_dict:
                            device_serial = chan_dict['serial']
                            
                        self.set_module_channels(module_name=module_name,
                                                 channel_numbers=chan,
                                                 channel_names=chan_name,
                                                 global_channel_numbers=chan_number,
                                                 device_types=device_type,
                                                 device_serials=device_serial)
                    
        except:
            raise ValueError('ERROR: MACRT setup file has unknown format!')



        
    def add_module(self, module_type, module_name, module_ip, module_number=None,
                   channel_numbers=None, global_channel_numbers=None, channel_names=None,
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
        if channel_numbers is not None:
            module.add_channels(channel_numbers=channel_numbers, channel_names=channel_names,
                                global_channel_numbers=global_channel_numbers,
                                device_types=device_types, device_serials=device_serials,
                                replace=replace)
            
        # append to list
        self._module_list.append(module)
        


        
        
    def set_module_channels(self, module_name=None, module_number=None, module_ip=None,
                            channel_numbers=None, channel_names=None, global_channel_numbers=None,
                            device_types=None, device_serials=None, replace=False):
        
        """
        """

        # get module
        module = self.get_module(module_name=module_name, module_number=module_number,
                                 module_ip=module_ip)

        if module is not None:
            module.add_channels(channel_numbers=channel_numbers, channel_names=channel_names,
                                global_channel_numbers=global_channel_numbers,
                                device_types=device_types, device_serials=device_serials,
                                replace=replace)
    


            
        
    def scan_modules(self, broadcast_address):
        """
        """
        #response = self.scan('0 1', 8001, broadcast_address)
        print('NOT WORKING :-(')
        return


    
    
    

    def get_module(self, module_name=None, module_number=None, module_ip=None,
                   module_type=None, channel_name=None, global_channel_number=None,
                   raise_errors=True):
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
                or (channel_name is not None and channel_name in module.channel_names)
                or (global_channel_number is not None
                    and global_channel_number in module.global_channel_numbers)):

                # module type
                if (module_type is not None and module.type != module_type):
                    continue
                else:
                    module_output = module
                    nb_modules += 1
                    
                
        # display warning
        if nb_modules==0:
            if raise_errors:
                raise ValueError('ERROR: No module found!')
            else:
                module_output = None
        elif nb_modules>1:
            if raise_errors:
                raise ValueError('ERROR: Multiple modules found! Check module info.')
            else:
                print('WARNING: Multiple modules found! Returning None')
                module_output = None

                
        return module_output
                

     
    def get_channel_table(self, channel_type=None):
        """
        Get channel table
        """

        # loop modules and merge tables
       
        tables = list()
        for module in self._module_list:
            if (channel_type=='resistance'
                and module.type!='MMR3'):
                continue
            if (channel_type=='heater'
                and module.type!='MGC3'):
                continue
            
            tables.append(module.get_channel_table())


        channel_table = None
        if tables:
            channel_table = pd.concat(tables)

        return channel_table
            
                
                
    
    def get_temperature(self, channel_name=None, global_channel_number=None,
                        manual_conversion=False):    
        """
        """
        
        # get module
        module = self.get_module(channel_name=channel_name,
                                 global_channel_number=global_channel_number,
                                 module_type='MMR3')
        

        
        # get temperature (or resistance if manual conversion)
        param_name = 'X'
        if manual_conversion:
            param_name = 'R'
            
        result = module.get(param_name,
                            channel_name=channel_name,
                            global_channel_number=global_channel_number)
        
        
        # Manual conversion resistance to temperature
        if manual_conversion:
            print('WARNING: Conversion not implemented, returning resistance!')

        temperature = float(result)
        
        return temperature



    
    def get_resistance(self, channel_name=None, global_channel_number=None):    
        """
        """
        
        # get module
        module = self.get_module(channel_name=channel_name,
                                 global_channel_number=global_channel_number,
                                 module_type='MMR3')
        
        # get parameter
        result = module.get('R',
                            channel_name=channel_name,
                            global_channel_number=global_channel_number)
        
        resistance = float(result)
        
        return resistance
    
    
    

    
    
    def set_temperature(self, temperature,
                        channel_name=None,
                        global_channel_number=None,
                        heater_channel_name=None,
                        heater_global_channel_number=None,
                        wait_temperature_reached=False,
                        wait_cycle_time=30,
                        wait_stable_time=300,
                        max_wait_time=1200,
                        tolerance=0.2):
        """
        Set temperature
        """
        
        # set PID
        self.set_pid_control(on=True,
                     channel_name=channel_name,
                     global_channel_number=global_channel_number,
                     heater_channel_name=heater_channel_name,
                     heater_global_channel_number=heater_global_channel_number)
        


        
        # get heater module
        heater_module = self.get_module(channel_name=heater_channel_name,
                                        global_channel_number=heater_global_channel_number,
                                        module_type='MGC3')
        
        
        # set temperature
        heater_module.set('setpoint', temperature,
                          channel_name=heater_channel_name,
                          global_channel_number=heater_global_channel_number)
        
    


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
                temperature_now = self.get_temperature(channel_name=channel_name)
                # check tolerance
                if abs(temperature_now-temperature)/temperature_now > tolerance:
                    # reset stable time 
                    time_stable =  time_now

                if time_now-time_stable > wait_stable_time:
                    if self._verbose:
                        print('INFO: Temperature ' + str(temperature_now*1000) + 'mK reached!')
                    break
            
                # sleep...
                time.sleep(wait_cycle_time)

    def get_pid_control(self, heater_channel_name=None, heater_global_channel_number=None):
        """
        Get PID
        """

        # get heater module
        heater_module = self.get_module(channel_name=heater_channel_name,
                                        global_channel_number=heater_global_channel_number,
                                        module_type='MGC3')
        
        # Initialize ouput
        output = dict()
        if heater_channel_name is not None:
            output['heater_channel_name']  = heater_channel_name
        if heater_global_channel_number is not None:
            output['heater_global_channel_number'] = heater_global_channel_number 


        # check pid enables
        output['pid_enabled'] = bool(float(
            heater_module.get('onoff',
                              channel_name=heater_channel_name,
                              global_channel_number=heater_global_channel_number)
        ))
        
        
        output['P'] = float(
            heater_module.get('P',
                              channel_name=heater_channel_name,
                              global_channel_number=heater_global_channel_number)
        )
        
        output['I'] = float(
            heater_module.get('I',
                              channel_name=heater_channel_name,
                              global_channel_number=heater_global_channel_number)
        )
        
        output['D'] = float(
            heater_module.get('D',
                              channel_name=heater_channel_name,
                              global_channel_number=heater_global_channel_number)
        )
        
        
        output['input_channel_number'] = int(float(
            heater_module.get('channel',
                              channel_name=heater_channel_name,
                              global_channel_number=heater_global_channel_number)
        ))
        
        output['input_module'] = str(
            heater_module.get('name',
                              channel_name=heater_channel_name,
                              global_channel_number=heater_global_channel_number)
        )

        output['setpoint'] =  float(
            heater_module.get('setpoint',
                              channel_name=heater_channel_name,
                              global_channel_number=heater_global_channel_number)
        )
        


        return output

    

        
    def set_pid_control(self, on=None,
                        heater_channel_name=None, heater_global_channel_number=None,
                        P=None, I=None, D=None,
                        channel_name=None, global_channel_number=None):
        """
        Set PID 
        """

       
            
        # get heater module
        heater_module = self.get_module(channel_name=heater_channel_name,
                                        global_channel_number=heater_global_channel_number,
                                        module_type='MGC3')
        
        
        if P is not None:
            heater_module.set('P', P,
                              channel_name=heater_channel_name,
                              global_channel_number=heater_global_channel_number)
            
        if I is not None:
            heater_module.set('I', I,
                              channel_name=heater_channel_name,
                              global_channel_number=heater_global_channel_number)
            
        if D is not None:
            heater_module.set('D', D,
                              channel_name=heater_channel_name,
                              global_channel_number=heater_global_channel_number)

        


        # set thermometer channel
        if channel_name is not None or global_channel_number is not None:
            
            resistance_module = self.get_module(channel_name=channel_name,
                                                global_channel_number=global_channel_number,
                                                module_type='MMR3')
           
            channel_number = resistance_module.get_channel_number(channel_name=channel_name,
                                                                  global_channel_number=global_channel_number)

            # module identity
            module_identity = resistance_module.identity

            # set MMR3 module name
            heater_module.set('name', module_identity,
                              channel_name=heater_channel_name,
                              global_channel_number=heater_global_channel_number)

            # set channel number/index (Note: channel number from 0-2)
            channel_number -= 1
            heater_module.set('channel', channel_number,
                              channel_name=heater_channel_name,
                              global_channel_number=heater_global_channel_number)
            

        # on/off
        if on is not None and isinstance(on, bool):
            onoff = int(on)
            heater_module.set('onoff', onoff,
                              channel_name=heater_channel_name,
                              global_channel_number=heater_global_channel_number)
            

            

    def disconnect(self):
        """
        Disconnect 
        """

        # FIXME....

        if self._verbose:
            print('INFO: MACRT modules disconnected!')
        
        
