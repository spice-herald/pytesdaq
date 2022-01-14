import subprocess
import os
import time
from datetime import datetime
import fcntl

from nidaqmx.utils import flatten_channel_string
from pytesdaq.utils import arg_utils


class PolarisTask:
    
    def __init__(self):

        # initialize some parameters
        self._lock_daq=True
        self._lock_file = '/tmp/nidaq.lock'
        self._overwrite_config_allowed = True
        self._polaris_exe = 'polaris'
        self._config_file_name = '.nidaq.cfg'
        self._log_file = str()
        self._verbose = True
        self._quiet = False
              
        # data taking config
        # ADC/Run: unable to guess, need to be set by user
        self._adc_config = dict()
        self._required_adc_config = ['sample_rate', 'nb_samples', 'channel_list',
                                     'device_name', 'voltage_min','voltage_max',
                                     'trigger_type']
        self._run_config = dict()

        # Detector config: optional
        self._det_config = dict()

        # Polaris: let's initialize to the most likely setting
        self._polaris_config = dict()
        self._polaris_config['daq'] = {'lib':'./lib/libnidaq.so',
                                       'fcn':'NIdaq',
                                       'enable':'true',
                                       'next':'recorder'}
        
        self._polaris_config['recorder'] = {'lib':'./lib/libnidaq.so',
                                            'fcn':'HDF5Recorder',
                                            'enable':'true',
                                            'next':'daq'}
        
    @property
    def lock_daq(self):
        return self._lock_daq
        
    @lock_daq.setter
    def lock_daq(self,value):
        self._lock_daq=value
        
    @property
    def lock_file(self):
        return self._lock_file
        
    @lock_file.setter
    def lock_file(self,value):
        self._lock_file=value
    
    @property
    def log_file(self):
        return self._log_file
        
    @log_file.setter
    def log_file(self,value):
        self._log_file=value

      
    @property
    def verbose(self):
        return self._verbose
        
    @verbose.setter
    def verbose(self,value):
        self._verbose=value
 
    @property
    def quiet(self):
        return self._quiet
        
    @quiet.setter
    def quiet(self,value):
        self._quiet=value
        
  
    @property
    def overwrite_config_allowed(self):
        return self._overwrite_config_allowed
        
    @overwrite_config_allowed.setter
    def overwrite_config_allowed(self,value):
        self._overwrite_config_allowed=value
         
    @property
    def polaris_exe(self):
        return self._polaris_exe
        
    @overwrite_config_allowed.setter
    def polaris_exe(self,value):
        self._polaris_exe=value
       
    @property
    def config_file_name(self):
        return self._config_file_name
        
    @config_file_name.setter
    def config_file_name(self,value):
        self._config_file_name=value
       

    
    def set_polaris_config(self, config_dict):
        """
        Set Polaris configuration
        """
       
        # replace keys in self._polaris_config with
        # config_dict

        for item in self._polaris_config:
            if item in config_dict:
                for key, val in self._polaris_config[item].items():
                    if key in config_dict[item]:
                        self._polaris_config[item][key] = config_dict[item][key]
                        
                        


    def set_detector_config(self, config_dict):
        """
        Set detector configuration
        """
        self._det_config = config_dict
        

    def set_run_config(self, config_dict):
        """
        Set Run configuration
        """
        self._run_config = config_dict
        



    def set_adc_config_from_dict(self, config_dict):
        """
        Set ADC configuration
        """
        self._adc_config = config_dict
       
        

    def get_required_adc_config(self):
        return self._required_adc_config


    def set_adc_config(self,adc_name, device_name=str(), sample_rate=[], nb_samples=[],
                       voltage_min=list(), voltage_max=list(), channel_list=list(), 
                       trigger_type = [],buffer_length=[]):
        
        """
        Set ADC config
        """
     
   
        adc_dict = dict()
        if not self._adc_config:
            self._adc_config = dict()
        elif adc_name in self._adc_config:
            adc_dict = self._adc_config[adc_name]
            
            
        if device_name:
            adc_dict['device_name'] = device_name

        if sample_rate:
            adc_dict['sample_rate'] = int(sample_rate)
            
        if nb_samples:
            adc_dict['nb_samples'] = int(nb_samples)
            
        if channel_list:
            adc_dict['channel_list'] = channel_list
            
        if voltage_min:
            adc_dict['voltage_min'] = float(voltage_min)
    
        if voltage_max:
            adc_dict['voltage_max'] = float(voltage_max)
    
        if trigger_type:
            adc_dict['trigger_type'] = int(trigger_type)
            
        
        self._adc_config[adc_name] = adc_dict


    def clear(self):
        return

    def run(self, run_time=60, run_comment=str(), write_config=True, debug=False):
        
        """
        Run Polaris
        """

        # write configuration file
        if write_config:
            success = self._write_config_file()
            if not success:
                print("ERROR from polaris::run: Unable to write configuration file!")
                return False
 

        # check if ongoing process
        
        if self._lock_daq and self._lock_file:
            if self._is_locked():
                return False
                
        # build system commend
        
        polaris_cmd = self._polaris_exe + ' --cfg ' + self._config_file_name + ' --time ' + str(run_time)
        if self._verbose:
            polaris_cmd = polaris_cmd + ' --verbose'
        if self._quiet:
            polaris_cmd = polaris_cmd + ' --quiet'
        if debug:
            polaris_cmd = polaris_cmd + ' --debug'
        if self._log_file:
             polaris_cmd = polaris_cmd + ' --log ' + self._log_file

             
       
        print('INFO: Polaris command: ' + polaris_cmd)
        print('INFO: Starting data taking using polaris!')
        
               
        # lock
        if self._lock_daq and self._lock_file:
            polaris_cmd = 'flock -n ' + self._lock_file + ' -c '+ '\''+ polaris_cmd +'\''

      
   
        start = datetime.now()
        env = os.environ.copy() # specific environment for polaris?
  
     
        with subprocess.Popen(polaris_cmd,shell=True,stdout=subprocess.PIPE, 
                              stderr=subprocess.STDOUT,env=env) as running_task:
     
            while running_task.poll() == None:

                if self._verbose:
                    output = running_task.stdout.readline()
                    if output:
                        print(output.strip().decode('utf-8'))
                time.sleep(0.1)
                        

            if running_task.returncode !=0:
                print('ERROR: polaris data taking ended with an error!')
                return False


        end = datetime.now()
        duration_secs = (end - start).total_seconds()
        duration_secs = max(duration_secs, 1)

        print('INFO: Data taking successfully done in ' + str(duration_secs) + ' seconds')
        

        return True



    def _is_locked(self):
        f_lock = open(self._lock_file,'w+')
        try:
            fcntl.flock(f_lock,fcntl.LOCK_EX | fcntl.LOCK_NB)
        except:
            f_lock.close()
            print('\nWARNING from polaris::is_locked: Ongoing data taking... Stop data taking before starting a new run!\n')
            return True
        else:
            fcntl.flock(f_lock,fcntl.LOCK_UN)
        f_lock.close() 
        return False



    def _write_config_file(self):
        """
        Write config file - Assume configuration have been set already
        """
        
        # check mandatory config
        if not self._polaris_config:
            print('ERROR: Polaris configuration not available! Unable to start run')
            return False

        if not self._adc_config:   
            print('ERROR: ADC configuration not available! Unable to start run')
            return False

        if not self._run_config: 
            print('ERROR: Run configuration not available! Unable to start run')
            return False



        # initialize list
        cfg_list = list()

        
        # date
        now = datetime.now()
        dt_string = now.strftime('%d/%m/%Y %H:%M:%S')
        cfg_list.append('# Configuration file production date: ' +  dt_string + '\n\n')

       
        # polaris module
        cfg_list.append('\nmodule {\n')
        for module_key in self._polaris_config:
            cfg_list.append('\t' + module_key + ' {\n')
            config_dict = self._polaris_config[module_key]
            for key in config_dict:
                cfg_list.append('\t\t' + key + ' : ' + str(config_dict[key]) + ',\n')
            cfg_list.append('\t}\n')
        cfg_list.append('}\n\n')

        # run config
        for key in self._run_config:
            cfg_list.append(key + ' : ' + str(self._run_config[key]) + ',\n')
                        
        
        # adc config
        for adc_name in self._adc_config:

            cfg_list.append('\n' + adc_name + ' {\n')
            config_dict = self._adc_config[adc_name]
            
            # check parameter
            for param in self._required_adc_config:
                if param not in config_dict:
                    print('ERROR from polaris::write_config:  Missing ADC configuration "' + param + '"!')
                    return False
            
            # sample rate, nb samples
            cfg_list.append('\tsample_rate : ' + str(config_dict['sample_rate']) + ',\n')
            cfg_list.append('\tnb_samples : ' + str(config_dict['nb_samples']) + ',\n')

            # channel list
            channel_list = config_dict['channel_list']
            if isinstance(channel_list,str):
                channel_list =  arg_utils.hyphen_range(config_dict['channel_list'])
            channel_names = list()
            for chan in channel_list:
                channel_names.append(config_dict['device_name'] + '/ai' + str(chan))
            channel_names_flatten = flatten_channel_string(channel_names)
            cfg_list.append('\tchannel : ' + channel_names_flatten + ',\n')

            # voltage range
            nb_channels = len(channel_list)
            voltage_min_list =list()
            if (isinstance(config_dict['voltage_min'], list) and 
                len(config_dict['voltage_min'])==nb_channels):
                voltage_min_list = config_dict['voltage_min']
            else:
                for ii in range(nb_channels):
                    voltage_min_list.append(config_dict['voltage_min'])
            Vmin = ' '.join(map(str,voltage_min_list))
            cfg_list.append('\tVmin : ' + Vmin + ',\n')

            voltage_max_list =list()
            if (isinstance(config_dict['voltage_max'], list) and 
                len(config_dict['voltage_max'])==nb_channels):
                voltage_max_list = config_dict['voltage_max']
            else:
                for ii in range(nb_channels):
                    voltage_max_list.append(config_dict['voltage_max'])
            Vmax = ' '.join(map(str,voltage_max_list))
            cfg_list.append('\tVmax : ' + Vmax + ',\n')

                               
            # connection
            for config in config_dict:
                if 'connection' in config and 'connection_table'!= config:
                    val = ' '.join(map(str,config_dict[config]))
                    cfg_list.append('\t' + config + ' : ' + val + ',\n')


            data_mode = 'cont'
            if int(config_dict['trigger_type'])==2:
                data_mode = 'trig-ext'
            
            cfg_list.append('\tdata_mode : ' + data_mode + ',\n')

            if data_mode == 'trig-ext':
                trigger_channel = '/Dev1/pfi0'
                if 'trigger_channel' in config_dict:
                    trigger_channel = config_dict['trigger_channel']
                cfg_list.append('\ttrig_channel : ' + trigger_channel + ',\n')

            # close section
            cfg_list.append('}\n')
               

         
        # detector config
        if self._det_config:
            for adc_key in self._det_config:
                device_key = adc_key
                if adc_key[0:3] == 'adc':
                    device_key = 'detconfig' + str(adc_key[3:])
                cfg_list.append('\n'+device_key + ' {\n')
                config_dict = self._det_config[adc_key]
                for key,val_list in config_dict.items():
                    if not isinstance(val_list, list):
                        val_list = [val_list]
                    val_str = ' '.join(map(str,val_list))
                    cfg_list.append('\t' + key + ' : ' + val_str + ',\n')
                cfg_list.append('}\n')

                        

        # write file
        print('INFO: Writing new polaris configuration file "' + self._config_file_name + '"!')
                  
        
        cfg_str = ''.join(cfg_list)
        cfg_file= open(self._config_file_name,'w+')
        cfg_file.write(cfg_str)
        cfg_file.close()
        return True
