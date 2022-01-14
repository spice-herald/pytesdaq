import time
import numpy as np
import pickle
from PyQt5.QtCore import QCoreApplication
from matplotlib import pyplot as plt
import pandas as pd

import pytesdaq.daq as daq
import pytesdaq.instruments.control as instrument
import pytesdaq.config.settings as settings
import pytesdaq.io.redis as redis
import pytesdaq.io.hdf5 as hdf5
from pytesdaq.utils import  arg_utils
from pytesdaq.analyzer import analyzer



class Readout:
    
    def __init__(self, setup_file=None):
            

        # setup file
        self._setup_file = setup_file
        
        #self._web_scope = web_scope

        # data source: 
        self._data_source = 'niadc'


        # ADC device 
        self._adc_name = 'adc1'


        # initialize db/adc
        self._daq = None
        self._redis = None
        self._hdf5 = None

        # Is running flag
        self._is_running = False

        # data configuration
        self._adc_config = dict()
        self._detector_config = dict()

        # channels
        self._selected_channel_list = list()
        self._selected_channel_name_list = list()
        
        # Display
        self._first_draw = True
        self._plot_ref = None
        self._plot_fit_ref = None

        # UI
        self._is_qt_ui = False
        self._axes=[]
        self._canvas = []
        self._status_bar = []
        self._colors = dict()
        self._enable_auto_scale = True
        self._nb_bins = 0
        self._ui_widget = dict()
        
     
        # instanciate analyzer
        self._analyzer = analyzer.Analyzer()
        self._do_get_norm = False
        self._do_get_sg = False
        self._do_get_fit_param = False

        
        # instrument control
        self._instrument = None
     
        # selected  data array
        self._selected_data_array = None

        # didv data
        self._didv_data_dict = None

        # hdf5 file
        self._current_file_name = None

        

    def register_ui(self, axes, canvas, status_bar, colors,
                    display_control):
        self._is_qt_ui = True
        self._axes = axes
        self._canvas = canvas
        self._status_bar = status_bar
        self._ui_widget['control'] = display_control
               
        # color
        for key,value in colors.items():
            color = (value[0]/255, value[1]/255,value[2]/255)
            self._colors[key] = color

            
    def register_tools_ui(self, fit_button, result_field,
                          rshunt_spinbox, rp_spinbox, dt_spinbox,
                          pileup_checkbox):
        self._ui_widget['fit'] = fit_button
        self._ui_widget['rshunt'] = rshunt_spinbox
        self._ui_widget['rp'] = rp_spinbox
        self._ui_widget['dt'] = dt_spinbox
        self._ui_widget['pileup'] = pileup_checkbox
        
        self._fit_result_field = result_field


        rshunt = self._analyzer.get_config('rshunt')
        if rshunt is not None:
            self._ui_widget['rshunt'].setValue(rshunt*1000)

        
  
    def select_channels(self, channels):

        self._first_draw = True
        self._analyzer.set_config('reset_running_avg', True)
        self._selected_channel_list = channels
        self._do_get_norm = True
        
        

    def configure(self, data_source, adc_name = 'adc1', channel_list=[],
                  sample_rate=[], trace_length=[],
                  voltage_min=[], voltage_max=[],trigger_type=4,
                  file_list=[]):
        

        
        # check if running
        if self._is_running:
            print('WARNING: Need to stop display first')
            return False
            
        # data source 
        self._data_source = data_source

        # adc name 
        self._adc_name = adc_name


        # read configuration file
        self._config = settings.Config(setup_file=self._setup_file)
        self._adc_config = dict()

        # initialize
        self._daq = None
        self._redis = None
        self._hdf5 = None
    

        
        # NI ADC source
        if self._data_source == 'niadc':

            # check
            if not channel_list or not adc_name:
                error_msg = 'ERROR: Missing channel list or adc name!'
                return error_msg

            # instantiate daq
            self._daq  = daq.DAQ(driver_name = 'pydaqmx',verbose = False)
            self._daq.lock_daq = True
            
            # adc name list
            adc_list = self._config.get_adc_list()
            if adc_name not in adc_list:
                self._daq.clear()
                error_msg = 'ERROR: ADC name "' + adc_name + '" unrecognized!'
                return error_msg

            # ADC setup
            self._adc_config = self._config.get_adc_setup(adc_name)

            # convert connection dataframe to dict 
            connections = self._adc_config['connection_table'].to_dict(orient='list')
            self._adc_config['connection_map'] = dict()
            self._adc_config['connection_map']['adc_chans'] = [int(x) for x in connections['adc_channel']]
            self._adc_config['connection_map']['detector_chans'] = connections['detector_channel']
            self._adc_config['connection_map']['tes_chans'] = connections['tes_channel']
            self._adc_config['connection_map']['controller_chans'] = list()
            for ichan in range(len(connections['controller_channel'])):
                self._adc_config['connection_map']['controller_chans'].append(
                    connections['controller_id'][ichan]+'_'+ connections['controller_channel'][ichan]
                )
                
            
            self._adc_config['channel_list'] = channel_list
            if sample_rate:
                self._adc_config['sample_rate'] = int(sample_rate)
            if trace_length:
                nb_samples = round(self._adc_config['sample_rate']*trace_length/1000)
                self._adc_config['nb_samples'] = int(nb_samples)
            if voltage_min:
                self._adc_config['voltage_min'] = float(voltage_min)
            if voltage_max:
                self._adc_config['voltage_max'] = float(voltage_max)
            
            self._adc_config['trigger_type'] = int(trigger_type)

            adc_config = dict()
            adc_config[adc_name] =  self._adc_config
            self._daq.set_adc_config_from_dict(adc_config)


        # Redis
        elif self._data_source == 'redis':

            self._redis = redis.RedisCore()
            self._redis.connect()
        
        
        # hdf5
        elif self._data_source == 'hdf5':

            if not file_list:
                error_msg = 'ERROR from readout: No files provided'
                return error_msg

            self._hdf5 = hdf5.H5Reader()
            self._hdf5.set_files(file_list)
            
                
    
        return True



    def stop_run(self):
        self._do_stop_run = True
      
    def resume_run(self):
        self._do_pause_run = False

    def clear_daq(self):
        self._do_stop_run = True
        if self._data_source == 'niadc':
            self._daq.clear()    
       

    def is_running(self):
        return self._is_running



        
    def update_analysis_config(self, norm_type=None, unit=None,
                               calc_psd=None,
                               enable_pileup_rejection=None,
                               pileup_cuts=None,
                               enable_running_avg=None,
                               reset_running_avg=None,
                               nb_events_avg=None,
                               fit_didv=None, didv_1pole=None,
                               didv_2pole=None, didv_3pole=None,
                               didv_measurement=None,
                               rshunt=None, rp=None, r0=None,
                               dt=None, add_180phase=None):
        
        """
        Update analysis configuration
        """
        
        if norm_type is not None:
            self._do_get_norm = True
            self._analyzer.set_config('norm_type', norm_type)
            
        if unit is not None:
            self._analyzer.set_config('unit', unit)
        
        if calc_psd is not None:
            self._analyzer.set_config('calc_psd', calc_psd)
            
        if enable_pileup_rejection is not None:
            self._analyzer.set_config('enable_pileup_rejection', enable_pileup_rejection)
        
        if enable_running_avg is not None:
            self._analyzer.set_config('enable_running_avg', enable_running_avg)

        if reset_running_avg is not None:
            self._analyzer.set_config('reset_running_avg', reset_running_avg)
            
        if nb_events_avg is not None:
            self._analyzer.set_config('nb_events_avg', nb_events_avg)

        if fit_didv is not None:
            self._do_get_sg = True
            self._analyzer.set_config('fit_didv', fit_didv)

        if didv_1pole is not None:
            self._analyzer.set_config('didv_1pole', didv_1pole)

        if didv_2pole is not None:
            self._analyzer.set_config('didv_2pole', didv_2pole)
            
        if didv_3pole is not None:
            self._analyzer.set_config('didv_3pole', didv_3pole)
                        
        if didv_measurement is not None:
            self._analyzer.set_config('didv_measurement', didv_measurement)
            
        if rshunt is not None:
            self._analyzer.set_config('rshunt', rshunt)

        if rp is not None:
            self._analyzer.set_config('rp', rp)

        if r0 is not None:
            self._analyzer.set_config('r0', r0)
            
        if dt is not None:
            self._analyzer.set_config('dt', dt)
            
        if add_180phase is not None:
            self._analyzer.set_config('add_180phase', add_180phase)
            
        if pileup_cuts is not None:
            self._analyzer.set_config('pileup_cuts', pileup_cuts)



            
        # redraw after analysis update
        self._first_draw = True
        

        # reset running avg
        if (norm_type is not None or unit is not None or 
            calc_psd is not None or enable_pileup_rejection is not None or
            pileup_cuts is not None):
            self._analyzer.set_config('reset_running_avg', True)


        # ui update

        if self._is_qt_ui:
            
            # pileup:
            if enable_running_avg is not None:
                if enable_running_avg:
                    self._ui_widget['pileup'].setEnabled(True)
                else:
                    self._ui_widget['pileup'].setChecked(False)
                    self._ui_widget['pileup'].setEnabled(False)
            

    def set_auto_scale(self, enable_auto_scale):
        self._enable_auto_scale  = enable_auto_scale
  


    def run(self, save_redis=False, do_plot=False):
        

               
        # =========================
        # Initialize data container
        # =========================
        data_array = []
        if self._data_source == 'niadc':
            nb_channels = len(self._adc_config['channel_list'])
            nb_samples =  self._adc_config['nb_samples']
            data_array = np.zeros((nb_channels,nb_samples), dtype=np.int16)
        
            

        
        # =========================
        # LOOP Events
        # =========================
        self._do_stop_run = False
        self._do_pause_run = False
        self._is_running = True
        self._first_draw = True
        
        while (not self._do_stop_run):
            
            # event QT process
            if self._is_qt_ui:
                QCoreApplication.processEvents()
                
                

            # ----------------------
            # Pause
            # ----------------------
            if self._do_pause_run:
                time.sleep(0.01)
                continue

                
            # ----------------------
            # Get Traces
            # ----------------------

            if self._data_source == 'niadc':

                self._daq.read_single_event(data_array, do_clear_task=False)


            elif self._data_source == 'hdf5':

                data_array, self._adc_config = self._hdf5.read_event(include_metadata=True,
                                                                     adc_name=self._adc_name)
                
                # if error -> output is a string
                if self._adc_config['read_status'] != 0:
                    if self._is_qt_ui:
                        self._status_bar.showMessage('INFO: ' + self._adc_config['error_msg'])
                    break

                # add channel list
                if isinstance(self._adc_config['adc_channel_indices'], np.int32):
                    self._adc_config['channel_list'] = [self._adc_config['adc_channel_indices']]
                else:
                    self._adc_config['channel_list'] = list(self._adc_config['adc_channel_indices'])


                # add current file name
                current_file = self._hdf5.get_current_file_name()
                self._adc_config['file_name'] = current_file.split('/')[-1]

                # display
                if 'event_num' in self._adc_config and self._is_qt_ui:
                    self._status_bar.showMessage('INFO: File = '
                                                 + self._adc_config['file_name']
                                                 + ', EventNumber = '
                                                 + str(self._adc_config['event_num']))
                                                 

                # connection map
                self._adc_config['connection_map'] = self._hdf5.get_connection_dict()
                                 
                # detector config
                if (self._detector_config is None
                    or self._current_file_name is None
                    or self._current_file_name!=self._adc_config['file_name']):
                    
                    self._current_file_name = self._adc_config['file_name']
                    self._detector_config['settings'] = self._hdf5.get_detector_config()
                    self._detector_config['connection_map'] = self._adc_config['connection_map']
                    self._do_get_norm = True
                    self._do_get_sg = True
                    self._do_get_fit_param = True
            
            else:
                print('Not implemented')


            # event QT process
            if self._is_qt_ui:
                QCoreApplication.processEvents()
              


            # ------------------
            # Analysis
            # ------------------

            # check selected channels
            channel_num_list = list()
            channel_index_list = list()
            counter = 0
          
            for chan in self._adc_config['channel_list']:
                if chan in self._selected_channel_list:
                    channel_num_list.append(chan)
                    channel_index_list.append(counter)
                counter+=1

            if len(channel_num_list) == 0:
                continue

            selected_data_array = data_array[channel_index_list,:]
            self._adc_config['selected_channel_list'] = channel_num_list
            self._adc_config['selected_channel_index'] = channel_index_list

         
            # get normalization
            if self._do_get_norm or self._analyzer.get_config('norm_list') is None:
                self._fill_norm()
                self._do_get_norm = False

            # get signal gen
            if self._do_get_sg or self._analyzer.get_config('signal_gen_current') is None:
                self._fill_signal_gen()
                self._fill_tes_bias()
                self._do_get_sg = False       

            # fit parameter
            if self._do_get_fit_param:
                self._fill_fit_param()
                self._do_get_fit_param = False



                
            # Do analysis
            self._selected_data_array, self._didv_data_dict, nb_avg = self._analyzer.process(
                selected_data_array,
                self._adc_config
            )

            # display running avg
            if self._is_qt_ui:
                if nb_avg>0:
                    self._status_bar.showMessage('Running average: '
                                                 + str(nb_avg)
                                                 + ' events')
                else:
                    self._status_bar.showMessage('Running...')
                

            # check if fit done
            resistance_type = self._analyzer.get_config('didv_measurement')
            if self._didv_data_dict is not None:
                             
                # update GUI
                if self._is_qt_ui:
                    self._ui_widget['fit'].setStyleSheet('background-color: rgb(162, 162, 241);')
                    self._ui_widget['fit'].setText('FIT')
                    self._ui_widget['fit'].setEnabled(True)
                    # pause run
                    self._ui_widget['control'].setStyleSheet('background-color: rgb(255, 255, 0);')
                    self._ui_widget['control'].setText('Resume \n Display')
                    self._do_pause_run = True

                    # update rp if needed
                    if resistance_type=='Rp':
                        key = 'params'
                        result = self._didv_data_dict['results'][0]
                        if 'smallsignalparams' in result:
                            key = 'smallsignalparams'
            
                        rp = result[key]['rp']
                        self._ui_widget['rp'].setValue(rp*1000)
                      
                    
                # Disable fit
                self.update_analysis_config(fit_didv=False)
              
            

            # event QT process
            if self._is_qt_ui:
                QCoreApplication.processEvents()
              

            # ------------------
            # Store in redis
            # ------------------





            # ------------------
            # Display
            # ------------------


            # channel names
            self._selected_channel_name_list = list()
            if do_plot or self._didv_data_dict is not None:

                tes_channels = None
                if 'tes_chans' in self._adc_config['connection_map']:
                    tes_channels =  self._adc_config['connection_map']['tes_chans']
           
                detector_channels = None
                if 'detector_chans' in self._adc_config['connection_map']:
                    detector_channels =  self._adc_config['connection_map']['detector_chans']
         
                for chan in self._adc_config['selected_channel_list']:
                    index = self._adc_config['connection_map']['adc_chans'].index(int(chan))
                    name = str()
                    if tes_channels is not None:
                        name = tes_channels[index]

                    if detector_channels is not None:
                        name_det = detector_channels[index]
                    if tes_channels is not None:
                        name = name + ': ' + name_det
                    else:
                        name =  name_det

                    if not name:
                        name = 'AI' + str(chan)

                    self._selected_channel_name_list.append(name)



                    
            # Histogram
            if do_plot:
                fit_array = None
                fit_dt = None
                if self._didv_data_dict is not None:
                    fit_array = self._didv_data_dict['fit_array']
                    fit_dt = self._didv_data_dict['results'][0]['params']['dt']
                self._plot_data(self._selected_data_array,
                                fit_array,
                                fit_dt,
                                self._analyzer.freq_array)


            # Fit results
            if self._didv_data_dict is not None and self._is_qt_ui:

                # display
                self._fit_result_field.clear()

                # get Rp
                rp = None
                if resistance_type!='Rp':
                    rp = float(self._analyzer.get_config('rp'))

                                
                # loop channel
                nb_chan = len(self._didv_data_dict['results'])
                               
                for ichan in range(nb_chan):

                    result_list = list()
                    infinite_l_result_list = list()
                    falltimes_list = list()
                    
                    chan_name = self._selected_channel_name_list[ichan]
                    didv = self._didv_data_dict['results'][ichan]['didv0']
                    result = self._didv_data_dict['results'][ichan]['smallsignalparams']
                    falltimes = self._didv_data_dict['results'][ichan]['falltimes']
                    result_infinite_l = dict()
                    if 'infinite_l' in self._didv_data_dict['results'][ichan]:
                        result_infinite_l = self._didv_data_dict['results'][ichan]['infinite_l']
                        
                    
                    
                    rshunt = result['rsh']
                    result_list.append(['Input Rsh [mOhms]', f"{rshunt*1000:.2f}"])

                    if resistance_type=='Rp':
                        rp = result['rp']
                        result_list.append(['Rp [mOhms]', f"{rp*1000:.2f}"])
                    else:
                        result_list.append(['Input Rp [mOhms]', f"{rp*1000:.2f}"])
                        
                    if 'r0' in result:
                        result_list.append(['Input R0 [mOhms]', f"{result['r0']*1000:.2f}"])
                     
                    if resistance_type=='Rn':
                        rn = result['rp']-rp
                        result_list.append(['Rn [mOhms]', f"{rn*1000:.2f}"])
                                      
                     
                    if 'tau0' in result:
                        result_list.append(['tau0 [us]', f"{result['tau0']*1e6:.3f}"])

                    #if 'tau3' in result:
                    #    result_list.append(['tau3 [us]', f"{result['tau3']*1e6:.3f}"])
                                                              
                    result_list.append(['L [nH]', f"{result['L']*1e9:.3f}"])
                    result_list.append(['dt [mus]', f"{result['dt']*1e6:.3f}"])
                  
                    if 'l' in result:
                        result_list.append(['loop gain (l)', f"{result['l']:.3f}"])
                      
                    if 'beta' in result:
                        result_list.append(['beta', f"{result['beta']:.3f}"])

                    if 'gratio' in result:
                        result_list.append(['gratio', f"{result['gratio']:.3f}"])

                    
                    if resistance_type=='R0' and result_infinite_l:
                        r0_infinite = result_infinite_l['r0']*1000
                        i0_infinite = result_infinite_l['i0']*1e6
                        p0_infinite = result_infinite_l['p0']*1e15
                        
                        infinite_l_result_list.append(['R0 [mOhms]',
                                                       f"{r0_infinite:.2f}"])
                        infinite_l_result_list.append(['I0 [uA]',
                                                       f"{i0_infinite:.3f}"])
                        infinite_l_result_list.append(['P0 [fWatts]',
                                                       f"{p0_infinite:.2f}"])
                        
                    # Fall times
                    falltime_name = ['Tau+ (~Tau_L/R) [us]','Tau- (~Tau_eff) [us]', 'Tau3 [us]']
                    for ift in range(len(falltimes)):
                        falltime = falltimes[ift]*1e6
                        falltimes_list.append([falltime_name[ift], f"{falltime:.3f}"])
                        
                    # convert to dataframe
                    smallsignal_pd = pd.DataFrame(result_list, columns = ['Parameter','Value'])
                    falltime_pd = pd.DataFrame(falltimes_list, columns = ['Parameter','Value'])

                    infinite_l_pd = None
                    if infinite_l_result_list:
                        infinite_l_pd = pd.DataFrame(infinite_l_result_list, columns = ['Parameter','Value'])

                    
                    # insert to UI
                    chan_html = "<font color='red' size='4'><u>" + chan_name + "</u><br></font>"
                    self._fit_result_field.insertHtml(chan_html)
                    self._fit_result_field.insertHtml(
                        "<br><font color='blue' size='3'>Small Signal Parameters</font>")
                    self._fit_result_field.insertHtml(smallsignal_pd.to_html(index=False))
                    if infinite_l_pd is not None:
                        self._fit_result_field.insertHtml(
                            "<br><br><font color='blue' size='3'>Infinite Loop Gain Approx.</font>")
                        self._fit_result_field.insertHtml(infinite_l_pd.to_html(index=False))
                    self._fit_result_field.insertHtml(
                        "<br><br><font color='blue' size='3'>Pole Fall Times</font>")
                    self._fit_result_field.insertHtml(falltime_pd.to_html(index=False))
                    self._fit_result_field.insertHtml("<br><br><br><br>")
                


        # =========================
        # Cleanup
        # =========================
        if self._data_source == 'niadc':
            self._daq.clear()
        
        self._is_running = False
        self._current_file_name = None
        self._adc_config = None


    def save_data(self, filename):
        """
        Save data array
        """
        if filename and self._selected_data_array is not None:
            np.save(filename, self._selected_data_array)
            np.save(filename+'_freq', self._analyzer.freq_array)
            print('File ' + filename + '.npy saved!')


    def save_fit_results(self, filename=None):
        """
        Save test results in a pickle file
        """
        if self._didv_data_dict is not None:
            with open('test.pickle', 'wb') as handle:
                pickle.dump(self._didv_data_dict, handle, protocol=pickle.HIGHEST_PROTOCOL)
                
    

    def read_from_board(self, read_norm=False, read_sg=False,
                        read_bias=False):
        """
        Read from board, FEB/Magnicon or signal generator
        Save in analysis config
        """

        # check if norm needs to be read
        norm_type = self._analyzer.get_config('norm_type')
        if  norm_type.find('OpenLoop') == -1  and  norm_type.find('CloseLoop') == -1:
            read_norm = False
            
        # check if signal gen needs to be read
        if not self._analyzer.get_config('fit_didv'):
            read_sg = False
            
        # Return if nothing to do
        if not read_norm and not read_sg:
            return
            
        
        # Instantiate instrument
        if self._instrument is None:
            self._instrument = instrument.Control(setup_file=self._setup_file,
                                                  dummy_mode=False)


        # Read normalization
        if read_norm:

            # intialize
            norm_val = 1
            norm_list = list()

            # loop selected channels and get norm
            for chan in self._adc_config['selected_channel_list']:
            
                if norm_type == 'OpenLoop PreAmp':
                    norm_val = abs(
                        self._instrument.get_open_loop_preamp_norm(adc_id=self._adc_name, 
                                                                   adc_channel=chan)
                    )
                    
                elif norm_type == 'OpenLoop PreAmp+FB':
                    norm_val = abs(
                        self._instrument.get_open_loop_full_norm(adc_id=self._adc_name, 
                                                                 adc_channel=chan)
                    )
                    
                elif norm_type == 'CloseLoop':
                    norm_val = abs(
                        self._instrument.get_volts_to_amps_close_loop_norm(adc_id=self._adc_name, 
                                                                           adc_channel=chan)
                    )

                print('INFO: Normalization for channel ' + str(chan) + ' = ' + str(norm_val))
                
                # fill array
                norm_list.append(norm_val)
                
            self._analyzer.set_config('norm_list', norm_list)

            
        # Signal Gen
        if read_sg:
            signal_gen_info = dict()
            for chan in self._adc_config['selected_channel_list']:
                signal_gen_info = self._instrument.get_signal_gen_params(adc_id=self._adc_name,
                                                                         adc_channel=chan)
                # FIXME... Currently it depends of channel.
                # Let's just assume there is only one signal generator 
                break
            
            self._analyzer.set_config('signal_gen_current', signal_gen_info['current'])
            self._analyzer.set_config('signal_gen_frequency', signal_gen_info['frequency'])
            
            
        # TES bias
        tes_bias_list = list()
        if read_bias or read_sg:
            for chan in self._adc_config['selected_channel_list']:
                bias = float(self._instrument.get_tes_bias(adc_id=self._adc_name,
                                                           adc_channel=chan))
                tes_bias_list.append(bias*1e-6)
            self._analyzer.set_config('tes_bias', tes_bias_list)
            
            

    def _plot_data(self, data_array, fit_array=None, fit_dt=None, freq_array=[]):


        if self._do_stop_run:
            return


        # chan/bins
        nchan =  np.size(data_array,0)
        nbins =  np.size(data_array,1)


        # sanity checks
        if nchan == 0 or nbins==0:
            return

        if self._plot_ref is None or len(self._plot_ref)!=nchan:
            self._first_draw = True

        if fit_array is not None and (
                self._plot_fit_ref is None
                or  len(self._plot_fit_ref)!=nchan):
            self._first_draw = True

            
        if self._analyzer.get_config('calc_psd'):
            if freq_array is None or len(freq_array)!=nbins:
                return


        if self._nb_bins != nbins:
            self._nb_bins = nbins
            self._first_draw = True


        # label
        ylabel = self._analyzer.get_config('unit')
        if self._analyzer.get_config('calc_psd'):
            ylabel = ylabel + '/rtHz'
            
        


        # draw!
        if self._first_draw:
           
            # axes label
            self._axes.clear()
            if self._analyzer.get_config('calc_psd'):
                self._axes.set_xlabel('Hz')
                self._axes.set_ylabel(ylabel)
                self._axes.set_title('PSD')
                self._axes.set_yscale('log')
                self._axes.set_xscale('log')
            else:
                self._axes.set_xlabel('ms')
                self._axes.set_ylabel(ylabel)
                self._axes.set_title('Pulse')
                self._axes.set_yscale('linear')
                self._axes.set_xscale('linear')

            # x axis value
            dt = 1/self._adc_config['sample_rate']
            x_axis = np.arange(0,nbins)*1e3*dt
            if self._analyzer.get_config('calc_psd') and len(freq_array)!=0:
                x_axis = freq_array
          
            self._plot_ref = [None]*nchan

            x_axis_fit = []
            if fit_array is not None and fit_dt is not None:
                x_axis_fit = (np.arange(0,nbins)*dt+fit_dt)*1e3
                self._plot_fit_ref = [None]*nchan
                
    
            for ichan in range(nchan):
                chan = self._adc_config['selected_channel_list'][ichan]

                self._plot_ref[ichan], = self._axes.plot(x_axis, data_array[ichan],
                                                         color=self._colors[chan])
                if fit_array is not None:
                    self._plot_fit_ref[ichan], = self._axes.plot(x_axis_fit, fit_array[ichan],
                                                                 color='black')
            self._canvas.draw()    
            self._first_draw = False
        else:
            
            for ichan in range(nchan):
                self._plot_ref[ichan].set_ydata(data_array[ichan])
                if fit_array is not None:
                    self._plot_fit_ref[ichan].set_ydata(fit_array[ichan])

        if self._enable_auto_scale:
            self._axes.relim()
            self._axes.autoscale_view()
            

        self._axes.grid(which='major',axis='both',alpha=0.6)
        self._axes.grid(which='minor',axis='both',alpha=0.3, ls='dashed')
        self._axes.legend(self._selected_channel_name_list, loc='upper right')
        self._canvas.draw()
        self._canvas.flush_events()
            

        
    def _fill_norm(self):
        """
        Fill normalization list and store in analysis dictionary
        """

        # find current normalization type
        norm_type = self._analyzer.get_config('norm_type')

     
        # case open/closed loop -> read from board
        if norm_type.find('OpenLoop')!=-1 or norm_type.find('CloseLoop')!=-1:

            if self._data_source == 'niadc':
                self.read_from_board(read_norm=True)
                
            elif self._data_source == 'hdf5':
                norm_list = list()
                for chan in self._adc_config['selected_channel_list']:
                    chan_index = self._detector_config['connection_map']['adc_chans'].index(chan)
                    detector_name = self._detector_config['connection_map']['detector_chans'][chan_index]
                    settings = self._detector_config['settings'][detector_name]
                    norm_val = 1
                    if norm_type == 'OpenLoop PreAmp':
                        norm_val = abs(settings['open_loop_preamp_norm'])
                    elif norm_type == 'OpenLoop PreAmp+FB':
                        norm_val = abs(settings['open_loop_full_norm'])
                    elif norm_type == 'CloseLoop':
                        norm_val = settings['close_loop_norm']
                    norm_list.append(norm_val)
                self._analyzer.set_config('norm_list', norm_list)
                
        else:
            # gain defined by user
            norm_val = 1
            if norm_type=='Gain=10':
                norm_val = 10
            elif norm_type=='Gain=100':
                norm_val = 100
            
            # add to analysis config
            norm_list = list()
            for chan in self._adc_config['selected_channel_list']:
                norm_list.append(norm_val)
            self._analyzer.set_config('norm_list', norm_list)
        
         
        
    def _fill_signal_gen(self):
        """
        Signal generator information
        """
              
        if self._data_source == 'niadc':
            self.read_from_board(read_sg=True)
            
        elif self._data_source == 'hdf5':

            for chan in self._adc_config['selected_channel_list']:
                chan_index = self._detector_config['connection_map']['adc_chans'].index(chan)
                detector_name = self._detector_config['connection_map']['detector_chans'][chan_index]
                settings = self._detector_config['settings'][detector_name]
                self._analyzer.set_config('signal_gen_current', float(settings['signal_gen_current']))
                self._analyzer.set_config('signal_gen_frequency', float(settings['signal_gen_frequency']))
                break



            
    def _fill_tes_bias(self):
        """
        TES bias
        """
              
        if self._data_source == 'niadc':
            self.read_from_board(read_bias=True)
            
        elif self._data_source == 'hdf5':
            
            tes_bias_list = list()
            for chan in self._adc_config['selected_channel_list']:
                chan_index = self._detector_config['connection_map']['adc_chans'].index(chan)
                detector_name = self._detector_config['connection_map']['detector_chans'][chan_index]
                settings = self._detector_config['settings'][detector_name]
                bias = float(self._detector_config['settings'][detector_name]['tes_bias'])
                tes_bias_list.append(bias)
            self._analyzer.set_config('tes_bias', tes_bias_list)

    


    def _fill_fit_param(self):
        """
        Shunt Resistance 
        (one value for all channels)
        """
        
        if self._data_source == 'hdf5':
            
            for chan in self._adc_config['selected_channel_list']:
                chan_index = self._detector_config['connection_map']['adc_chans'].index(chan)
                detector_name = self._detector_config['connection_map']['detector_chans'][chan_index]
                settings = self._detector_config['settings'][detector_name]
             
                self._analyzer.set_config('rshunt', settings['shunt_resistance'])
                if 'rshunt' in self._ui_widget:
                    self._ui_widget['rshunt'].setValue(settings['shunt_resistance']*1000)
                break

                
