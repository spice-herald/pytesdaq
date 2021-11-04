"""
Main instrumentation control class
"""
import time
import numpy
import pytesdaq.config.settings as settings
import pytesdaq.io.redis as redis
from pytesdaq.utils import connection_utils
import pytesdaq.utils.remote as remote
from  pytesdaq.instruments.feb  import FEB
from pytesdaq.instruments.magnicon import Magnicon
from pytesdaq.instruments.lakeshore import Lakeshore
from pytesdaq.instruments.imacrt import MACRT
from  pytesdaq.instruments.keysight import KeysightFuncGenerator
import pytesdaq.io.redis as redis
from pytesdaq.utils import connection_utils
import pytesdaq.utils.remote as remote
from math import nan
import pandas as pd
from IPython.display import display

class Control:
    """
    Control TES related instruments
    """
    
    def __init__(self, setup_file=None, verbose=True,
                 dummy_mode=False, raise_errors=True):
        
        # for code development
        self._dummy_mode = dummy_mode
        self._verbose = verbose
        self._raise_errors = raise_errors
        self._debug = False
        
        # config
        self._setup_file = setup_file
        self._config = settings.Config(setup_file=setup_file)
      
        # signal connection map
        self._connection_table = self._config.get_adc_connections()
            
        # TES/SQUID Controller
        self._squid_controller_name = self._config.get_squid_controller()
        self._readout_inst = None

        # Signal Generator Controller
        self._signal_generator_name = self._config.get_signal_generator()
        self._signal_generator_inst = None
        
        # Temperatuer controllers (multiple controller allowed)
        self._temperature_controller_name_list = self._config.get_temperature_controllers()
        self._temperature_controller_insts = None
        self._resistance_channel_table = None
        self._heater_channel_table = None
        
        if not self._dummy_mode:
            self._connect_instruments()   
 
        # redis
        self._enable_redis = self._config.enable_redis()
        self._read_from_redis = False
        if self._enable_redis:
             self._redis_db = redis.RedisCore()
             self._redis_db.connect()
             
        # readback 
        self._enable_readback = self._config.enable_redis()


    def __del__(self):
        """
        """


        # temperature controllers
        if self._temperature_controller_insts  is not None:
         for name, inst in self._temperature_controller_insts.items():
             inst.disconnect()

        
    @property
    def verbose(self):
        return self._verbose
        
    @verbose.setter
    def verbose(self, value):
        self._verbose=value
        
    @property
    def read_from_redis(self):
        return self._read_from_redis
        
    @read_from_redis.setter
    def read_from_redis(self, value):
        if value and not self._enable_redis:
            print('WARNING: unable to read from Redis! Redis DB not enabled...)')
        else:
            self._read_from_redis=value
        
    @property
    def squid_controller_name(self):
        return self._squid_controller_name

    @property
    def signal_generator_name(self):
        return self._signal_generator_name

    @property
    def temperature_controller_names(self):
        return self._temperature_controller_name_list

    
            

    def set_tes_bias(self, bias, 
                     tes_channel=None,
                     detector_channel=None,
                     adc_id=None, adc_channel=None):
        
        """
        Set TES bias 
        """
        try:
            self._set_sensor_val('tes_bias', bias,
                                 tes_channel=tes_channel,
                                 detector_channel=detector_channel,
                                 adc_id=adc_id, adc_channel=adc_channel)
        except:
            print('ERROR setting TES bias')
            return False

        return True
    


    def set_squid_bias(self, bias, 
                       tes_channel=None,
                       detector_channel=None,
                       adc_id=None, adc_channel=None):
        
        """
        Set SQUID bias 
        """
        try:
            self._set_sensor_val('squid_bias', bias,
                                 tes_channel=tes_channel,
                                 detector_channel=detector_channel,
                                 adc_id=adc_id, adc_channel=adc_channel)
        except:
            print('ERROR setting SQUID bias')
            return False

        return True
    



    def set_lock_point(self, lock_point, 
                       tes_channel=None,
                       detector_channel=None,
                       adc_id=None, adc_channel=None):
        

        """
        Set SQUID lock point
        """
        try:
            self._set_sensor_val('lock_point_voltage', lock_point,
                                 tes_channel=tes_channel,
                                 detector_channel=detector_channel,
                                 adc_id=adc_id, adc_channel=adc_channel)
        except:
            print('ERROR setting SQUID lock point')
            return False

        return True
    


 
    def set_feedback_gain(self, gain, 
                          tes_channel=None,
                          detector_channel=None,
                          adc_id=None, adc_channel=None):
        

        """
        Set Feedback gain (magnicon: gain-bw product) [Hz]
        
        """
        try:
            self._set_sensor_val('feedback_gain', gain,
                                 tes_channel=tes_channel,
                                 detector_channel=detector_channel,
                                 adc_id=adc_id, adc_channel=adc_channel)
        except:
            print('ERROR setting feedback gain')
            return False

        return True
    


    def set_preamp_gain_bandwidth(self, gain, 
                                  tes_channel=None,
                                  detector_channel=None,
                                  adc_id=None, adc_channel=None):
        

        """
        Set preamp gain, and for magnicon bandwidth
        """
        try:
            self._set_sensor_val('preamp_gain', gain,
                                 tes_channel=tes_channel,
                                 detector_channel=detector_channel,
                                 adc_id=adc_id, adc_channel=adc_channel)
        except:
            print('ERROR setting preamp gain')
            return False

        return True




    def set_output_offset(self, offset, 
                          tes_channel=None,
                          detector_channel=None,
                          adc_id=None, adc_channel=None):
        

        """
        Set output offset
        """
        try:
            self._set_sensor_val('output_offset', offset,
                                 tes_channel=tes_channel,
                                 detector_channel=detector_channel,
                                 adc_id=adc_id, adc_channel=adc_channel)
        except:
            print('ERROR setting output offset')
            return False

        return True
    


    def set_output_gain(self, gain, 
                        tes_channel=None,
                        detector_channel=None,
                        adc_id=None, adc_channel=None):
        


        """
        Set output gain
        """
        try:
            self._set_sensor_val('output_gain', gain,
                                 tes_channel=tes_channel,
                                 detector_channel=detector_channel,
                                 adc_id=adc_id, adc_channel=adc_channel)
        except:
            print('ERROR setting output gain')
            return False

        return True  
            

    def set_feedback_polarity(self, val, 
                              tes_channel=None,
                              detector_channel=None,
                              adc_id=None, adc_channel=None):
        

        """
        Set feedback loop polarity
        invert = True
        non invert = False
        """
        try:
            self._set_sensor_val('feedback_polarity', val,
                                 tes_channel=tes_channel,
                                 detector_channel=detector_channel,
                                 adc_id=adc_id, adc_channel=adc_channel)
        except:
            print('ERROR setting feedback polarity')
            return False
        
        return True
        
            
    def set_feedback_mode(self, val, 
                          tes_channel=None,
                          detector_channel=None,
                          adc_id=None, adc_channel=None):
        

        """
        Set feedback mode: 'open' or 'close'
        """
        try:
            self._set_sensor_val('feedback_mode', val,
                                 tes_channel=tes_channel,
                                 detector_channel=detector_channel,
                                 adc_id=adc_id, adc_channel=adc_channel)
        except:
            print('ERROR setting feedback loop state (open/closed)')
            return False

        return True


    def relock(self,
               tes_channel=None,
               detector_channel=None,
               adc_id=None, adc_channel=None,
               num_relock=2):
        

        """
        Relock (open/close)

        Parameters:
        ----------
           Required: tes_channel OR detector_channel 
                     OR (adc_id AND adc_channel)
        """

        for ilock in range(num_relock):

            # open
            self.set_feedback_mode('open', 
                                   tes_channel=tes_channel,
                                   detector_channel=detector_channel,
                                   adc_id=adc_id, adc_channel=adc_channel)

            # sleep 2 seconds
            time.sleep(2)

            # close
            self.set_feedback_mode('close', 
                                   tes_channel=tes_channel,
                                   detector_channel=detector_channel,
                                   adc_id=adc_id, adc_channel=adc_channel)
            # sleep 2 seconds
            time.sleep(2)

    


    def set_signal_source(self, source, 
                          tes_channel=None,
                          detector_channel=None,
                          adc_id=None, adc_channel=None):
        

        """
        Set readout source ('preamp' or 'feedback') 
        """

        

        try:
            self._set_sensor_val('signal_source', source,
                                 tes_channel=tes_channel,
                                 detector_channel=detector_channel,
                                 adc_id=adc_id, adc_channel=adc_channel)
        except:
            print('ERROR setting signal source')
            return False

        return True   



    

    def set_signal_gen_onoff(self, on_off_flag, signal_gen_num=1, tes_channel=None,
                             detector_channel=None, adc_id=None, adc_channel=None):

        """
        Set signal gen on/off
        """
        if on_off_flag not in ['on','off']:
            print('ERROR in set_signal_gen_onoff:  Argument is  "on" or "off"')
            return
            

        if self._dummy_mode:
            print('INFO: Setting signal generator #' + str(signal_gen_num) + ' ' +
                  on_off_flag)
            return
        
        
        
        if self._signal_generator_name == 'magnicon':

            # get readout controller ID and Channel (FIXME: Is it necessary)
            controller_id, controller_channel = (
                connection_utils.get_controller_info(self._connection_table,
                                                     tes_channel=tes_channel,
                                                     detector_channel=detector_channel,
                                                     adc_id=adc_id,
                                                     adc_channel=adc_channel)
            )


                        
            mon_onoff = 'OFF'
            gen1_onoff = 'OFF'
            gen2_onoff = 'OFF'
            if signal_gen_num == 1:
                gen1_onoff = on_off_flag.upper()
            else:
                gen2_onoff = on_off_flag.upper()


            if gen1_onoff=='ON' or gen2_onoff=='ON':
                mon_onoff = 'ON'

            rb_onoff1, rb_onoff, rb_mon_onoff = (
                self._readout_inst.set_generator_onoff(controller_channel, 
                                                       gen1_onoff, gen2_onoff, mon_onoff)
            )

        else:
            self._signal_generator_inst.set_generator_onoff(on_off_flag.lower(),
                                                            source=signal_gen_num)
            
            

    
    def set_signal_gen_params(self, tes_channel=None,
                              detector_channel=None,
                              adc_id=None, adc_channel=None,
                              signal_gen_num=1, source=None,
                              voltage=None, current=None, offset=None,
                              frequency=None, shape=None, phase_shift=0,
                              freq_div=0, half_pp_offset='OFF'):

        """
        Set signal generator parameters

        source:  'tes' or 'feedback' (required)
        voltage: peak-to-peak voltage amplitude  [mVpp]
        current: peak-to-peak current amplitude  [uA]
        frequency: Float [Hz] (Default = 100 Hz)
        shape: 'triangle', 'sawtoothpos', 'sawtoothneg', 'square', 'sine', 'noise'
        offset: DC offset in mV
        """
        
        


        # check parameters
        if voltage is not None and current is not None:
            print('ERROR: Set signal generator amplitude either with "current" or "voltage", not both!')
            return
        
        if source is not None and (source != 'tes' and source != 'feedback'):
            print('ERROR: Source can be either "tes" or "feedback"')
            
              
        if self._dummy_mode:
            print('INFO: Setting signal generator #' + str(signal_gen_num))
            return



        # initialize readback values
        readback_amp = nan
        readback_freq = nan

        # magnicon
        if self._signal_generator_name == 'magnicon': 



            # get readout controller ID and Channel
            controller_id, controller_channel = (
                connection_utils.get_controller_info(self._connection_table,
                                                     tes_channel=tes_channel,
                                                     detector_channel=detector_channel,
                                                     adc_id=adc_id,
                                                     adc_channel=adc_channel)
            )




            
            # convert some parameters
            source_magnicon = 'I'
            if source == 'feedback':
                source_magnicon = 'Ib'



            readback_amp, readback_freq = (
                self._readout_inst.set_generator_params(int(controller_channel), int(signal_gen_num), 
                                                         float(frequency), source_magnicon, shape, 
                                                         int(phase_shift), int(freq_div), half_pp_offset, 
                                                         float(current))
                )
            

        # External function generator
        else:


            # shape
            if shape is not None:
                if shape == 'sawtoothpos' or shape == 'sawtoothneg':
                    shape = 'ramp'
                self._signal_generator_inst.set_shape(shape, source=signal_gen_num)
            
            # amplitude
            if voltage is None and current is not None:
                resistance = float(self._config.get_signal_gen_tes_resistance())
                voltage = resistance*current/1000

            if voltage is not None:
                self._signal_generator_inst.set_amplitude(voltage, unit='mVpp', source=signal_gen_num)

            # frequency
            if frequency is not None:
                self._signal_generator_inst.set_frequency(frequency, unit='Hz', source=signal_gen_num)


            # offset
            if offset is not None:
                self._signal_generator_inst.set_offset(offset, unit='mV', source=signal_gen_num)


                
            # source
            if source is not None and self._squid_controller_name == 'feb':

                
                # get readout controller ID and Channel
                controller_id, controller_channel = (
                    connection_utils.get_controller_info(self._connection_table,
                                                         tes_channel=tes_channel,
                                                         detector_channel=detector_channel,
                                                         adc_id=adc_id,
                                                         adc_channel=adc_channel)
                )


                connect_to_tes = False
                connect_to_feedback = False
                
                if source == 'tes':
                    connect_to_tes = True
                if source == 'feedback':
                    connect_to_feedback = True
                    
                self.connect_signal_gen_to_tes(connect_to_tes,
                                               tes_channel=tes_channel,
                                               detector_channel=detector_channel,
                                               adc_id=adc_id,
                                               adc_channel=adc_channel)
                
                self.connect_signal_gen_to_feedback(connect_to_feedback,
                                                    tes_channel=tes_channel,
                                                    detector_channel=detector_channel,
                                                    adc_id=adc_id,
                                                    adc_channel=adc_channel)
                
                            
            
            # phase shift, half_pp_offset, not implemented
                        
            




    def connect_signal_gen_to_feedback(self, do_connect, 
                                    tes_channel=None,
                                    detector_channel=None,
                                    adc_id=None, adc_channel=None):
        
        
        """
        Set signal generator feedback connection (True) or feedback (False)
        """
        
        

        try:
            self._set_sensor_val('signal_gen_feedback_connection',bool(do_connect),
                                 tes_channel=tes_channel,
                                 detector_channel=detector_channel,
                                 adc_id=adc_id, adc_channel=adc_channel)
        except:
            print('ERROR setting signal generator feedback connection')
            return False

        return True   



    def connect_signal_gen_to_tes(self, do_connect, 
                                  tes_channel=None,
                                  detector_channel=None,
                                  adc_id=None, adc_channel=None):
        
        
        """
        Set  connection signal generator TES line (True) or tes (False)
        """
        
        

        try:
            self._set_sensor_val('signal_gen_tes_connection', bool(do_connect),
                                 tes_channel=tes_channel,
                                 detector_channel=detector_channel,
                                 adc_id=adc_id, adc_channel=adc_channel)
        except:
            print('ERROR setting signal generator TES line connection')
            return False

        return True   





    def get_tes_bias(self, 
                     tes_channel=None,
                     detector_channel=None,
                     adc_id=None, adc_channel=None):
        


        """
        Get TES bias 
        """
        bias = nan
        #try:
        bias = self._get_sensor_val('tes_bias',
                                    tes_channel=tes_channel,
                                    detector_channel=detector_channel,
                                    adc_id=adc_id, adc_channel=adc_channel)
            
        #except:
        #    print('ERROR getting TES bias')
            
        return bias
        
        
    def get_squid_bias(self, 
                       tes_channel=None,
                       detector_channel=None,
                       adc_id=None, adc_channel=None):
        


        """
        Get SQUID bias 
        """
        bias = nan
        try:
            bias = self._get_sensor_val('squid_bias',
                                        tes_channel=tes_channel,
                                        detector_channel=detector_channel,
                                        adc_id=adc_id, adc_channel=adc_channel)
                                                   
        except:
            print('ERROR getting SQUID bias')
            
        return bias




    def get_lock_point(self, 
                       tes_channel=None,
                       detector_channel=None,
                       adc_id=None, adc_channel=None):
        


        """
        Get lock point [mV]
        """
        lock_point = nan
        try:
            lock_point = self._get_sensor_val('lock_point_voltage',
                                              tes_channel=tes_channel,
                                              detector_channel=detector_channel,
                                              adc_id=adc_id, adc_channel=adc_channel)
            
        except:
            print('ERROR getting lock point')
            
        return lock_point




    def get_feedback_gain(self, 
                          tes_channel=None,
                          detector_channel=None,
                          adc_id=None, adc_channel=None):
        


        """
        Get feedback gain

        """
        feedback_gain = nan
        try:
            feedback_gain = self._get_sensor_val('feedback_gain',
                                                 tes_channel=tes_channel,
                                                 detector_channel=detector_channel,
                                                 adc_id=adc_id, adc_channel=adc_channel)
            
        except:
            print('ERROR getting feedback gain')
            
        return feedback_gain


    def get_output_offset(self, 
                          tes_channel=None,
                          detector_channel=None,
                          adc_id=None, adc_channel=None):
        
        """
        Get output offset
        """
        output_offset = nan
        try:
            output_offset = self._get_sensor_val('output_offset',
                                                 tes_channel=tes_channel,
                                                 detector_channel=detector_channel,
                                                 adc_id=adc_id, adc_channel=adc_channel)
            
        except:
            print('ERROR getting output offset')
            
        return output_offset




    def get_output_total_gain(self, 
                              tes_channel=None,
                              detector_channel=None,
                              adc_id=None, adc_channel=None):
        
        """
        Get output gain
        """
        output_variable_gain = 1
        try:
            output_variable_gain = self._get_sensor_val('output_gain',
                                                        tes_channel=tes_channel,
                                                        detector_channel=detector_channel,
                                                        adc_id=adc_id, adc_channel=adc_channel)
            
        except:
            print('ERROR getting output gain')
            

        # fix gain
        output_fix_gain = self._config.get_output_fix_gain()
        
        # total gain
        if output_variable_gain == nan:
            output_total_gain = output_fix_gain
        else:
            output_total_gain = output_fix_gain * output_variable_gain
            
            
        return output_total_gain




    def get_preamp_total_gain(self, 
                              tes_channel=None,
                              detector_channel=None,
                              adc_id=None, adc_channel=None):
        
        """
        Get preamp gain (variable*fix gain)
        """
        preamp_variable_gain = 1
        try:
            preamp_variable_gain = self._get_sensor_val('preamp_gain',
                                                        tes_channel=tes_channel,
                                                        detector_channel=detector_channel,
                                                        adc_id=adc_id, adc_channel=adc_channel)
            
        except:
            print('ERROR getting preamp gain')
            

        # fix gain
        preamp_fix_gain = self._config.get_preamp_fix_gain()
        
        # total gain
        if preamp_variable_gain == nan:
            preamp_total_gain = preamp_fix_gain
        else:
            preamp_total_gain = preamp_fix_gain * preamp_variable_gain
            
            
        return preamp_total_gain


    

    def get_squid_loop_total_gain(self, 
                                  tes_channel=None,
                                  detector_channel=None,
                                  adc_id=None, adc_channel=None):
        
        
        # preamp gain
        preamp_gain = self.get_preamp_total_gain(tes_channel=tes_channel,
                                                 detector_channel=detector_channel,
                                                 adc_id=adc_id, adc_channel=adc_channel)
        
        # feedback gain (outside preamp)
        # FIXME: Only fix gain??
        feedback_gain = self._config.get_feedback_fix_gain()

        
        gain = preamp_gain * feedback_gain
        return gain
        

        
    def get_feedback_polarity(self, 
                              tes_channel=None,
                              detector_channel=None,
                              adc_id=None, adc_channel=None):
        


        """
        Get feedback polarity
        """
        feedback_polarity = nan
        try:
            feedback_polarity = self._get_sensor_val('feedback_polarity',
                                                     tes_channel=tes_channel,
                                                     detector_channel=detector_channel,
                                                     adc_id=adc_id, adc_channel=adc_channel)
            
        except:
            print('ERROR getting  feedback polarity')
            
        return feedback_polarity
            




    def get_feedback_mode(self, 
                          tes_channel=None,
                          detector_channel=None,
                          adc_id=None, adc_channel=None):
        
        """
        Get feedback mode ('open' or 'close')
        """

        mode = nan
        try:
            mode = self._get_sensor_val('feedback_mode',
                                        tes_channel=tes_channel,
                                        detector_channel=detector_channel,
                                        adc_id=adc_id, adc_channel=adc_channel)
            
        except:
            print('ERROR getting  feedback polarity')
            
        return mode
            



    def get_signal_source(self, 
                          tes_channel=None,
                          detector_channel=None,
                          adc_id=None, adc_channel=None):
        


        """
        Get readout source
        """

        source = nan
        try:
            source = self._get_sensor_val('signal_source',
                                          tes_channel=tes_channel,
                                          detector_channel=detector_channel,
                                          adc_id=adc_id, adc_channel=adc_channel)
            
        except:
            print('ERROR getting signal source')
            
        return is_preamp
            


    def is_signal_gen_connected_to_feedback(self, 
                                            tes_channel=None,
                                            detector_channel=None,
                                            adc_id=None, adc_channel=None):
        
        

        """
        Is signal generator connected to feedback
        """
        
        is_connected = nan
        try:
            is_connected = self._get_sensor_val('signal_gen_feedback_connection',
                                                tes_channel=tes_channel,
                                                detector_channel=detector_channel,
                                                adc_id=adc_id, adc_channel=adc_channel)
          
        except:
            print('ERROR getting signal generator connection')
            
        return is_connected
            

    
    def get_signal_gen_onoff(self, signal_gen_num=1, tes_channel=None,
                             detector_channel=None, adc_id=None, adc_channel=None):

        """
        Get signal gen state ("on"/"off")
        """
                   

        if self._dummy_mode:
            return "off"
            
        
        # get readout controller ID and Channel (FIXME: Is it necessary?)
        controller_id, controller_channel = connection_utils.get_controller_info(self._connection_table,
                                                                                 tes_channel=tes_channel,
                                                                                 detector_channel=detector_channel,
                                                                                 adc_id=adc_id,
                                                                                 adc_channel=adc_channel)
        

        val = nan
        if self._signal_generator_name == 'magnicon':
            gen1_onoff, gen2_onoff, mon_onoff = self._readout_inst.get_generator_onoff(controller_channel)
            if signal_gen_num == 1:
                val = gen1_onoff.lower()
            else:
                val = gen2_onoff.lower()

        else:
            val = self._signal_generator_inst.get_generator_onoff(source=signal_gen_num)
            
                        

        return val

        

    def is_signal_gen_on(self, signal_gen_num=1, tes_channel=None,
                         detector_channel=None, adc_id=None, adc_channel=None): 

        """
        Is signal generator on?
        Return: BOOL
        """

        val = self.get_signal_gen_onoff(signal_gen_num=signal_gen_num, tes_channel=tes_channel,
                                        detector_channel=detector_channel, 
                                        adc_id=adc_id, adc_channel=adc_channel)

        val_bool = None
        if val == 'on':
            val_bool = True
        elif  val == 'off':
            val_bool = False
        else:
            val_bool = val

        return val_bool
            
        



    def get_signal_gen_params(self, signal_gen_num=1, 
                              tes_channel=None,
                              detector_channel=None,
                              adc_id=None, adc_channel=None):
        
        """
        Get signal generator parameters
        Return:
           dictionary
        """
                
        
        # initialize dictionary
        output_dict = dict()
        output_dict['source'] = nan
        output_dict['frequency'] = nan
        output_dict['shape'] = nan
        output_dict['phase_shift'] = nan
        output_dict['freq_div'] = nan
        output_dict['half_pp_offset'] = nan
        output_dict['voltage'] = []
        output_dict['current'] = []

        # magnicon
        if self._signal_generator_name == 'magnicon':


            # get readout controller ID and Channel
            controller_id, controller_channel = (
                connection_utils.get_controller_info(self._connection_table,
                                                     tes_channel=tes_channel,
                                                     detector_channel=detector_channel,
                                                     adc_id=adc_id,
                                                     adc_channel=adc_channel)
            )
        

            if self._dummy_mode:
                print('INFO: Getting signal generator #' + str(signal_gen_num) + ', ' + 
                      controller_id + ' channel ' + str(controller_channel))
                return output_dict
            
            
            # convert some parameters
            source_magnicon = 'I'
           
            source, shape, freq, freq_div, shift, amp, offset = (
                self._readout_inst.get_generator_params(controller_channel,
                                                         signal_gen_num)
            )
            
            # fill dictionary
            if source=='I':
                output_dict['source'] = 'tes'
            elif source=='Ib':
                output_dict['source'] = 'feedback'
            else:
                output_dict['source'] = source

            output_dict['current'] = amp/1000000.0
            output_dict['voltage'] = []
            output_dict['frequency'] = freq
            output_dict['shape'] = shape
            output_dict['phase_shift'] = shift
            output_dict['freq_div'] = freq_div
            output_dict['half_pp_offset'] = offset



        # external signal generator
        else:

            # signal generator parameter
            if not self._dummy_mode:
                output_dict['voltage'] = float(
                    self._signal_generator_inst.get_amplitude(source=signal_gen_num)
                )
                resistance = float(self._config.get_signal_gen_tes_resistance())
                output_dict['current']  = float(output_dict['voltage']/resistance)
                output_dict['frequency'] = float(
                    self._signal_generator_inst.get_frequency(source=signal_gen_num)
                )
                output_dict['shape'] = self._signal_generator_inst.get_shape(source=signal_gen_num)

            # source
            if self._squid_controller_name == 'feb':


                # get readout controller ID and Channel
                controller_id, controller_channel = (
                    connection_utils.get_controller_info(self._connection_table,
                                                         tes_channel=tes_channel,
                                                         detector_channel=detector_channel,
                                                         adc_id=adc_id,
                                                         adc_channel=adc_channel)
                )


                if self._dummy_mode:
                    print('INFO: Getting signal generator #' + str(signal_gen_num) + ', ' + 
                          controller_id + ' channel ' + str(controller_channel))
                    return output_dict

                
                is_connected_to_tes = (
                    self.is_signal_gen_connected_to_tes(tes_channel=tes_channel,
                                                        detector_channel=detector_channel,
                                                        adc_id=adc_id, adc_channel=adc_channel)
                )

                is_connected_to_feedback = (
                    self.is_signal_gen_connected_to_feedback(tes_channel=tes_channel,
                                                             detector_channel=detector_channel,
                                                             adc_id=adc_id, adc_channel=adc_channel)
                )

                
                if is_connected_to_tes and is_connected_to_feedback:
                    print('WARNING: Signal generator connected to both TES AND Feedback!')
                    
                if is_connected_to_tes:
                    output_dict['source'] = 'tes'
                elif is_connected_to_feedback:
                    output_dict['source'] = 'feedback'
                else:
                    output_dict['source'] = 'none'
            
            else:
                # FIXME: default to tes if not FEB
                output_dict['source'] = 'tes'
                
        return output_dict





    def is_signal_gen_connected_to_tes(self, 
                                       tes_channel=None,
                                       detector_channel=None,
                                       adc_id=None, adc_channel=None):
        
        """
        Is signal generator connected to TES line
        """

        is_connected = nan
        try:
            is_connected = self._get_sensor_val('signal_gen_tes_connection',
                                                tes_channel=tes_channel,
                                                detector_channel=detector_channel,
                                                adc_id=adc_id, adc_channel=adc_channel)
            
        except:
            print('ERROR getting signal generator connection')
            
        return is_connected
            



    def get_feedback_resistance(self, tes_channel=None,
                                detector_channel=None,
                                adc_id=None, adc_channel=None):
        """
        Get feedback resistance [Ohm]
           - Magnicon: value can be modified and read back
           - FEB: Needs to be in setup.ini file
        """
        
        feedback_resistance = nan


        # Magnicon: feedback resistance can be modifed and read
        if self._squid_controller_name == 'magnicon':
        
            try:
                feedback_resistance = self._get_sensor_val('feedback_resistance',
                                                           tes_channel=tes_channel,
                                                           detector_channel=detector_channel,
                                                           adc_id=adc_id, adc_channel=adc_channel)
            except:
                print('ERROR getting feedback resistance')

            # convert from kOhms to Ohms
            feedback_resistance = feedback_resistance *1000
                
        else:

            if (tes_channel is not None or  detector_channel is not None):
                adc_id, adc_channel = connection_utils.get_adc_channel_info(
                    self._connection_table,
                    tes_channel=tes_channel,
                    detector_channel=detector_channel
                )
            
            detector_config = self._config.get_detector_config(adc_id=adc_id,
                                                               adc_channel_list=[adc_channel])

            if ('feedback_resistance' in  detector_config and
                len(detector_config['feedback_resistance'])==1):
                feedback_resistance = float(detector_config['feedback_resistance'][0])
                
        
            
        return feedback_resistance


    def get_shunt_resistance(self, tes_channel=None,
                             detector_channel=None,
                             adc_id=None, adc_channel=None):
        """
        Get shunt resistance [Ohm]
        (from setup file)
        """
        
        shunt_resistance = nan

        # get ADC id/number
        if (tes_channel is not None or  detector_channel is not None):
            adc_id, adc_channel = connection_utils.get_adc_channel_info(
                self._connection_table,
                tes_channel=tes_channel,
                detector_channel=detector_channel
            )

        # get detector config
        detector_config = self._config.get_detector_config(adc_id=adc_id,
                                                           adc_channel_list=[adc_channel])

        # extract shunt resistance
        if ('shunt_resistance' in  detector_config and
            len(detector_config['shunt_resistance'])==1):
            shunt_resistance = detector_config['shunt_resistance'][0]
                
        return shunt_resistance



    def get_squid_turn_ratio(self, tes_channel=None,
                             detector_channel=None,
                             adc_id=None, adc_channel=None):
        """
        Get SQUID loop ratio (from setup file)
        """
        
        squid_turn_ratio = nan

        # get ADC id/number
        if (tes_channel is not None or  detector_channel is not None):
            adc_id, adc_channel = connection_utils.get_adc_channel_info(
                self._connection_table,
                tes_channel=tes_channel,
                detector_channel=detector_channel
            )

        # get detector config
        detector_config = self._config.get_detector_config(adc_id=adc_id,
                                                           adc_channel_list=[adc_channel])

        # extract shunt resistance
        if ('squid_turn_ratio' in  detector_config and
            len(detector_config['squid_turn_ratio'])==1):
            squid_turn_ratio = detector_config['squid_turn_ratio'][0]
                
        return squid_turn_ratio

    


    def get_volts_to_amps_close_loop_norm(self, tes_channel=None,
                                          detector_channel=None,
                                          adc_id=None, adc_channel=None):
        """
        get normalization to convert output volts to amps
        in close loop
        """
        
        # driver gain
        output_total_gain = self.get_output_total_gain(tes_channel=tes_channel,
                                                       detector_channel=detector_channel,
                                                       adc_id=adc_id, adc_channel=adc_channel)
        
        
        # feedback resistance
        feedback_resistance = self.get_feedback_resistance(tes_channel=tes_channel,
                                                           detector_channel=detector_channel,
                                                           adc_id=adc_id, adc_channel=adc_channel)

        if feedback_resistance == nan or feedback_resistance is None:
            print('ERROR: unable to find feedback resistance. It needs to be added in setup.ini file!')
            return None
        
        
        # squid loop turn ratio
        squid_turn_ratio = self.get_squid_turn_ratio(tes_channel=tes_channel,
                                                     detector_channel=detector_channel,
                                                     adc_id=adc_id, adc_channel=adc_channel)
     
        if squid_turn_ratio == nan or squid_turn_ratio is None:
            print('ERROR: unable to find SQUID turn ratio. It needs to be added in setup.ini file!')
            return None


        # calculate normalization
        norm = output_total_gain*feedback_resistance*squid_turn_ratio
        return norm





    def get_open_loop_preamp_norm(self, tes_channel=None,
                                  detector_channel=None,
                                  adc_id=None, adc_channel=None):
        """
        get open loop preamp normalization 
        
        """
        
        # driver gain
        output_total_gain = self.get_output_total_gain(tes_channel=tes_channel,
                                                       detector_channel=detector_channel,
                                                       adc_id=adc_id, adc_channel=adc_channel)
        
      
        # preamp gain
        preamp_total_gain = self.get_preamp_total_gain(tes_channel=tes_channel,
                                                       detector_channel=detector_channel,
                                                       adc_id=adc_id, adc_channel=adc_channel)
        

        # calculate normalization
        norm = output_total_gain*preamp_total_gain
        return norm
        


    def get_open_loop_full_norm(self, tes_channel=None,
                                detector_channel=None,
                                adc_id=None, adc_channel=None):
        """
        get open loop preamp normalization 
        
        """
        
        # driver gain
        output_total_gain = self.get_output_total_gain(tes_channel=tes_channel,
                                                       detector_channel=detector_channel,
                                                       adc_id=adc_id, adc_channel=adc_channel)
        
      
        # preamp gain
        loop_total_gain = self.get_squid_loop_total_gain(tes_channel=tes_channel,
                                                           detector_channel=detector_channel,
                                                           adc_id=adc_id, adc_channel=adc_channel)
        

        
        # calculate normalization
        norm = output_total_gain*loop_total_gain
        return norm



    

    def read_all(self, tes_channel_list=None, detector_channel_list=None,
                 adc_id=None, adc_channel_list=None):
        """
        Read from board all parameters
        Output in a dictionary: dict['param'] = array values (index based
          on input list)
        
        """

        if self._verbose:
            print('INFO: Reading detector settings from board...') 

        
            
        # ====================
        # Initialize output
        # ====================
        
        output_dict = dict()

        
        # intialize output
        param_list = ['tes_bias','squid_bias','lock_point_voltage','output_offset',
                      'output_gain','preamp_gain','feedback_polarity','feedback_mode',
                      'signal_source']
        
        for param in param_list:
            output_dict[param] = list()
     
        output_dict['signal_gen_voltage'] = list()
        output_dict['signal_gen_current'] = list()
        output_dict['signal_gen_frequency'] = list()
        output_dict['signal_gen_shape'] = list()
        output_dict['signal_gen_phase_shift'] = list()
        output_dict['signal_gen_source'] = list()
        output_dict['signal_gen_onoff'] = list()
        output_dict['feedback_resistance'] =  list()
        output_dict['squid_turn_ratio'] = list()
        output_dict['shunt_resistance'] = list()
        output_dict['signal_gen_tes_resistance'] = list()
        output_dict['close_loop_norm'] = list()
        output_dict['open_loop_preamp_norm'] = list()
        output_dict['open_loop_full_norm'] = list()


        
        # ====================
        # channels
        # ====================

        # channel list 
        nb_channels = 0
        if tes_channel_list is not None:
            nb_channels = len(tes_channel_list)
            output_dict['channel_type'] = 'tes'
            output_dict['channel_list'] = tes_channel_list
        elif detector_channel_list is not None:
            nb_channels = len(detector_channel_list)
            output_dict['channel_type'] = 'detector_channel'
            output_dict['channel_list'] = detector_channel_list
        elif (adc_id is not None and adc_channel_list is not None):
            nb_channels = len(adc_channel_list)
            output_dict['adc_name'] = adc_id
            output_dict['channel_type'] = 'adc'
            output_dict['channel_list'] = adc_channel_list
        else:
            raise ValueError('ERROR in control::read_all: No argument given!')



        
        # ====================
        # Loop channels and
        # get parameters
        # ====================
        
        # loop channels
        for ichan in range(nb_channels):

            # channel 
            tes_chan = None
            detector_chan = None
            adc_chan_id = None
            adc_chan = None
            
            if tes_channel_list is not None:
                tes_chan = tes_channel_list[ichan]
            elif detector_channel_list is not None:
                detector_chan = detector_channel_list[ichan]
            else:
                adc_chan_id = adc_id
                adc_chan = adc_channel_list[ichan]
            


            # loop TES parameters
            for param in param_list:
                val = nan
                #try:

                val = self._get_sensor_val(param, tes_channel=tes_chan,
                                           detector_channel=detector_chan, 
                                           adc_id=adc_chan_id, adc_channel=adc_chan)
                #except:
                #    print('WARNING in control::read_all: unable to get value for "' +  param)
                    

                if val == nan or val is None:
                    val = -999999


                # change units of some parameter:

                # uA -> A
                if param=='tes_bias' or param=='squid_bias':
                    val = val/1000000.0

                # mV -> V
                if param=='lock_point_voltage':
                    val = val/1000.0
                
                output_dict[param].append(val)  
            
                # wait
                time.sleep(0.1)
        
            # Signal generator
            sig_gen_dict = self.get_signal_gen_params(signal_gen_num=1, tes_channel=tes_chan,
                                                      detector_channel=detector_chan, 
                                                      adc_id=adc_chan_id, adc_channel=adc_chan)
          
            onoff = self.get_signal_gen_onoff(signal_gen_num=1, tes_channel=tes_chan,
                                              detector_channel=detector_chan, 
                                              adc_id=adc_chan_id, adc_channel=adc_chan)
            
            output_dict['signal_gen_voltage'].append(sig_gen_dict['voltage'])
            output_dict['signal_gen_current'].append(sig_gen_dict['current'])
            output_dict['signal_gen_frequency'].append(sig_gen_dict['frequency'])
            output_dict['signal_gen_shape'].append(sig_gen_dict['shape'])
            output_dict['signal_gen_phase_shift'].append(sig_gen_dict['phase_shift'])
            output_dict['signal_gen_source'].append(sig_gen_dict['source'])
            output_dict['signal_gen_onoff'].append(onoff)

                        
            # other parameter
            output_dict['feedback_resistance'].append(
                self.get_feedback_resistance(tes_channel=tes_chan, 
                                             detector_channel=detector_chan, 
                                             adc_id=adc_chan_id, adc_channel=adc_chan)
            )
            
            output_dict['close_loop_norm'].append(
                self.get_volts_to_amps_close_loop_norm(tes_channel=tes_chan, 
                                                       detector_channel=detector_chan, 
                                                       adc_id=adc_chan_id, adc_channel=adc_chan)
            )
            
            output_dict['open_loop_preamp_norm'].append(
                self.get_open_loop_preamp_norm(tes_channel=tes_chan, 
                                               detector_channel=detector_chan, 
                                               adc_id=adc_chan_id, adc_channel=adc_chan)
            )
            
            output_dict['open_loop_full_norm'].append(
                self.get_open_loop_full_norm(tes_channel=tes_chan, 
                                             detector_channel=detector_chan, 
                                             adc_id=adc_chan_id, adc_channel=adc_chan)
            )
            

            output_dict['squid_turn_ratio'].append(
                self.get_squid_turn_ratio(tes_channel=tes_chan, 
                                          detector_channel=detector_chan, 
                                          adc_id=adc_chan_id, adc_channel=adc_chan)
            )

            
            output_dict['shunt_resistance'].append(
                self.get_shunt_resistance(tes_channel=tes_chan, 
                                          detector_channel=detector_chan, 
                                          adc_id=adc_chan_id, adc_channel=adc_chan)
            )
            
            output_dict['signal_gen_tes_resistance'].append(self._config.get_signal_gen_tes_resistance())
            
        return output_dict
        
        



    def _get_sensor_val(self,param_name, 
                        tes_channel=None,
                        detector_channel= None,
                        adc_id=None, adc_channel=None):
        
        
        if not self._dummy_mode and self._squid_controller_name is None:
            print('ERROR: No SQUID controller, check config')
            return nan

        # get readout controller ID and Channel
        controller_id, controller_channel = (
            connection_utils.get_controller_info(self._connection_table,
                                                 tes_channel=tes_channel,
                                                 detector_channel=detector_channel,
                                                 adc_id=adc_id,
                                                 adc_channel=adc_channel)
        )

        param_val = nan
        if not self._read_from_redis:
          
            if self._squid_controller_name == 'feb':
                # CDMS FEB device
                
                feb_info = self._config.get_feb_subrack_slot(controller_id)
              
                subrack = int(feb_info[0])
                slot = int(feb_info[1])
            
                if self._debug:
                    print('INFO: Getting setting "' + param_name + '" from FEB')
                    print('(subrack = ' + str(subrack) + ', slot = ' + str(slot) + 
                          ', channel = ' + str(controller_channel) + ')')
                        
                if self._dummy_mode:
                    param_val= 1
                else:

                    if param_name == 'tes_bias':
                        param_val = self._readout_inst.get_phonon_qet_bias(subrack, slot, controller_channel)

                    elif param_name == 'squid_bias':
                        param_val = self._readout_inst.get_phonon_squid_bias(
                            subrack, slot, controller_channel
                        )

                    elif param_name == 'lock_point_voltage':
                        param_val = self._readout_inst.get_phonon_lock_point(
                            subrack, slot, controller_channel
                        )

                    elif param_name == 'preamp_gain':
                        param_val = self._readout_inst.get_phonon_preamp_gain(
                            subrack, slot, controller_channel
                        )

                    elif param_name == 'output_offset':
                        param_val = self._readout_inst.get_phonon_offset(
                            subrack, slot, controller_channel
                        )

                    elif param_name == 'output_gain':
                        param_val = self._readout_inst.get_phonon_output_gain(
                            subrack, slot, controller_channel
                        )

                    elif param_name == 'feedback_polarity':
                        is_inverted = self._readout_inst.get_phonon_feedback_polarity(
                            subrack, slot, controller_channel
                        )
                        param_val = 1
                        if is_inverted:
                            param_val = -1

                    elif param_name == 'feedback_mode':
                        is_open = self._readout_inst.is_phonon_feedback_open(
                            subrack, slot,controller_channel
                        )
                        if is_open:
                            param_val = 'open'
                        else:
                            param_val = 'close'
                            
                    elif param_name == 'signal_source':
                        is_preamp = self._readout_inst.is_phonon_source_preamp(
                            subrack, slot,controller_channel
                        )
                        if is_preamp:
                            param_val = 'preamp'
                        else:
                            param_val = 'feedback'

                    elif param_name == 'signal_gen_feedback_connection':
                        param_val = self._readout_inst.is_signal_generator_feedback_connected(
                            subrack, slot,controller_channel
                        )
                    

                    elif param_name == 'signal_gen_tes_connection':
                        param_val = self._readout_inst.is_signal_generator_tes_connected(
                            subrack, slot,controller_channel
                        )

                    else:
                        pass
                
            elif self._squid_controller_name == 'magnicon':

                if self._verbose:
                    print('INFO: Getting "' + param_name + ' for channel ' 
                          + str(controller_channel) + ' (Magnicon)')


                if not self._dummy_mode:
                    
                    if param_name == 'tes_bias':
                        param_val = self._readout_inst.get_tes_current_bias(controller_channel)

                    elif param_name == 'squid_bias':
                        param_val = self._readout_inst.get_squid_bias(controller_channel,'I')

                    elif param_name == 'lock_point_voltage':
                        param_val = self._readout_inst.get_squid_bias(controller_channel,'V')

                    elif param_name == 'feedback_gain':
                        param_val = self._readout_inst.get_GBP(controller_channel)

                    elif param_name == 'output_offset':
                        # No offset setting magnicon
                        param_val = 0
                        
                    elif param_name == 'output_gain':
                        # No output gain magnicon
                        param_val = 1
                        
                    elif param_name == 'preamp_gain':
                        amp, bw = self._readout_inst.get_amp_gain_bandwidth(controller_channel)
                        param_val = amp

                    elif param_name == 'preamp_bandwidth':
                        amp, bw = self._readout_inst.get_amp_gain_bandwidth(controller_channel)
                        param_val = bw
                        
                    elif param_name == 'feedback_polarity':
                        param_val = self._readout_inst.get_squid_gain_sign(controller_channel)

                    elif param_name == 'feedback_mode':
                        val = self._readout_inst.get_amp_or_fll(controller_channel)
                        if val=='AMP':
                            param_val = 'open'
                        elif val=='FLL':
                            param_val = 'close'
                        else:
                            param_val = val

                    elif param_name == 'signal_source':
                        val = self._readout_inst.get_amp_or_fll(controller_channel)
                        if val=='AMP':
                            param_val = 'preamp'
                        elif val=='FLL':
                            param_val = 'feedback'
                        else:
                            param_val = val

                    elif param_name == 'feedback_resistance':
                        param_val = self._readout_inst.get_feedback_resistor(controller_channel)

                    else:
                        pass
                else:
                    param_val= 1

            else:
                print('ERROR: Unknown SQUID controller "' + 
                      self._squid_controller_name + '"!')

        else:
            print('ERROR: Reading from redis N/A')

            
            
        return param_val


        
        
    def _set_sensor_val(self,param_name,value, 
                        tes_channel=None,
                        detector_channel= None,
                        adc_id=None,adc_channel=None):

        
        
        """
        TBD
        """

        if not self._dummy_mode and self._squid_controller_name is None:
            print('ERROR: No SQUID controller, check config')
            return nan
            
            

        # get readout controller ID and Channel
        controller_id, controller_channel = (
            connection_utils.get_controller_info(self._connection_table,
                                                 tes_channel=tes_channel,
                                                 detector_channel=detector_channel,
                                                 adc_id=adc_id, 
                                                 adc_channel=adc_channel)
        )
              
        # ================
        # Set value
        # ================
        
        readback_val = None

        if self._squid_controller_name == 'feb':
            # CDMS FEB device
            
            feb_info = self._config.get_feb_subrack_slot(controller_id)
            subrack = int(feb_info[0])
            slot = int(feb_info[1])
            
            if self._verbose or self._debug:
                print('INFO: Setting ' + param_name + ' to ' + str(value) + ' using FEB!')
            if self._debug:
                print('DEBUG: FEB - subrack = ' + str(subrack) + ', slot = ' + str(slot) + ', channel = ' + 
                      str(controller_channel))
                 
            if not self._dummy_mode:
                if param_name == 'tes_bias':
                    self._readout_inst.set_phonon_qet_bias(subrack, slot, controller_channel, value)
            
                elif param_name == 'squid_bias':
                    self._readout_inst.set_phonon_squid_bias(subrack, slot, controller_channel, value)
                
                elif param_name == 'lock_point_voltage':
                    self._readout_inst.set_phonon_lock_point(subrack, slot, controller_channel, value)
                
                elif param_name == 'preamp_gain':
                    self._readout_inst.set_phonon_preamp_gain(subrack, slot, controller_channel, value)
                
                elif param_name == 'output_offset':
                    self._readout_inst.set_phonon_offset(subrack, slot, controller_channel, value)
                
                elif param_name == 'output_gain':
                    self._readout_inst.set_phonon_output_gain(subrack, slot, controller_channel, value)
                
                elif param_name == 'feedback_polarity':
                    do_invert = False
                    if val==-1:
                        do_invert = True
                    self._readout_inst.set_phonon_feedback_polarity(
                        subrack, slot, controller_channel, do_invert
                    )
            
                elif param_name == 'feedback_mode':
                    do_open = False
                    if value == 'open':
                        do_open = True
                    self._readout_inst.set_phonon_feedback_loop(subrack, slot, controller_channel, do_open)
                
                elif param_name == 'preamp_source':
                    self._readout_inst.set_phonon_source_preamp(subrack, slot, controller_channel, value)
                
                elif param_name == 'signal_gen_feedback_connection':
                    self._readout_inst.connect_signal_generator_feedback(
                        subrack, slot, controller_channel, value
                    )
                
                elif param_name == 'signal_gen_tes_connection':
                    self._readout_inst.connect_signal_generator_tes(subrack, slot, controller_channel, value)
                           

        elif self._squid_controller_name == 'magnicon':
            
            if self._verbose or self._debug:
                print('INFO: Setting "' + param_name + '" to ' + str(value) + ' for channel ' 
                      + str(controller_channel) + ' (Magnicon)!')

            if not self._dummy_mode:
                
                if param_name == 'tes_bias':
                    readback_val = self._readout_inst.set_tes_current_bias(
                        controller_channel, value, mode=None
                    )
                
                elif param_name == 'squid_bias':
                    readback_val = self._readout_inst.set_squid_bias(controller_channel, 'I', value)
                
                elif param_name == 'lock_point_voltage':
                    readback_val = self._readout_inst.set_squid_bias(controller_channel, 'V', value)
                
                elif param_name == 'feedback_gain':
                    readback_val = self._readout_inst.set_GBP(controller_channel, value)
                    
                elif param_name == 'feedback_polarity':
                    readback_val = self._readout_inst.set_squid_gain_sign(controller_channel, value)
                
                elif param_name == 'preamp_gain':
                    if isinstance(value,tuple) and len(value)==2:
                        amp, bw = self._readout_inst.set_amp_gain_bandwidth(
                            controller_channel, value[0], value[1]
                        )
                        readback_val = (amp,bw)
                    else:
                        print('WARNING: a tuple with (amplitude, bandwidth) required for magnicon preamp setting')

                elif param_name == 'feedback_mode':
                    mode = 'AMP'
                    if value=='close':
                        mode='FLL'
                    readback_val = self._readout_inst.set_amp_or_fll(controller_channel, mode)


        else:
            print('ERROR: Unknow SQUID controller "' + 
                  self._squid_controller_name + '"!')
        
    
        # ================
        # Read back
        # ================
        time.sleep(0.2)

        if  self._enable_readback and not self._dummy_mode:

            # FEB
            if self._squid_controller_name == 'feb':
                readback_val= self._get_sensor_val(param_name,
                                                   tes_channel=tes_channel,
                                                   detector_channel=detector_channel,
                                                   adc_id=adc_id, adc_channel=adc_channel)
             
            
            if self._verbose:
                print('INFO: Parameter ' + param_name)
                print('Value set = ' + str(value))
                print('Value readback = ' + str(value_readback))
        
        
        # ================
        # Redis
        # ================
        time.sleep(0.2)
        if self._enable_redis:
            hash_name = param_name
            hash_key  = controller_id + '/' + controller_channel
            hash_val =  value
            if self._enable_readback:
                hash_val = value_readback
            
            try:
                self._redis_db.add_hash(hash_name, hash_key, hash_val)
            except:
                print('ERROR adding value in redis!')
            
            


    
    
        
    def get_temperature_controllers_table(self, channel_type=None):
        """
        Get temperature controller channel table 
        """
        tables = list()
        for name, inst in self._temperature_controller_insts.items():
            instrument_table = inst.get_channel_table(channel_type=channel_type)
            if instrument_table is not None:
                tables.append(instrument_table)

        channel_table = None
        if tables:
             channel_table = pd.concat(tables)


        return channel_table

        

    def get_temperature_controller(self, channel_name=None,
                                   global_channel_number=None,
                                   instrument_name=None,
                                   channel_type=None):
        """
        Get temperature controller
        """

        # check input
        if instrument_name is None and channel_name is None and global_channel_number is None:
            raise ValueError('ERROR: Missing channel name, global number, or instrument name')
    

        # get instrument name
        instrument = None
        if instrument_name is None:

            # get channel table
            channel_table = self.get_temperature_controllers_table(channel_type=channel_type)

            # query instrument name
            if channel_name is not None:
                query_string = 'channel_name == @channel_name'
            else:
                query_string = 'global_channel_number == @global_channel_number'
            instrument_name = channel_table.query(query_string)['instrument_name'].values

            # check if found unique name
            if len(instrument_name)>1:
                raise ValueError('ERROR: Multiple instruments found for same channel')
            elif len(instrument_name)==1:
                instrument_name = instrument_name[0]
            else:
                raise ValueError('ERROR: No instrument find for input channel!')
            
        # get instrument
        if instrument_name in self._temperature_controller_insts:
            instrument = self._temperature_controller_insts[instrument_name]
        else:
            raise ValueError('ERROR: Unknown temperature controller "' +
                             instrument_name + '"!')
 
        return instrument

    
        
    def get_temperature(self, channel_name=None,
                        global_channel_number=None,
                        instrument_name=None):
        
        """
        Get temperature from thermometer [mK]
        
        """
        
        # find instrument
        inst = self.get_temperature_controller(channel_name=channel_name,
                                               global_channel_number=global_channel_number,
                                               instrument_name=instrument_name,
                                               channel_type='resistance')
        
        # get temperature
        temperature = inst.get_temperature(channel_name=channel_name,
                                          global_channel_number=global_channel_number)

       
        return temperature
         

          

    
    def get_resistance(self, channel_name=None,
                       global_channel_number=None,
                       instrument_name=None):
        
        """
        Get resistance from thermometer [Ohms]
        """

        # find instrument
        inst = self.get_temperature_controller(channel_name=channel_name,
                                               global_channel_number=global_channel_number,
                                               instrument_name=instrument_name,
                                               channel_type='resistance')
        
        
        resistance = inst.get_resistance(channel_name=channel_name,
                                         global_channel_number=global_channel_number)

       
        return resistance
         


    
    def set_temperature(self, temperature,
                        channel_name=None,
                        global_channel_number=None,
                        heater_channel_name=None,
                        heater_global_channel_number=None,
                        instrument_name=None,
                        wait_temperature_reached=False,
                        wait_cycle_time=30,
                        wait_stable_time=300,
                        max_wait_time=1200,
                        tolerance=0.2):
        
        """
        Set temperature
        """

        # find instrument
        inst = self.get_temperature_controller(channel_name=channel_name,
                                               global_channel_number=global_channel_number,
                                               instrument_name=instrument_name,
                                               channel_type='resistance')

        # set temperature
        inst.set_temperature(temperature,
                             channel_name=channel_name,
                             global_channel_number=global_channel_number,
                             heater_channel_name=heater_channel_name,
                             heater_global_channel_number=heater_global_channel_number,
                             wait_temperature_reached=wait_temperature_reached,
                             wait_cycle_time=wait_cycle_time,
                             wait_stable_time=wait_stable_time,
                             max_wait_time=max_wait_time,
                             tolerance=tolerance)
        
        
        
        

    def _connect_instruments(self):
        """
        Connect instruments
        """


        if self._dummy_mode:
            print('WARNING: Dummy mode enabled. Not connecting instruments!')
            return


        # visa library
        visa_library = self._config.get_visa_library()
        
        # ----------
        # CDMS FEB
        # ----------
        if self._squid_controller_name == 'feb':
            address = self._config.get_feb_address()
            if address:
                if self._verbose:
                    print('INFO: Instantiating FEB using address: ' + address)
                self._readout_inst = FEB(address,
                                         visa_library=visa_library,
                                         verbose=self._verbose, raise_errors=self._raise_errors)
            else:
                raise ValueError('Unable to find GPIB address. It will not work!')

        # ----------
        # Magnicon
        # ----------
        if (self._squid_controller_name == 'magnicon' or self._signal_generator_name == 'magnicon'):
            mag_control_info = self._config.get_magnicon_controller_info()
            mag_conn_info = self._config.get_magnicon_connection_info()
            magnicon_inst = Magnicon(channel_list=mag_control_info['channel_list'],
                                     default_active=mag_control_info['default_active'],
                                     reset_active=mag_control_info['reset_active'],
                                     conn_info=mag_conn_info)
            
            magnicon_inst.set_remote_inst()
            magnicon_inst.connect()
            magnicon_inst.chdir()
            magnicon_inst.listen_for(None)

            # verbose
            if self._verbose:
                if mag_conn_info:
                    print('SSH connection info for Magnicon:')
                    print('Hostname:', mag_conn_info['hostname'])
                    print('Username:', mag_conn_info['username'])
                    print('Port:', str(mag_conn_info['port']))
                    print('RSA key:', mag_conn_info['rsa_key'])
                    print('Log file:', mag_conn_info['log_file'])
                    print('Executable location:', mag_conn_info['exe_location'])
                if mag_control_info:
                    print('Controller info for Magnicon:')
                    print('Channel list:', str(mag_control_info['channel_list']))
                    print('Default active channel:', str(mag_control_info['default_active']))
                    print('Reset active channel after every step:', str(mag_control_info['reset_active']))
   

            if self._squid_controller_name == 'magnicon':
                self._readout_inst = magnicon_inst

            if self._signal_generator_name == 'magnicon':
                self._signal_generator_inst = magnicon_inst
                    
        # ----------------
        # Signal Generator
        # ----------------
        if self._signal_generator_name == 'keysight':
            address = self._config.get_signal_generator_visa_address('keysight')
            self._signal_generator_inst = (
                KeysightFuncGenerator(address,
                                      visa_library=visa_library,
                                      verbose=self._verbose,
                                      raise_errors=self._raise_errors)
            )


            
        # ----------------
        # Temperature controllers
        # ----------------
        self._temperature_controller_insts = dict()
        
        # loop controllers
        for controller_name in self._temperature_controller_name_list:

            if self._verbose:
                print('INFO: Connecting ' + controller_name)
            
            # lakeshore
            inst = None
            if controller_name.find('lakeshore')!=-1:
                inst = Lakeshore(instrument_name=controller_name)
            elif controller_name=='macrt':
                inst = MACRT()

            if inst == None:
                raise ValueError('ERROR: Only lakeshore and MACRT available')
    
                
            inst.setup_instrument_from_config(setup_file=self._setup_file)
            self._temperature_controller_insts[controller_name] = inst

            # connect (lakeshore only)
            if controller_name.find('lakeshore')!=-1:
                inst.connect()


            
    def _disconnect_instruments(self):
        """
        Disconnect instruments
        """
        return
