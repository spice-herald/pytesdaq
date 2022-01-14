import numpy as np
import time
import struct

from pytesdaq.config import settings
from pytesdaq.daq import polaris
from pytesdaq.daq import nidaqtask


class DAQ:

    
    def __init__(self, driver_name='polaris', verbose=True, setup_file=None):
        
        
        # initialize
        self._verbose = verbose
        self._driver_name = driver_name
        self._driver = None
           
      
        # run purpose dict 
        self._run_purpose_dict = {1:'Test', 2:'LowBg', 3:'Calibration', 4:'Noise',
                                  100:'Rp',101:'Rn',102: 'IV', 103:'dIdV'}
        
      
        # Configuration
        self._config = settings.Config(setup_file=setup_file)
      

        # instantiate driver 
        self._instantiate_driver()

      
        
          
            
    @property
    def driver_name(self):
        return self._driver_name
        

    @driver_name.setter
    def driver_name(self,value):
        if self._driver_name==value:
            print('WARNING: Driver already set to "' 
                  + value + '"!')
            return
        else:
            self._driver_name=value
            self._instantiate_driver()  
            
        
    @property
    def lock_daq(self):
        return self._driver.lock_daq
        
    @lock_daq.setter
    def lock_daq(self,value):
        self._driver.lock_daq = value
        
    @property
    def lock_file(self):
        return self._driver.lock_file
        
    @lock_file.setter
    def lock_file(self,value):
        self._driver.lock_file=value
    
    @property
    def log_file(self):
        return self._driver.log_file
        
    @log_file.setter
    def log_file(self,value):
        self._driver.log_file=value

  

   
    def _instantiate_driver(self):
         
        if self._driver is not None:
            self._driver.clear()
            self._driver = None
            
        if self._driver_name=='polaris':
            self._driver = polaris.PolarisTask()
            self._driver.overwrite_config_allowed = True
            self._driver.polaris_exe = 'polaris'
            self._driver.config_file_name = '.nidaq.cfg'

        elif self._driver_name=='pydaqmx':
            self._driver = nidaqtask.NITask()
          
        self._driver.verbose = self._verbose
        self._driver.quiet = False
        self._driver.lock_daq=False
        self._driver.lock_file = '/tmp/nidaq.lock'
        self._driver.log_file = str()


        # set ADC value (from setup.ini)
        config_list = self._driver.get_required_adc_config()
        config_dict = dict()
        adc_list = self._config.get_adc_list()
        for adc_name in adc_list:
            adc_config_dict = dict()
            adc_setup = self._config.get_adc_setup(adc_name)
            for item in adc_setup:
                if item in config_list:
                    adc_config_dict[item] = adc_setup[item]
            if adc_config_dict:
                config_dict[adc_name] = adc_config_dict

        self.set_adc_config_from_dict(config_dict)
                   
            
                            


    def set_adc_config_from_dict(self, config_dict):
        
        if not config_dict:
            return
       
        if self._driver_name=='polaris' or self._driver_name=='pydaqmx':
            self._driver.set_adc_config_from_dict(config_dict)
          
            

    def set_adc_config(self,adc_name, sample_rate=[],nb_samples=[],
                       voltage_min=list(),voltage_max=list(),
                       channel_list=list(),
                       buffer_length= [],
                       trigger_type=[]):
        

        if self._driver_name=='polaris' or _driver_name=='pydaqmx':
            self._driver.set_adc_config(adc_name, sample_rate=sample_rate,
                                        nb_samples=nb_samples,
                                        voltage_min=voltage_min,voltage_max=voltage_max,
                                        trigger_type = trigger_type,
                                        channel_list=channel_list,
                                        buffer_length=buffer_length)

    

    def set_detector_config(self, config_dict):
        """
        Set detector config dictionary
        """
        
        if not config_dict:
            return

       
        if self._driver_name=='polaris':
            self._driver.set_detector_config(config_dict)
        


    def run(self, run_time=60, run_type=1, run_comment='No comment',
            group_name='None', group_comment='No comment',
            data_prefix='raw', data_path=None,
            write_config=True, debug=False):
        
        success = False

        # run purpose (using "run type" -> "run pupose" table)
        run_purpose = 'Test'
        if run_type in self._run_purpose_dict:
            run_purpose = self._run_purpose_dict[run_type]
        
        # facilty, fridge run
        facility_num = self._config.get_facility_num()
        fridge_run = self._config.get_fridge_run()
        
        # data path
        if data_path is None:
            data_path = self._config.get_data_path()

            

        # run polaris
        if self._driver_name=='polaris':

            # polaris config
            polaris_config = self._config.get_polaris_info()
            if polaris_config:
                self._driver.set_polaris_config(polaris_config)

            # run config
            run_config = dict()
            run_config['facility'] = facility_num
            run_config['fridge_run'] = fridge_run
            run_config['comment'] = '"' + run_comment + '"'
            run_config['run_purpose'] = run_purpose
            run_config['run_type'] = run_type
            run_config['group_name'] = group_name
            run_config['group_comment'] = '"' + group_comment + '"'
            
            prefix = data_path + '/'
            if data_prefix:
                prefix =  prefix + data_prefix
            run_config['prefix'] = prefix

            self._driver.set_run_config(run_config)
            
            # run
            success = self._driver.run(run_time=run_time, run_comment=run_comment,
                                       write_config=write_config, debug=debug)


        elif self._driver_name=='pydaqmx':
            
            # run 
            success = self._driver.run(run_time=run_time, run_comment=run_comment)

        return success


    def read_single_event(self, data_array, do_clear_task=False):

        # only for "pydaqmx"
        if not self._driver_name=='pydaqmx':
            print('ERROR: "read_single_event" only available with "pydaqmx" driver')
            

        # read event
        self._driver.read_single_event(data_array=data_array, 
                                       do_clear_task=do_clear_task)


    def clear(self):
        if self._driver_name=='pydaqmx':
            self._driver.clear_task() 
            
