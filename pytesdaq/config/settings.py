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
        
        

    def get_sequencer_setup(self):
        """
        get sequencer setup

        """

        setup = dict()
        try:
            setup_configs = self._get_section('sequencer')
            for config in setup_configs:
                if len(config)!=2:
                    continue
                key = config[0]
                if config[1].strip() != '':
                    item = [s.strip() for s in config[1].split(',')]
                    if len(item)==1:
                        item = item[0]
                        if item =='true':
                            item = True
                        if item =='false':
                            item = False
                        
                    setup[key] = item
                                     
        except:
            pass

        return setup



    def get_iv_didv_setup(self):
        """
        Get IV / didv
        
        """
        iv_didv_config = dict()

        if self._has_section('iv'):
            config_section =  self._get_section('iv')
            setup_dict = dict()
            for config in config_section:
                if len(config)==2 and config[1].strip() != '':
                    setup_dict[config[0]] = config[1].strip()
            iv_didv_config['iv'] = setup_dict

        if self._has_section('didv'):
            config_section =  self._get_section('didv')
            setup_dict = dict()
            for config in config_section:
                if len(config)==2  and config[1].strip() != '':
                    setup_dict[config[0]] = config[1]
            iv_didv_config['didv'] = setup_dict
            iv_didv_config['rp'] = setup_dict.copy()
            iv_didv_config['rn'] = setup_dict.copy()
            
   
        if self._has_section('rp'):
            config_section =  self._get_section('rp')
            for config in config_section:
                if len(config) == 2 and config[1].strip() != '':
                    iv_didv_config['rp'][config[0]] = config[1]
   
        if self._has_section('rn'):
            config_section =  self._get_section('rn')
            for config in config_section:
                if len(config) == 2 and config[1].strip() != '':
                    iv_didv_config['rn'][config[0]] = config[1]
      
        return iv_didv_config

            

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




    def get_temperature_controller(self):
        """
        get temperature controller device name
            
        Returns:
            str - no type conversion happens here!
        """
        controller=str()
        try:
            controller =  self._get_setting('setup','temperature_controller')
        except:
            pass
        
        return controller




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

    
    def get_fig_data_path(self):
        data_path = './'
        try:
            data_path =  str(self._get_setting('setup','fig_data_path'))
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



    def get_shunt_resistance(self):
        """
        Read shunt resistance from setup.ini file
        """
        
        resistance = nan
        try:
            resistance =  float(self._get_setting('setup','shunt_resistance'))
        except:
            raise ValueError('ERROR: "shunt_resistance" parameter required!')
            
    
        return resistance



    def get_squid_turn_ratio(self):
        """
        Read SQUID Turn ratio from setup.ini file
        """
        
        squid_turn_ratio = nan

        try:
            squid_turn_ratio =  float(self._get_setting('setup','squid_turn_ratio'))
        except:
            raise ValueError('ERROR: "shunt_resistance" parameter required!')
         
         
    
        return squid_turn_ratio 



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



    def get_feedback_resistance(self):
        """
        Get feedback resistance
        Magnicon: variable feedback resistance can be read directly from electronics
        """

        resistance = nan
        if self._has_setting('setup','feedback_resistance'):
            resistance =  float(self._get_setting('setup','feedback_resistance'))
        return resistance
        


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
    
 
    def get_adc_setup(self,adc_id):
        """
        get ADC set
        
        Returns:
            pandas frame
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
             
            else:
                setup[item[0]] = item[1]       
                    

        connection_table = pd.DataFrame(adc_connections, columns = column_list)
        setup['connection_table'] = connection_table
        


        return setup

     
    def get_adc_connections(self, adc_id=''):
        """
        get ADC connections
            
        Returns:
           pandas frame
        """
   
        connection_table = []
        if adc_id:
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


    def get_signal_generator_address(self, device_name):
        """
        get function generators
        
        Returns:
            str - no type conversion happens here!
        """

        key = device_name + '_address'
        
        address=str()
        try:
            address =  self._get_setting('signal_generators',key)
        except:
            pass
    
        return address


    def get_temperature_controller_address(self, device_name):
        """
        get function generators
        
        Returns:
            str - no type conversion happens here!
        """

        key = device_name + '_address'
        
        address=str()
        try:
            address =  self._get_setting('temperature_controllers',key)
        except:
            pass
    
        return address
    

    
    def _get_ini_path(self,ini_filename):
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


    def _get_section(self,section):
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


    def _get_setting(self,section, name):
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


    
