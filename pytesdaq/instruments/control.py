"""
Main instrumentation class

"""
import time
import numpy
import pytesdaq.config.settings as settings
import pytesdaq.instruments.feb  as feb
import pytesdaq.instruments.magnicon as magnicon
import pytesdaq.io.redis as redis
from pytesdaq.utils import connection_utils
import pytesdaq.utils.remote as remote
from math import nan


class Control:
    """
    Control TES related instruments
    """
    
    def __init__(self,verbose=True, dummy_mode = True):
        
        # for code development
        self._dummy_mode = dummy_mode
        self._verbose = verbose

        # initialize
        self._config = settings.Config()
        self._squid_controller = self._config.get_squid_controller()
        self._signal_generator = self._config.get_signal_generator()
        self._temperature_controller = self._config.get_temperature_controller()

        # redis
        self._enable_redis = self._config.enable_redis()
        self._read_from_redis = False
        if self._enable_redis:
             self._redis_db = redis.RedisCore()
             self._redis_db.connect()
              
        # readback
        self._enable_readback = self._config.enable_redis()

        # instantiate / check instruments

        # FEB
        if self._squid_controller == 'feb' and not self._dummy_mode:
            address = self._config.get_feb_address()
            if address:
                if self._verbose:
                    print('FEB address: ' + address)
                self._feb_inst = feb.FEB(address)
            else:
                print('ERROR: Unable to find GPIB address')

    	# Magnicon
        if self._squid_controller == 'magnicon' and not self._dummy_mode:
            mag_control_info = self._config.get_magnicon_controller_info()
            mag_conn_info = self._config.get_magnicon_connection_info()
            self._mag_inst = magnicon.Magnicon(channel_list=mag_control_info['channel_list'],
                                               default_active=mag_control_info['default_active'],
                                               reset_active=mag_control_info['reset_active'],
                                               conn_info=mag_conn_info)
            self._mag_inst.set_remote_inst()
            self._mag_inst.connect()
            self._mag_inst.chdir()
            self._mag_inst.listen_for(None)
            if mag_conn_info:
                if self._verbose:
                    print('SSH connection info for Magnicon:')
                    print('Hostname:', mag_conn_info['hostname'])
                    print('Username:', mag_conn_info['username'])
                    print('Port:', str(mag_conn_info['port']))
                    print('RSA key:', mag_conn_info['rsa_key'])
                    print('Log file:', mag_conn_info['log_file'])
                    print('Executable location:', mag_conn_info['exe_location'])
            if mag_control_info:
                if self._verbose:
                    print('Controller info for Magnicon:')
                    print('Channel list:', str(mag_control_info['channel_list']))
                    print('Default active channel:', str(mag_control_info['default_active']))
                    print('Reset active channel after every step:', str(mag_control_info['reset_active']))

        # get connection map
        self._connection_table= self._config.get_adc_connections()



    @property
    def verbose(self):
        return self._verbose
        
    @verbose.setter
    def verbose(self,value):
        self._verbose=value
        
    @property
    def read_from_redis(self):
        return self._read_from_redis
        
    @read_from_redis.setter
    def read_from_redis(self,value):
        if value and not self._enable_redis:
            print('WARNING: unable to read from Redis! Redis DB not enabled...)')
        else:
            self._read_from_redis=value
        


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
    



    def set_squid_lock_point(self, lock_point, 
                             tes_channel=None,
                             detector_channel=None,
                             adc_id=None, adc_channel=None):
        

        """
        Set SQUID lock point
        """
        try:
            self._set_sensor_val('lock_point_voltage', bias,
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
        Set Feedback gain (magnicon: gain-bw product)
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
            self._set_sensor_val('output_offset',offset,
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
            self._set_sensor_val('output_gain',gain,
                                 tes_channel=tes_channel,
                                 detector_channel=detector_channel,
                                 adc_id=adc_id, adc_channel=adc_channel)
        except:
            print('ERROR setting output gain')
            return False

        return True  
            


    def set_preamp_polarity(self, val,
                              tes_channel=None,
                              detector_channel=None,
                              adc_id=None, adc_channel=None):


        """
        Set preamp gain polarity
        positive = +1
        negative = -1
        error = 0
        """
        try:
            self._set_sensor_val('preamp_polarity',val,
                                 tes_channel=tes_channel,
                                 detector_channel=detector_channel,
                                 adc_id=adc_id, adc_channel=adc_channel)
        except:
            print('ERROR setting preamp polarity')
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
            self._set_sensor_val('feedback_polarity',val,
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


    def set_signal_source(self, source, 
                          tes_channel=None,
                          detector_channel=None,
                          adc_id=None, adc_channel=None):
        

        """
        Set readout source ('preamp' or 'feedback') 
        """

        

        try:
            self._set_sensor_val('signal_source',source,
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
        
        
        # get readout controller ID and Channel (FIXME: Is it necessary)
        controller_id, controller_channel = connection_utils.get_controller_info(self._connection_table,
                                                                                 tes_channel=tes_channel,
                                                                                 detector_channel=detector_channel,
                                                                                 adc_id=adc_id,
                                                                                 adc_channel=adc_channel)
        

        if self._squid_controller=='magnicon':

            mon_onoff = 'OFF'
            gen1_onoff = 'OFF'
            gen2_onoff = 'OFF'
            if signal_gen_num==1:
                gen1_onoff = on_off_flag.upper()
            else:
                gen2_onoff = on_off_flag.upper()


            rb_onoff1, rb_onoff, rb_mon_onoff = self._mag_inst.set_generator_onoff(controller_channel, 
                                                                    gen1_onoff, gen2_onoff, mon_onoff)
                

    
        

    
    def set_signal_gen_params(self, tes_channel=None,
                              detector_channel=None,
                              adc_id=None, adc_channel=None,
                              signal_gen_num=1, 
                              source=None, amplitude=None, frequency=100,
                              shape='square', phase_shift=0, freq_div=0, half_pp_offset='OFF'):

        """
        Set signal generator parameters

        source:  'tes' or 'feedback' (required)
        amplitude: peak-to-peak amplitude, magnicon [uA], Keysight [mV]
        frequency: Float [Hz] (Default = 100 Hz)
        shape: 'triangle', 'sawtoothpos', 'sawtoothneg', 'square', 'sine', 'noise'
        """
        
        


        # check parameters
        if source is None or amplitude is None:
            print('ERROR: Required parameters = "source" and "amplitude"')
            return

        if source!='tes' and source!='feedback':
            print('ERROR: Source can be either "tes" or "feedback"')
            
        # get readout controller ID and Channel
        controller_id, controller_channel = connection_utils.get_controller_info(self._connection_table,
                                                                                 tes_channel=tes_channel,
                                                                                 detector_channel=detector_channel,
                                                                                 adc_id=adc_id,
                                                                                 adc_channel=adc_channel)
        
        

        
        if self._dummy_mode:
            print('INFO: Setting signal generator #' + str(signal_gen_num) + ', ' + 
                   controller_id + ' channel ' + str(controller_channel))
            return



        # initialize readback values
        readback_amp = nan
        readback_freq = nan

        # magnicon
        if self._squid_controller=='magnicon':
            
            # convert some parameters
            source_magnicon = 'I'
            if source!='feedback':
                source_magnicon = 'Ib'

            readback_amp, readback_freq = self.mag_inst.set_generator_params(controller_channel,signal_gen_num, 
                                                                             frequency, source, shape, 
                                                                             phase_shift, freq_div, half_pp_offset, 
                                                                             amplitude)



    def set_squid_dummy(self, val,
                        tes_channel=None,
                        detector_channel=None,
                        adc_id=None, adc_channel=None):

        """
        Set status of SQUID electronics in the dummy state (Magnicon)
        The val must be 'OFF' or 'ON' (case-insensitive)
        Note: this is independent of whether pytesdaq is in the dummy state.
        """

        try:
            self._set_sensor_val('squid_dummy', val.upper(),
                                 tes_channel=tes_channel,
                                 detector_channel=detector_channel,
                                 adc_id=adc_id, adc_channel=adc_channel)
        except:
            print('ERROR setting SQUID dummy status')
            return False

        return True



    def set_flux_bias_disconnect(self, val,
                                 tes_channel=None,
                                 detector_channel=None,
                                 adc_id=None, adc_channel=None):

        """
        Set status of SQUID electronics in the dummy state (Magnicon)
        The val must be 'DISCONNECTED' or 'CONNECTED' (case-insensitive)
        """

        try:
            self._set_sensor_val('flux_bias_disconnect', val.upper(),
                                 tes_channel=tes_channel,
                                 detector_channel=detector_channel,
                                 adc_id=adc_id, adc_channel=adc_channel)
        except:
            print('ERROR setting flux bias connection status')
            return False

        return True



    def set_output_coupling(self, val,
                            tes_channel=None,
                            detector_channel=None,
                            adc_id=None, adc_channel=None):

        """
        Set output coupling (Magnicon). Must be 'AC' or 'DC' (case-insensitive).
        """

        try:
            self._set_sensor_val('output_coupling', val.upper(),
                                 tes_channel=tes_channel,
                                 detector_channel=detector_channel,
                                 adc_id=adc_id, adc_channel=adc_channel)
        except:
            print('ERROR setting output coupling')
            return False

        return True



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
            self._set_sensor_val('signal_gen_tes_connection',bool(do_connect),
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
        try:
            bias = self._get_sensor_val('tes_bias',
                                        tes_channel=tes_channel,
                                        detector_channel=detector_channel,
                                        adc_id=adc_id, adc_channel=adc_channel)
            
        except:
            print('ERROR getting TES bias')
            
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
        Get lock point 
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
        Get preamp gain
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


        


    def get_preamp_polarity(self,
                            tes_channel=None,
                            detector_channel=None,
                            adc_id=None, adc_channel=None):

        """
        Get preamp gain polarity
        """
        preamp_polarity = nan
        try:
            preamp_polarity = self._get_sensor_val('preamp_polarity',
                                                   tes_channel=tes_channel,
                                                   detector_channel=detector_channel,
                                                   adc_id=adc_id, adc_channel=adc_channel)

        except:
            print('ERROR getting preamp polarity')


        return preamp_polarity



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
        if self._squid_controller == 'magnicon':
            gen1_onoff, gen2_onoff, mon_onoff = self._mag_inst.get_generator_onoff(controller_channel)
            if signal_gen_num == 1:
                val = gen1_onoff.lower()
            else:
                val = gen2_onoff.lower()


            

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
        if val=='on':
            val_bool = True
        elif  val=='off':
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
                
      
        # get readout controller ID and Channel
        controller_id, controller_channel = connection_utils.get_controller_info(self._connection_table,
                                                                                 tes_channel=tes_channel,
                                                                                 detector_channel=detector_channel,
                                                                                 adc_id=adc_id,
                                                                                 adc_channel=adc_channel)
        
        
        # initialize dictionay
        output_dict = dict()
        output_dict['source']=nan
        output_dict['amplitude']= nan
        output_dict['frequency']= nan
        output_dict['shape']= nan
        output_dict['phase_shift']= nan
        output_dict['freq_div']= nan
        output_dict['half_pp_offset'] = nan
       

        if self._dummy_mode:
            print('INFO: Getting signal generator #' + str(signal_gen_num) + ', ' + 
                   controller_id + ' channel ' + str(controller_channel))
            return output_dict



        # magnicon
        if self._squid_controller=='magnicon':

            # convert some parameters
            source_magnicon = 'I'
           

            source,shape,freq,freq_div,shift,amp,offset = self.mag_inst.get_generator_params(controller_channel,
                                                                                             signal_gen_num)

            # fill dictionary
            if source=='I':
                output_dict['source'] = 'tes'
            elif source=='Ib':
                output_dict['source'] = 'feedback'
            else:
                output_dict['source'] = source

            output_dict['amplitude']= amp
            output_dict['frequency']= freq
            output_dict['shape']= shape
            output_dict['phase_shift']= shift
            output_dict['freq_div']= freq_div
            output_dict['half_pp_offset'] = offset
                         
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
            



    def get_feedback_resistance(self,tes_channel=None,
                                detector_channel=None,
                                adc_id=None, adc_channel=None):
        """
        Get feedback resistance (magnicon)
        """
        
        feedback_resistance = nan
        
        try:
            feedback_resistance = self._get_sensor_val('feedback_resistance',
                                                     tes_channel=tes_channel,
                                                     detector_channel=detector_channel,
                                                     adc_id=adc_id, adc_channel=adc_channel)
        except:
            print('ERROR getting feedback resistance')


        # if needed get it from config file
        if feedback_resistance==nan:
            feedback_resistance = self._config.get_feedback_resistance()


            
        return feedback_resistance





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
      
        if feedback_resistance==nan or feedback_resistance is None:
            print('ERROR: unable to find feedback resistance. It needs to be added in setup.ini file!')
            return None
        
        
        # squid loop turn ratio
        squid_turn_ratio = self._config.get_squid_turn_ratio()
        if squid_turn_ratio is None:
            print('ERROR: unable to find SQUID turn ratio. It needs to be added in setup.ini file!')
            return None


        # calculate normalization
        norm = output_total_gain*feedback_resistance*squid_turn_ratio
        return norm





    def get_open_loop_norm(self, tes_channel=None,
                           detector_channel=None,
                           adc_id=None, adc_channel=None):
        """
        get open loop normalization 
        
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
        


    def get_squid_dummy(self,tes_channel=None,
                                detector_channel=None,
                                adc_id=None, adc_channel=None):
        """
        Get status of SQUID electronics in the dummy state (Magnicon)
        Returns on, off, or fail.
        Note: this is independent of whether pytesdaq is in the dummy state.
        """

        squid_dummy = ''

        try:
            squid_dummy = self._get_sensor_val('squid_dummy',
                                               tes_channel=tes_channel,
                                               detector_channel=detector_channel,
                                               adc_id=adc_id, adc_channel=adc_channel)
        except:
            print('ERROR getting SQUID dummy')

        return squid_dummy.lower()



    def get_flux_bias_disconnect(self,tes_channel=None,
                                 detector_channel=None,
                                 adc_id=None, adc_channel=None):
        """
        Get status of flux bias connection (Magnicon)
        Returns 'CONNECTED', 'DISCONNECTED', or 'FAIL'.
        """

        flux_bias_disconnect = ''

        try:
            flux_bias_disconnect = self._get_sensor_val('flux_bias_disconnect',
                                               tes_channel=tes_channel,
                                               detector_channel=detector_channel,
                                               adc_id=adc_id, adc_channel=adc_channel)
        except:
            print('ERROR getting flux bias disconnect')

        return flux_bias_disconnect.upper()



    def get_output_coupling(self,tes_channel=None,
                                 detector_channel=None,
                                 adc_id=None, adc_channel=None):
        """
        Get output coupling. Returns 'AC', 'DC', or 'FAIL'.
        """

        coupling = ''

        try:
            coupling = self._get_sensor_val('output coupling',
                                            tes_channel=tes_channel,
                                            detector_channel=detector_channel,
                                            adc_id=adc_id, adc_channel=adc_channel)
        except:
            print('ERROR getting output coupling')

        return coupling.upper()



    def read_all(self, tes_channel_list=None, detector_channel_list= None,
                 adc_id=None,adc_channel_list=None):
        """
        Read from baord all parameters
        Output in a dictionary: dict['param'] = array values (index based
          on input list)
        
        """


        # intialize output
        output_dict = dict()
        
        # TES parameter list
        param_list = ['tes_bias','squid_bias','lock_point_voltage','output_offset',
                      'output_gain','feedback_polarity','feedback_mode',
                      'signal_source']
                      


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

       
        # intialize output
        for param in param_list:
            output_dict[param] = list()
            
        output_dict['signal_gen_amplitude'] = list()
        output_dict['signal_gen_frequency'] = list()
        output_dict['signal_gen_shape'] = list()
        output_dict['signal_gen_phase_shift'] = list()
        output_dict['signal_gen_source'] = list()
        output_dict['signal_gen_onoff'] = list()
        output_dict['feedback_resistance'] =  list()
        output_dict['squid_turn_ratio'] = list()
        #output_dict['shunt_resistance'] = list()
        output_dict['close_loop_norm'] = list()
        output_dict['open_loop_norm'] = list()

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
                try:
                    val = self._get_sensor_val(param, tes_channel=tes_chan, detector_channel=detector_chan, 
                                               adc_id=adc_chan_id, adc_channel=adc_chan)
                except:
                    print('WARNING in control::read_all: unable to get value for "' +  param 
                          + '" (' + str(channel_type) + ' = ' +  str(chan) + ')')
                    

                if val==nan or val is None:
                    val = -999999
                output_dict[param].append(val)  
            
                # wait
                time.sleep(0.1)
        
            # Signal generator
            sig_gen_dict = self.get_signal_gen_params(signal_gen_num=1, tes_channel=tes_chan, detector_channel=detector_chan, 
                                                      adc_id=adc_chan_id, adc_channel=adc_chan)

            onoff = self.get_signal_gen_onoff(signal_gen_num=1, tes_channel=tes_chan, detector_channel=detector_chan, 
                                              adc_id=adc_chan_id, adc_channel=adc_chan)
            

            output_dict['signal_gen_amplitude'].append(sig_gen_dict['amplitude'])
            output_dict['signal_gen_frequency'].append(sig_gen_dict['frequency'])
            output_dict['signal_gen_shape'].append(sig_gen_dict['shape'])
            output_dict['signal_gen_phase_shift'].append(sig_gen_dict['phase_shift'])
            output_dict['signal_gen_source'].append(sig_gen_dict['source'])
            output_dict['signal_gen_onoff'].append(onoff)
            

            
            # other parameter
            output_dict['feedback_resistance'].append(self.get_feedback_resistance(tes_channel=tes_chan, 
                                                                                   detector_channel=detector_chan, 
                                                                                   adc_id=adc_chan_id, adc_channel=adc_chan))

            output_dict['close_loop_norm'].append(self.get_volts_to_amps_close_loop_norm(tes_channel=tes_chan, 
                                                                                         detector_channel=detector_chan, 
                                                                                         adc_id=adc_chan_id, adc_channel=adc_chan))
            output_dict['open_loop_norm'].append(self.get_open_loop_norm(tes_channel=tes_chan, 
                                                                         detector_channel=detector_chan, 
                                                                         adc_id=adc_chan_id, adc_channel=adc_chan))
   

            output_dict['squid_turn_ratio'].append(self._config.get_squid_turn_ratio())
            #output_dict['shunt_resistance'].append(self._config.get_shunt_resistance())
            


        return output_dict
        
        



    def _get_sensor_val(self,param_name, 
                        tes_channel=None,
                        detector_channel= None,
                        adc_id=None, adc_channel=None):
        
        

        if not self._dummy_mode and not self.squid_controller:
            print('ERROR: No SQUID controller, check config')
            return nan
            
      
        # get readout controller ID and Channel
        controller_id, controller_channel = connection_utils.get_controller_info(self._connection_table,
                                                                                 tes_channel=tes_channel,
                                                                                 detector_channel=detector_channel,
                                                                                 adc_id=adc_id,
                                                                                 adc_channel=adc_channel)
        

        param_val = nan
        
        if not self._read_from_redis:

            if self._squid_controller=='feb':
                # CDMS FEB device
                
                feb_info = self._config.get_feb_subrack_slot(controller_id)
                subrack = int(feb_info[0])
                slot = int(feb_info[1])
            
                if self._verbose:
                    print('INFO: Getting setting "' + param_name + '" from FEB')
                    print('(subrack = ' + str(subrack) + ', slot = ' + str(slot) + 
                          ', channel = ' + str(controller_channel) + ')')
                
                if not self._dummy_mode:

                    if param_name == 'tes_bias':
                        param_val = self._feb_inst.get_phonon_qet_bias(subrack, slot,controller_channel)

                    elif param_name == 'squid_bias':
                        param_val = self._feb_inst.get_phonon_squid_bias(subrack, slot,controller_channel)

                    elif param_name == 'lock_point_voltage':
                        param_val = self._feb_inst.get_phonon_lock_point(subrack, slot,controller_channel)

                    elif param_name == 'preamp_gain':
                        param_val = self._feb_inst.get_phonon_preamp_gain(subrack, slot,controller_channel)

                    elif param_name == 'output_offset':
                        param_val = self._feb_inst.get_phonon_offset(subrack, slot,controller_channel)

                    elif param_name == 'output_gain':
                        param_val = self._feb_inst.get_phonon_output_gain(subrack, slot,controller_channel)

                    elif param_name == 'feedback_polarity':
                        is_inverted = self._feb_inst.get_phonon_feedback_polarity(subrack, slot,controller_channel)
                        param_val = 1
                        if is_inverted:
                            param_val = -1

                    elif param_name == 'feedback_mode':
                        is_open = self._feb_inst.is_phonon_feedback_open(subrack, slot,controller_channel)
                        if is_open:
                            param_val = 'open'
                        else:
                            param_val = 'close'
                            
                    elif param_name == 'signal_source':
                        is_preamp = self._feb_inst.is_phonon_source_preamp(subrack, slot,controller_channel)
                        if is_preamp:
                            param_val = 'preamp'
                        else:
                            param_val = 'feedback'

                    elif param_name == 'signal_gen_feedback_connection':
                        param_val = self._feb_inst.is_signal_generator_feedback_connected(subrack, slot,controller_channel)
                    elif param_name == 'signal_gen_tes_connection':
                        param_val = self._feb_inst.is_signal_generator_tes_connected(subrack, slot,controller_channel)

                    else:
                        pass
                else:
                    param_val= 1

            elif self._squid_controller=='magnicon':

                if self._verbose:
                    print('INFO: Getting "' + param_name + ' for channel ' 
                          + str(controller_channel) + ' (Magnicon)')


                if not self._dummy_mode:
                    
                    if param_name == 'tes_bias':
                        param_val = self._mag_inst.get_tes_current_bias(controller_channel)
                    
                    elif param_name == 'squid_bias':
                        param_val = self._mag_inst.get_squid_bias(controller_channel,'I')

                    elif param_name == 'lock_point_voltage':
                        param_val = self._mag_inst.get_squid_bias(controller_channel,'V')

                    elif param_name == 'feedback_gain':
                        param_val = self._mag_inst.get_GBP(controller_channel)
               
                    elif param_name == 'preamp_gain':
                        amp, bw = self._mag_inst.get_amp_gain_bandwidth(controller_channel)
                        param_val = amp

                    elif param_name == 'preamp_bandwidth':
                        amp, bw = self._mag_inst.get_amp_gain_bandwidth(controller_channel)
                        param_val = bw

                    elif param_name == 'preamp_polarity':
                        param_val = self._mag_inst.get_amp_gain_sign(controller_channel)
                        
                    elif param_name == 'feedback_polarity':
                        param_val = self.mag_inst.get_squid_gain_sign(controller_channel)

                    elif param_name == 'feedback_mode':
                        val = self.mag_inst.get_amp_or_fll(controller_channel)
                        if val=='AMP':
                            param_val = 'open'
                        elif val=='FLL':
                            param_val = 'close'
                        else:
                            param_val = val
                     
                    elif param_name == 'feedback_resistance':
                        param_val = self.mag_inst.get_feedback_resistor(controller_channel)

                    elif param_name == 'squid_dummy':
                        param_val = self._mag_inst.get_dummy(controller_channel)

                    elif param_name == 'flux_bias_disconnect':
                        param_val = self._mag_inst.get_flux_bias_disconnect(controller_channel)

                    elif param_name == 'output_coupling':
                        param_val = self._mag_inst.get_output_coupling(controller_channel)

                    else:
                        pass
                else:
                    param_val= 1

            else:
                print('ERROR: Unknown SQUID controller "' + 
                      self._squid_controller + '"!')

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

        if not self._dummy_mode and not self.squid_controller:
            print('ERROR: No SQUID controller, check config')
            return nan
            
            

        # get readout controller ID and Channel
        controller_id, controller_channel = connection_utils.get_controller_info(self._connection_table,
                                                                                tes_channel=tes_channel,
                                                                                detector_channel=detector_channel,
                                                                                adc_id=adc_id, 
                                                                                adc_channel=adc_channel)
      
              
        # ================
        # Set value
        # ================
        
        readback_val = None

        if self._squid_controller=='feb':
            # CDMS FEB device
            
            feb_info = self._config.get_feb_subrack_slot(controller_id)
            subrack = int(feb_info[0])
            slot = int(feb_info[1])
            
            if self._verbose:
                print('INFO: Setting ' + param_name + ' to ' + str(value) + ' using FEB:')
                print('subrack = ' + str(subrack) + ', slot = ' + str(slot) + ', channel = ' + 
                      str(controller_channel))
                 
            if not self._dummy_mode:
                if param_name == 'tes_bias':
                    self._feb_inst.set_phonon_qet_bias(subrack, slot,controller_channel,value)
            
                elif param_name == 'squid_bias':
                    self._feb_inst.set_phonon_squid_bias(subrack, slot,controller_channel,value)
                
                elif param_name == 'lock_point_voltage':
                    self._feb_inst.set_phonon_lock_point(subrack, slot,controller_channel,value)
                
                elif param_name == 'feedback_gain':
                    self._feb_inst.set_phonon_feedback_gain(subrack, slot,controller_channel,value)
                
                elif param_name == 'output_offset':
                    self._feb_inst.set_phonon_offset(subrack, slot,controller_channel,value)
                
                elif param_name == 'output_gain':
                    self._feb_inst.set_phonon_output_gain(subrack, slot,controller_channel,value)
                
                elif param_name == 'feedback_polarity':
                    do_invert = False
                    if val==-1:
                        do_invert = True
                    self._feb_inst.set_phonon_feedback_polarity(subrack, slot,controller_channel,do_invert)
            
                elif param_name == 'feedback_mode':
                    self._feb_inst.set_phonon_feedback_loop(subrack, slot,controller_channel,value)
                
                elif param_name == 'preamp_source':
                    self._feb_inst.set_phonon_source_preamp(subrack, slot,controller_channel,value)
                
                elif param_name == 'signal_gen_feedback_connected':
                    self._feb_inst.connect_signal_generator_feedback(subrack, slot,controller_channel,value)
                
                elif param_name == 'signal_gen_tes_connected':
                    self._feb_inst.connect_signal_generator_tes(subrack, slot,controller_channel,value)
                           

        elif self._squid_controller=='magnicon':
            
            if self._verbose:
                print('INFO: Setting "' + param_name + '" to ' + str(value) + ' for channel ' 
                      + str(controller_channel) + ' (Magnicon)!')

            if not self._dummy_mode:
                
                if param_name == 'tes_bias':
                    readback_val = self._mag_inst.set_tes_current_bias(controller_channel, value, mode=None)
                
                elif param_name == 'squid_bias':
                    readback_val = self._mag_inst.set_squid_bias(controller_channel, 'I',value)
                
                elif param_name == 'lock_point_voltage':
                    readback_val = self._mag_inst.set_squid_bias(controller_channel, 'V',value)
                
                elif param_name == 'feedback_gain':
                    readback_val = self._mag_inst.set_GBP(controller_channel, value)
                    
                elif param_name == 'preamp_gain' or param_name == 'preamp_bandwidth':
                    if isinstance(value,tuple) and len(value)==2:
                        amp, bw = self._mag_inst.set_amp_gain_bandwidth(controller_channel, value[0], value[1])
                        readback_val = (amp,bw)
                    else:
                        print('WARNING: a tuple with (amplitude, bandwidth) required for magnicon preamp setting')

                elif param_name == 'preamp_polarity':
                    readback_val = self._mag_inst.set_amp_gain_sign(controller_channel, value)

                elif param_name == 'feedback_polarity':
                    readback_val = self._mag_inst.set_squid_gain_sign(controller_channel, value)

                elif param_name == 'feedback_mode':
                    mode = 'AMP'
                    if value=='close':
                        value='FLL'
                    readback_val = self._mag_inst.set_amp_or_fll(controller_channel, value)

                elif param_name == 'feedback_resistance':
                    readback_val = self._mag_inst.set_feedback_resistor(controller_channel, value)

                elif param_name == 'squid_dummy':
                    readback_val = self._mag_inst.set_dummy(controller_channel, value)

                elif param_name == 'flux_bias_disconnect':
                    readback_val = self._mag_inst.set_flux_bias_disconnect(controller_channel, value)

                elif param_name == 'output_coupling':
                    readback_val = self._mag_inst.set_output_coupling(controller_channel, value)


        else:
            print('ERROR: Unknow SQUID controller "' + 
                  self._squid_controller + '"!')
        
    
        # ================
        # Read back
        # ================
        time.sleep(0.2)

        if  self._enable_readback and not self._dummy_mode:

            # FEB
            if self._squid_controller=='feb':
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
            
            






    '''
    def get_signal_gen_amplitude(self):

        """
        Signal Generator Amplitude [mVpp]
        (assume only 1 signal generator available?)

        """
        
        return 20.0



    def get_signal_gen_frequency(self):

        """
        Signal generator frequency [Hz]
        (assume only 1 signal generator available?)

        """

        return 100.0

    
    def get_signal_gen_shape(self):

        """
        Signal generator shape
        (assume only 1 signal generator available?)
            1. square wave
            2. sine wave
            3. triangle wave
            4. DC constant
            5. arbitrary pulse shape
        """
        
        return 1


    '''




    def set_heater(self, percent):
        
        """
        Set heater percent
        
        """
        
        print('Setting heater to  ' + str(percent) + '/%')
        

    
    def get_heater(self):
        
        """
        Set heater percent
        
        """
        return 0

        

    
    def set_temperature(self, temperature):
        
        """
        Iteratively set the temperature by increasing 
        the heater (feedback co
        """
        
        print('Setting heater to  ' + str(temperature) + 'mK')
        
        
    def get_temperature(self, channel=[]):
        
        """
        Get temperature from thermometer [mK]
        
        """
        return 20
        
        

    def get_temperature_resistance(self, channel=[]):
        
        """
        Get resistance from thermometer [Ohms]
        """
        return 99999
         
