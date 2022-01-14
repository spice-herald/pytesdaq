import configparser
from io import StringIO
import os,string
import pandas as pd
import re
import traceback
from pytesdaq.utils import connection_utils
from math import nan
import os
import sys

class Config:
    
    def __init__(self, setup_file=None, sequencer_file=None, verbose=False):
        
    
        # config files
        self._setup_file = setup_file
        self._sequencer_file = sequencer_file

        if setup_file is None or not setup_file:
            self._setup_file = self._get_ini_path('setup.ini')
        if sequencer_file is None or not sequencer_file:
            self._sequencer_file = self._get_ini_path('sequencer.ini')
            

        if not os.path.isfile(self._setup_file):
            raise ValueError('Setup file "' + self._setup_file + '" not found!')
        elif verbose:
            print('INFO: Reading setup file ' + self._setup_file)

        self._cached_config = configparser.RawConfigParser()
        self._cached_config.read([self._setup_file, self._sequencer_file])
                
        

    @property
    def setup_file(self):
        return self._setup_file
        
    @setup_file.setter
    def setup_file(self,value):
        self._setup_file=value
        self.reload_config()
        
    @property
    def sequencer_file(self):
        return self._sequencer_file
        
    @sequencer_file.setter
    def sequencer_file(self,value):
        self._sequencer_file=value
        self.reload_config()
        



    def reload_config(self):
        self._cached_config = None
        self._cached_config = configparser.RawConfigParser()
        self._cached_config.read([self._setup_file, self._sequencer_file])


        
    def get_processing_setup(self):
        """
        Get sequencer processing setup
        """
       
        return self._get_section_dict('processing')
                  
        

    def get_sequencer_setup(self, measurement_name, measurement_list=None):
        """
        get sequencer setup

        """

        output_setup = dict()

        # measurement list
        if measurement_list is None:
            measurement_list = [measurement_name]
            
        try:

            # convert to dictionary
            config_dict = dict()
            setup_config = self._get_section(measurement_name)
            for config in setup_config:
                if len(config)!=2:
                    continue
                if config[1].strip() == '':
                    continue
                key = config[0]
                values = [s.strip() for s in config[1].split(',')]
                if len(values)==1:
                    values = values[0]
                    if values =='true' or values =='True':
                        values = True
                    elif values =='false' or values =='False':
                        values = False
                    elif values.isdigit():
                        values = float(values)
                elif len(values)>1:
                    for ival in range(len(values)):
                        if values[ival].isdigit():
                            values[ival] = float(values[ival])
                        
                config_dict[key] = values
          

                        
            # case "iv_didv": get other individual sections
            if measurement_name == 'iv_didv':
                output_setup['iv_didv'] = config_dict.copy()
                for name in measurement_list:
                    # copy setup and update with individual setup
                    output_setup[name] = config_dict.copy()
                
                    if self._has_section(name):
                        iv_didv_config =  self._get_section(name)
                        for config in iv_didv_config:
                            if len(config)!=2:
                                continue
                            if config[1].strip() == '':
                                continue
                            key = config[0]
                            values = [s.strip() for s in config[1].split(',')]
                            if len(values)==1:
                                values = values[0]
                                if values =='true' or values =='True':
                                    values = True
                                elif values =='false' or values =='False':
                                    values = False
                                elif values.isdigit():
                                    values = float(values)
                            elif len(values)>1:
                                for ival in range(len(values)):
                                    if values[ival].isdigit():
                                        values[ival] = float(values[ival])
                            output_setup[name][key] = values
            else:
                output_setup[measurement_name] = config_dict
                          
        except:
            print('WARNING: Problem reading settings file for "'+
                  measurement_name + '" measurement!')

        return output_setup 


  
    def get_squid_controller(self):
        """
        get SQUID/TES controller device name
        
        Returns:
           str - no type conversion happens here!
        """
        controller=str()
        try:
            controller =  self._get_setting('setup','squid_controller')
        except:
            pass
    
        return controller




    def get_temperature_controllers(self):
        """
        get temperature controller device names
        (comma separated)
            
        Returns:
            list of strings - no type conversion happens here!
        """
        controllers=list()
        
        try:
            controllers =  self._get_comma_separated_setting('setup','temperature_controllers')
        except:
            pass
        
        return controllers




    def get_signal_generator(self):
        """
        get signal generator device name
            
        Returns:
             str - no type conversion happens here!
        """
        controller=str()
        try:
            controller = self._get_setting('setup','signal_generator')
        except:
            pass
    
        return controller



    def enable_redis(self):
        """
        Enable redis
            
        Returns:
             bool
        """
        try:
            return self._get_boolean_setting('setup','enable_redis')
        except:
            return False
    


    def enable_readback(self):
        """
        Enable readback
            
        Returns:
            bool
        """
        try:
            return self._get_boolean_setting('setup','enable_readback')
        except:
            return False
   


    def get_facility_num(self):
        facility = []
        try:
            facility =  int(self._get_setting('setup','facility'))
        except:
            pass
    
        return facility

    def get_data_path(self):
        data_path = './'
        try:
            data_path =  str(self._get_setting('setup','data_path'))
        except:
            pass
        
        return data_path


    def get_fridge_run(self):
        fridge_run = []
        try:
            fridge_run =  int(self._get_setting('setup','fridge_run'))
        except:
            pass
    
        return fridge_run



    def get_preamp_fix_gain(self, controller_name=None):
        """
        Get SQUID readout preamp fix gain
        """

        # default
        preamp_fix_gain = 1
        
        if controller_name is None:
            controller_name = self.get_squid_controller()


        if self._has_setting(controller_name,'preamp_fix_gain') and controller_name is not None:
            preamp_fix_gain =  float(self._get_setting(controller_name,'preamp_fix_gain'))
            
            
        return preamp_fix_gain


    
    
    def get_feedback_fix_gain(self, controller_name=None):
        """
        Get SQUID readout feedback fix gain
        """

        # default
        feedback_fix_gain = 1
        
        if controller_name is None:
            controller_name = self.get_squid_controller()


        if self._has_setting(controller_name,'feedback_fix_gain') and controller_name is not None:
            feedback_fix_gain =  float(self._get_setting(controller_name,'feedback_fix_gain'))
            
            
        return feedback_fix_gain




    
    def get_output_fix_gain(self, controller_name=None):
        """
        Get SQUID readout output driver fix gain
        """
        output_fix_gain = 1

        if controller_name is None:
            controller_name = self.get_squid_controller()

        
        if self._has_setting(controller_name,'output_fix_gain') and controller_name is not None:
            output_fix_gain =  float(self._get_setting(controller_name,'output_fix_gain'))
            
        return output_fix_gain


    

    def get_signal_gen_tes_resistance(self, controller_name=None):
        """
        Get SQUID readout output driver fix gain
        """
        resistance = nan

        if controller_name is None:
            controller_name = self.get_squid_controller()

        
        if self._has_setting(controller_name,'signal_gen_tes_resistance') and controller_name is not None:
            resistance  =  float(self._get_setting(controller_name,'signal_gen_tes_resistance'))
            
        return resistance


    
    def get_adc_list(self):
        adc_list = list()
        try:
            adc_list =  self._get_comma_separated_setting('setup','enable_adc')
        except:
            pass
        
        return adc_list
    
 
    def get_adc_setup(self, adc_id):
        """
        get ADC set
        
        Returns:
            dictionary with adc setup
        """

        setup = dict()

        # get items
        item_list = self._get_section(adc_id)
        adc_connections = list()
        column_list = list()
        for item in item_list:

            if 'voltage_range' == item[0]:
                voltage_range = [int(voltage.strip()) for voltage in item[1].split(',')]
                if len(voltage_range) == 2:
                    voltage_range = (voltage_range[0],voltage_range[1])
                    setup['voltage_range'] = voltage_range

            elif ('sample_rate' == item[0] or 'nb_samples'== item[0] or 
                  'trigger_type'== item[0]):
                setup[item[0]] = int(item[1])

            elif 'connection' in item[0] and 'connection_table'!=item[0]:
                adc_chan = re.sub(r'\s+','', str(item[0]))[10:]
                name_val_list, name_list, val_list  = connection_utils.extract_adc_connection(item[1])
                setup[item[0]] = name_val_list
                val_list  = [adc_id,adc_chan] + val_list
                adc_connections.append(val_list)
                column_list = ['adc_id','adc_channel'] + name_list

            elif 'detector_config' in item[0]:
                continue
            else:
                setup[item[0]] = item[1]       
                    

        connection_table = pd.DataFrame(adc_connections, columns = column_list)
        setup['connection_table'] = connection_table
        


        return setup

     
    def get_adc_connections(self, adc_id=None):
        """
        get ADC connections
            
        Returns:
           pandas frame
        """
   
        connection_table = []
        if adc_id is not None:
            adc_setup = self.get_adc_setup(adc_id)
            if 'connection_table' in adc_setup:
                connection_table = adc_setup['connection_table']
        else:
            adc_list = self.get_adc_list()
            connection_table_list = []
            for adc in adc_list:
                adc_setup = self.get_adc_setup(adc)
                if 'connection_table' in adc_setup:
                    connection_table_list.append(adc_setup['connection_table'])
            if connection_table_list:
                connection_table = pd.concat(connection_table_list)
            
        return connection_table 


    
    def get_detector_config(self, adc_id=None, adc_channel_list=None):
        """
        get detector config from setup.ini file 
            
        Returns:
           dictionary with config
        """


        # check arguments
        if  adc_id is None or adc_channel_list is None:
            raise ValueError('ERROR in get_detector_config: "adc_id" and "adc_channel_list" required!')

        adc_list = self.get_adc_list()
        if adc_id not in adc_list:
            raise ValueError('ERROR in get_detector_config: No information in setup file for "'
                             + str(acd_id) + '"!')





        
        # intialize
        param_list = ['tes_bias','squid_bias','lock_point_voltage','output_offset',
                      'output_gain','preamp_gain','feedback_polarity','feedback_mode',
                      'signal_source','signal_gen_current','signal_gen_frequency',
                      'squid_turn_ratio','shunt_resistance', 'feedback_resistance',
                      'signal_gen_tes_resistance','close_loop_norm']
        
        detector_config = dict()
        for param in param_list:
            detector_config[param] = list()
            

        # store channel lost
        detector_config['adc_name'] = adc_id
        detector_config['channel_type'] = 'adc'
        detector_config['channel_list'] = adc_channel_list


            
        # loop channel list
        for adc_chan in adc_channel_list:
            item = 'detector_config' + str(adc_chan)
            if not self._has_setting(adc_id, item):
                raise ValueError('ERROR in get_detector_config: No detector settings found for channel '
                                 + str(adc_chan) + '!')

            settings = self._get_comma_separated_setting(adc_id, item)
            for param in settings:
                param_split = param.split(':')
                param_name = param_split[0]
                param_val = float(param_split[1])

                # some conversion needed
                if param_name=='tes_bias' or param_name=='squid_bias' or param_name=='signal_gen_current':
                    param_val = param_val/1000000.0
                if param_name=='lock_point_voltage':
                    param_val = param_val/1000.0

                # add in config
                detector_config[param_name].append(param_val)

                       
        return detector_config 

    def get_visa_library(self):
        """
        get VISA Library
        
        Returns:
            str - no type conversion happens here!
        """
        library_path = None
        try:
            if self._has_setting('setup','visa_library'):
                library_path =  self._get_setting('setup','visa_library')
        except:
            pass
    
        return library_path

    
    def get_feb_address(self):
        """
        get FEB GPIB address
        
        Returns:
            str - no type conversion happens here!
        """
        address=str()
        try:
            address =  self._get_setting('feb','visa_address')
        except:
            pass
    
        return address


    def get_feb_subrack_slot(self,feb_id='feb1'):
        """
        get subrack/slot in a list
    
        Returns:
           list -str
        """
    
        feb_info = list()
        try:
            feb_info = self._get_comma_separated_setting('feb', feb_id)
        except:
            pass

        return feb_info 

    def get_polaris_info(self):
        """
        Get Polaris info from setup.ini file
        """
        
        info = dict()
        if self._has_section('polaris_daq'):
            info['daq'] = dict()
            item_list = self._get_section('polaris_daq')
            for item in  item_list:
                info['daq'][str(item[0])] = str(item[1]).strip()
               
        if self._has_section('polaris_recorder'):
            info['recorder'] = dict()
            item_list = self._get_section('polaris_recorder')
            for item in  item_list:
                info['recorder'][str(item[0])] = str(item[1]).strip()
               
        return info

            


    def get_redis_info(self):
        """
        Get redis DB info from setup.ini file
        """

        info = dict()
        try:
            info['host'] = self._get_setting('redis','host')
            info['port'] = int(self._get_setting('redis','port'))
            info['password'] = self._get_setting('redis','password')
            if info['password']=='None':
                info['password']=''
            info['data_stream'] =  self._get_setting('redis','data_stream')   
        except:
            print('ERROR: Missing redis parameter in config file!')
            print('Required: host, port, password, data_stream')

        return info



    def get_magnicon_connection_info(self):
        """
        Returns a dictionary with the magnicon SSH connection info
        """
        info = {}

        try:
            info['hostname'] = self._get_setting('magnicon', 'hostname')
            info['username'] = self._get_setting('magnicon', 'username')
            info['port'] = int(self._get_setting('magnicon', 'port'))
            info['rsa_key'] = self._get_setting('magnicon', 'rsa_key')
            info['log_file'] = self._get_setting('magnicon', 'log_file')
            info['exe_location'] = self._get_setting('magnicon', 'exe_location')
        except:
            print('ERROR: Could not get complete connection info for Magnicon')

        return info



    def get_magnicon_controller_info(self):
        """
        Returns a dictionary with the magnicon controller info
        """
        info = {}

        try:
            info['channel_list'] = [int(x) for x in self._get_setting('magnicon', 'channel_list').split(',')]
            info['default_active'] = int(self._get_setting('magnicon', 'default_active'))
            info['reset_active'] = int(self._get_setting('magnicon', 'reset_active'))
        except Exception as e:
            print('ERROR: Could not get complete controller info for Magnicon')
            print(str(e))
            traceback.print_exc()

        return info


    def get_signal_generator_visa_address(self, device_name):
        """
        get function generators
        
        Returns:
            str - no type conversion happens here!
        """

        key = device_name + '_visa_address'
        
        address=str()
        try:
            address =  self._get_setting('signal_generators',key)
        except:
            pass
    
        return address


    def get_temperature_controller_setup(self, device_name):
        """
        get function generators
    
        Args:
            devic_name = "lakeshore" or "macrt"

        Returns:
            str - no type conversion happens here!
        """

        # get all items in sectiob
        items = None

        try:
            items = self._get_section('temperature_controllers')
        except:
            return items


        # initialize dictionary
        output_dict = dict()

        try:
            
            for item in items:
            
                # extract device name
                device = item[0][0:item[0].find('_')]
                device = device.strip()
                device_param = item[0][item[0].find('_')+1:]
                device_param = device_param.strip()

                # check if selected device
                if device  != device_name:
                    continue
                output_dict[device_param] = dict()

                # get parameters
                params = item[1].split(',')
                for param in params:
                    param_name = str(param.split(':')[0]).strip()
                    param_val = str(param.split(':')[1]).strip()
                    output_dict[device_param][param_name] = param_val
            
        except:
            raise ValueError('ERROR: Unknown temperature_controllers format!')
                
        
        return output_dict
    

    
    def _get_ini_path(self, ini_filename):
        """
        Get the path where the ini files live. ini files
        should be placed in the same directory as the settings.py module.
    
        Args:
    
        * ini_filename (str)
        
        Returns:
             str, full path to that file.
        """

        this_dir = os.path.dirname(os.path.realpath(__file__))
        return os.path.abspath(os.path.join(this_dir, ini_filename))


    def _get_section(self, section):
        """
        Get all items from section
        
        Args:
        
        * section (str)
           
        Returns:
             
        """
        return self._cached_config.items(section) 



    def _has_section(self,section):
        """
        check is section exist
        
        Args:
        
        * section (str)
        
        Returns:
           bool
        """
        
        has_section = False
        try:
            has_section = self._cached_config.has_section(section)
        except:
            pass
    
        return has_section


    def _get_setting(self, section, name):
        """
        Get a particular setting from setup.ini. 
        
        Args:
    
        * section (str)
        * name (str)
        
        Returns:
             str - no type conversion happens here!
        """
        return self._cached_config.get(section, name) 


    

    def _has_setting(self, section, name):
        """
        check is setting exist
        
        Args:
        
        * section (str)
        * name (str)
        
        Returns:
           bool
        """
        
        has_option = False
        try:
            has_option = self._cached_config.has_option(section, name)
        except:
            pass
    
        return has_option


    def _get_boolean_setting(self, section, name):
        """
        Get a particular setting from setup.ini. 
        
        Args:
        
        * section (str)
        * name (str)
        
        Returns:
            str - no type conversion happens here!
        """
        return self._cached_config.getboolean(section, name) 

    
    def _get_comma_separated_setting(self, section, name):
        """
        Get comma-separated list from setup.ini
     
        Args:
    
        * section (str)
        * name (str)
        
        Returns:
             list of str (possibly empty)
        """
        setting_str = str()
    
        try:
            setting_str = self._get_setting(section, name)
        except:
            pass
    
        if setting_str.strip() == '':
            return []
    
        return [s.strip() for s in setting_str.split(',')]


    
    def _get_section_dict(self, section):
        """
        Get section and store 
        in dictionary
        """
        output_dict = dict()

        
        try:
            section_config = self._get_section(section)
            for config in section_config:
                if len(config)!=2:
                    continue
                if config[1].strip() == '':
                    continue
                key = config[0]
                values = [s.strip() for s in config[1].split(',')]
                if len(values)==1:
                    values = values[0]
                    if values =='true' or values =='True':
                        values = True
                    elif values =='false' or values =='False':
                        values = False
                    elif values.isdigit():
                        values = float(values)
                elif len(values)>1:
                    for ival in range(len(values)):
                        if values[ival].isdigit():
                            values[ival] = float(values[ival])
                        
                output_dict[key] = values

        except:
            return None

        return output_dict
