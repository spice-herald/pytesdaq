"""
TBD
"""

import numpy as np
import nidaqmx
from nidaqmx.utils import flatten_channel_string
from nidaqmx.task import Task
from nidaqmx.stream_readers import (
    AnalogUnscaledReader, AnalogSingleChannelReader, AnalogMultiChannelReader)
import time

import pytesdaq.instruments.niadc as niadc
from pytesdaq.utils import arg_utils


class NITask(Task):
    """
    TBD
    """

    def __init__(self, new_task_name=''):
        super().__init__(new_task_name)
        
        
        # initialize some parameters
        self._lock_daq=True
        self._lock_file = '/tmp/nidaq.lock'
        self._log_file = str()
        self._verbose = True
        self._quiet = False
        
        # ADC config / Detector configure
        self._adc_config = dict()
        self._det_config = dict()
        self._is_run_configured = False
        self._required_adc_config = ['sample_rate', 'nb_samples', 'channel_list',
                                     'device_name', 'voltage_min','voltage_max',
                                     'trigger_type']

        # check if device available
        devices = niadc.NIDevice.get_device_list()
        if not devices:
            print('ERROR: no NI device available!')
            self.close()
            return 

        # ni reader
        self._ni_reader = AnalogUnscaledReader(self.in_stream)

        # useful data taking variable
        self._nb_samples = 0
        self._nb_channels = 0
        self._event_counter = 0
        self._is_continuous =False
        
        # output array
        self._data_array = []
     
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
    def is_run_configured(self):
        return self._is_run_configured



    def set_adc_config_from_dict(self, config_dict):
        """
        Set ADC configuration
        """
        self._adc_config = config_dict
        self._is_run_configured = False


    def set_adc_config(self,adc_name, device_name = str(), sample_rate=[],nb_samples=[],
                       voltage_min = [],voltage_max = [], channel_list=list(), 
                       trigger_type = [], buffer_length = [],filter_enable=[]):
        
            
        """
        Update ADC configuration dictionary 
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
    
        # buffer_length:
        if buffer_length:
            adc_dict['buffer_length'] = buffer_length

        if filter_enable:
            adc_dict['filter_enable'] = filter_enable
        
        # trigger type
        if trigger_type:
            adc_dict['trigger_type'] = trigger_type
            
         
        self._adc_config[adc_name] = adc_dict
        self._is_run_configured = False
        
    

    def get_required_adc_config(self):
        return self._required_adc_config



    def clear_task(self):
        self.close()
        self._is_run_configured = False
    

    def _configure_run(self):

        # check adc_config is filled
        if not self._adc_config:
            print('ERROR: First set configuration with "set_adc_config"!')
            return False

        # FIXME -> Only for one device
        adc_keys = list(self._adc_config.keys())
        if len(adc_keys)!=1:
            print('ERROR: Unable to take data with multiple devices (FIXME)')
            return False

        config_dict = self._adc_config[adc_keys[0]]   


        # check required parameter
        for param in self._required_adc_config:
            if param not in config_dict:
                print('ERROR from polaris::write_config:  Missing ADC configuration "' + param + '"!')
                return False



        # set channels
        channel_list = config_dict['channel_list']
        if isinstance(channel_list,str):
            channel_list =  arg_utils.hyphen_range(config_dict['channel_list'])
            
        channel_names = list()
        for chan in channel_list:
            channel_names.append(config_dict['device_name'] + '/ai' + str(chan))
        channel_names_flatten = flatten_channel_string(channel_names)

        # set channels/voltage
        ai_voltage_channels = self.ai_channels.add_ai_voltage_chan(str(channel_names_flatten),
                                                                   max_val=float(config_dict['voltage_max']),
                                                                   min_val=float(config_dict['voltage_min']))
        


        # fill useful container
        self._nb_samples = int(config_dict['nb_samples'])
        self._nb_channels = len(channel_list)


        # transfer mode (not sure it is doing anything...)
        #ai_voltage_channels.ai_data_xfer_mech = nidaqmx.constants.DataTransferActiveTransferMode.INTERRUP
        #ai_voltage_channels.ai_data_xfer_mech = nidaqmx.constants.DataTransferActiveTransferMode.DMA
        

        # sampling rate / trigger mode (continuous vs finite)
        buffer_length = self._nb_samples
        if config_dict['trigger_type']==1:
            buffer_length = int(config_dict['sample_rate'])

        if 'buffer_length' in config_dict:
            buffer_length =config_dict['buffer_length']
               
        mode = int()
        if config_dict['trigger_type']==1:
            mode = nidaqmx.constants.AcquisitionType.CONTINUOUS
        else:
            mode = nidaqmx.constants.AcquisitionType.FINITE


        self.timing.cfg_samp_clk_timing(int(config_dict['sample_rate']),
                                        sample_mode=mode,
                                        samps_per_chan=buffer_length)
    
                   


        # low pass filter (PCI-6120 only)
        if niadc.NIDevice.get_product_type()=='PCI-6120':
            ai_voltage_channels.ai_lowpass_enable=True # default
            if 'filter_enable' in config_dict and not config_dict['filter_enable']:
                ai_voltage_channels.ai_lowpass_enable=False
                                
        # external trigger
        if config_dict['trigger_type']==2:
            self.triggers.start_trigger.cfg_dig_edge_start_trig(trigger_source='/'+ config_dict['device_name'] 
                                                                + '/pfi0')
            

        # data mode
        if config_dict['trigger_type']==1:
            self._is_continuous =True
        else:
            self._is_continuous =False
            
        # register callback function
        self.register_every_n_samples_acquired_into_buffer_event(self._nb_samples,
                                                                 self._read_callback)

        
        adc_conversion_factor = list()
        for chan in ai_voltage_channels:
            adc_conversion_factor.append(chan.ai_dev_scaling_coeff)
            
            
        config_dict['adc_conversion_factor'] = np.array(adc_conversion_factor)

        

        self._is_run_configured = True
    

       

    def _is_locked(self):
        f_lock = open(self._lock_file,'w+')
        try:
            fcntl.flock(f_lock,fcntl.LOCK_EX | fcntl.LOCK_NB)
        except:
            f_lock.close()
            print('\nERROR: Ongoing data taking... Stop data taking before starting a new run!\n')
            return True
        else:
            fcntl.flock(f_lock,fcntl.LOCK_UN)
        f_lock.close() 
        return False



    def run(self,run_time=60, max_nb_events=[], run_comment=str(),):
        
        # configure:
        self._configure_run()

        # initialize data
        self._data_array = np.zeros((self._nb_channels,self._nb_samples), dtype=np.int16)
         
        # loop max events and/or runtime
        self._event_counter = 0
        while (self._event_counter < 3):
            # start task
            self.start()
            
            # wait until task is done -> then exit
            run_continue = True
            while(run_continue):
                run_continue = not self.is_task_done()
                time.sleep(0.1)
                
            # stop task
            self.stop()
            
            # task done if continuous
            if self._is_continuous:
                break
    
        self.clear_task()
      


    def read_single_event(self,data_array, do_clear_task=False):

        
        # configure if needed
        if not self._is_run_configured:
            self._configure_run()

        # data array
        self._data_array = data_array

        # check if continuous
        if self._is_continuous:
            print('ERROR: "read_single_event" only for finite data, not continuous!')
            return

                    
        # start task
        self.start()
        
        # wait task is done
        run_continue = True
        while(run_continue):
            run_continue = not self.is_task_done()
            time.sleep(0.005)   

        self.stop()
        
        if do_clear_task:
            self.clear_task()
        








    def _read_callback(self,task_handle,
                       every_n_samples_event_type,
                       number_of_samples,
                       callback_data):

        
        # type of data (FIXME: hardcoded)
        data_type = 'int16'

        try:
            # available samples, postion in buffer
            #num_samples_available = int(self.in_stream.avail_samp_per_chan
            #curr_read_pos = self.in_stream.curr_read_pos

            if data_type=='int16':
                self._ni_reader.read_int16(self._data_array,number_of_samples_per_channel=self._nb_samples,
                                           timeout=nidaqmx.constants.WAIT_INFINITELY)
                

            self._event_counter+=1

        except nidaqmx.errors.DaqWarning as warn:
            print('WARNING: ' + str(warn))
            self.stop()
            
        except nidaqmx.errors.DaqError as err:
            print('ERROR: ' + str(err))
            self.stop()

        return 0
