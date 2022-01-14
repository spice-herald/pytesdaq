"""
Main Frame Window
"""
import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from matplotlib import pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT  as NavigationToolbar
from matplotlib.figure import Figure
from glob import glob
import os
import time
from datetime import datetime

from pytesdaq.config import settings
from pytesdaq.scope import readout
from pytesdaq.utils import arg_utils



class MainWindow(QtWidgets.QMainWindow):
    
    def __init__(self, setup_file=None):
        super().__init__()
               

        # initialize attribute
        self._data_source = 'niadc'
        self._file_list = list()
        self._select_hdf5_dir = False

        # raw data path
        self._default_raw_data_dir = './'
        self._default_fig_data_dir = './'
        if setup_file is not None:
            config = settings.Config(setup_file=setup_file)
            run = 'run' + str(config.get_fridge_run())
            base_path = config.get_data_path()
            self._default_raw_data_dir = base_path + '/' + run + '/raw'
            if not os.path.isdir(self._default_raw_data_dir):
                self._default_raw_data_dir  = base_path
            self._default_fig_data_dir = base_path + '/' + run + '/operation'
            if not os.path.isdir(self._default_fig_data_dir):
                self._default_fig_data_dir = base_path
        

        # initalize main window
        self.setWindowModality(QtCore.Qt.NonModal)
        self.resize(900, 700)
        self.setStyleSheet('background-color: rgb(211, 252, 255);')
        self.setTabShape(QtWidgets.QTabWidget.Rounded)
        self.setWindowTitle('Pulse Viewer')



        # channel color map
        self._channels_color_map = {0:(255, 207, 32),
                                    1:(0, 85, 255),
                                    2:(170, 0, 255),
                                    3:(0, 170, 127),
                                    4:(255, 0, 0),
                                    5:(170, 116, 28),
                                    6:(15, 235, 255),
                                    7:(121, 121, 121)}
        


        # channel list
        self._channel_list = list()

        # setup frames
        self._init_main_frame()
        self._init_title_frame()
        self._init_control_frame()
        self._init_display_frame()
        self._init_channel_frame()
        self._init_tools_frame()

              
        # show
        self.show()

        
        # initialize readout
        self._readout = readout.Readout(setup_file=setup_file)
        self._readout.register_ui(self._axes,self._canvas, self.statusBar(),
                                  self._channels_color_map,
                                  self._display_control_button)
        


        # tools
        self._tools = ToolsWindow(readout=self._readout,
                                  unit_combobox=self._unit_combobox,
                                  running_avg_checkbox=self._running_avg_checkbox,
                                  running_avg_spinbox=self._running_avg_spinbox)
            
        
    def closeEvent(self,event):
        """
        This function is called when exiting window
        superse base class
        """
        
        self._readout.stop_run()
        
        # wait (needed?)
        for ii in range(10):
            time.sleep(0.01)
                
        
        self._tools = None
        print('Exiting Pulse Display UI')
        

    def _get_run_state(self):
        """
        Get Run State
        1 = stopped
        2 = paused
        3 = runnining
        """
        run_state = 0
        display_text = self._display_control_button.text()
        if display_text == 'Display \n Waveform':
            run_state = 1
        elif display_text == 'Resume \n Display':
            run_state = 2
        else:
            run_state = 3

    
        return run_state 
            

    def _handle_display(self):
        """
        Handle display. Called when clicking on display waveform 
        """

        run_state = self._get_run_state()
               
        if run_state==3:

            # Stop run
            self._readout.stop_run()
                       
            # change button display
            self._set_display_button(False)

            # enable
            self._data_source_tabs.setEnabled(True)
            self._source_combobox.setEnabled(True)

            # status bar
            self.statusBar().showMessage('Display Stopped')
          

        elif run_state==2:
            
            self._set_display_button(True)
            self._readout.resume_run()
            
        elif run_state==1:
            
            adc_name = 'adc1'
            device = self._device_combobox.currentText()
            if device[0:2] == 'NI':
               adc_name =  device.split()
               adc_name = adc_name[1].lower()
                        

            if self._data_source  == 'niadc':
                
                # get sample rate:
                sample_rate = int(self._sample_rate_spinbox.value())
           
                # get trace length
                trace_length = float(int(self._trace_length_spinbox.value()))
        
                # voltage min:
                voltage_min = int(self._voltage_min_combobox.currentText())
                voltage_max = int(self._voltage_max_combobox.currentText())
             

                # trigger type
                trigger_mode = self._trigger_combobox.currentText()
                trigger_type = 4
                if trigger_mode=='ExtTrig':
                    trigger_type = 2
                elif trigger_mode=='Threshold':
                    trigger_type = 3


                # get all channels
                channel_list = list(range(8))
                status = self._readout.configure('niadc', adc_name=adc_name, channel_list=channel_list,
                                                 sample_rate=sample_rate, trace_length=trace_length,
                                                 voltage_min=voltage_min, voltage_max=voltage_max,
                                                 trigger_type=trigger_type)
                
                # error
                if isinstance(status,str):
                    self.statusBar().showMessage(status)
                    return

            elif self._data_source == 'hdf5':
                
                # check selection done
                if not self._file_list:
                    self.statusBar().showMessage('WARNING: No files selected!')  
                    return

                status = self._readout.configure('hdf5', file_list=self._file_list)

                # error
                if isinstance(status,str):
                    self.statusBar().showMessage(status)
                    return
            
            else:
                self.statusBar().showMessage('WARNING: Redis not implemented')  
                return


            # reset running avg
            self._readout.update_analysis_config(reset_running_avg=True)


            
            # status bar
            self.statusBar().showMessage('Running...')
          

            # disable 
            self._data_source_tabs.setEnabled(False)
            self._source_combobox.setEnabled(False)


            # run 
            self._set_display_button(True)
            self._readout.run(do_plot=True)

  
            # status bar
            self.statusBar().showMessage('Run stopped...')
          

            # change status
            self._set_display_button(False)
            self._data_source_tabs.setEnabled(True)
            self._source_combobox.setEnabled(True)


           
            
        


  
    def _handle_source_selection(self):
        
        # get source
        data_source = str(self._source_combobox.currentText())
        
        # select tab
        if data_source== 'Redis':

            self._data_source  = 'redis'

            # visibility
            self._data_source_tabs.setTabVisible(0,False)
            self._data_source_tabs.setTabVisible(1,False)
            self._data_source_tabs.setTabVisible(2,True)

            # set current
            self._data_source_tabs.setCurrentWidget(self._redis_tab)


            # disable read from board
            self._read_board_button.setEnabled(False)
            
            
        elif data_source== 'HDF5':
            
            self._data_source  = 'hdf5'
            
            # visibility
            self._data_source_tabs.setTabVisible(0,False)
            self._data_source_tabs.setTabVisible(1,True)
            self._data_source_tabs.setTabVisible(2,False)

            # set current
            self._data_source_tabs.setCurrentWidget(self._hdf5_tab)

            # disable read from board
            self._read_board_button.setEnabled(False)
            


            
        elif data_source== 'Device':
            
            self._data_source  = 'niadc'

            # visibility
            self._data_source_tabs.setTabVisible(0,True)
            self._data_source_tabs.setTabVisible(1,False)
            self._data_source_tabs.setTabVisible(2,False)

            # set current
            self._data_source_tabs.setCurrentWidget(self._niadc_tab)


            # enable read from board
            self._read_board_button.setEnabled(True)
            
            

            
        else:
            print('WARNING: Unknown selection')



    def _handle_hdf5_filedialog_type(self):

        if self._hdf5_dir_radiobutton.isChecked():
            self._select_hdf5_dir = True
        else:
            self._select_hdf5_dir = False
                

    def _handle_hdf5_filedialog(self):
        """
        Handle hdf5 selection. 
        Called when clicking on select HDF5
        """
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog

        files = list()
        if not self._select_hdf5_dir:
            files, _ = QtWidgets.QFileDialog.getOpenFileNames(self,'Select File (s)',self._default_raw_data_dir,
                                                              'HDF5 Files (*.hdf5)', options=options)
        else:
            options |= QtWidgets.QFileDialog.ShowDirsOnly  | QtWidgets.QFileDialog.DontResolveSymlinks
            dir = QtWidgets.QFileDialog.getExistingDirectory(self,'Select Directory',
                                                             self._default_raw_data_dir,options=options)
                                 

            if os.path.isdir(dir):
                files = glob(dir+'/*_F*.hdf5')

        if not files:
            self.statusBar().showMessage('No file have been selected!')
        else:
            self.statusBar().showMessage('Number of files selected = ' + str(len(files)))
            self._file_list = files
            self._file_list.sort()



    def _handle_save_data(self):

        # default name
        now = datetime.now()
        default_name = now.strftime('%Y') +  now.strftime('%m') + now.strftime('%d') 
        default_name += '_' +  now.strftime('%H') + now.strftime('%M') + now.strftime('%S')
        


        
        # select directory
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(self,'Choose file name to save to',
                                                            self._default_fig_data_dir +'/' + default_name,
                                                            'Fig (*.png) + Numpy File (*.npy)',
                                                            options=options)
        
        self._readout.save_data(filename)
        self._fig.savefig(filename + '.png')


            

    def _handle_channel_selection(self):
        """
        Handle channel buttons selection (Signal/Slot connection)
        """

        # get sender
        button = self.sender()

        # get channel number
        object_name = str(button.objectName())
        name_split =  object_name.split('_')
        channel_num = int(name_split[1])

        # change color
        if button.isChecked():
            # change color
            button.setStyleSheet('background-color: rgb(226, 255, 219);')

            # remove from list
            if self._channel_list and channel_num in self._channel_list:
                self._channel_list.remove(channel_num)
        else:

            # change color
            color = self._channels_color_map[channel_num]
            color_str = 'rgb(' + str(color[0]) + ',' + str(color[1]) + ',' + str(color[2]) + ')' 
            button.setStyleSheet('background-color: ' + color_str +';')
        
            # add to list
            self._channel_list.append(channel_num)

            # make sure it is unique...
            self._channel_list = list(set(self._channel_list))


            
        # update readout
        self._readout.select_channels(self._channel_list)

        
        

    def _handle_waveform_type(self):
        """
        Handle waveform type and unit selection (Signal/Slot connection)
        """
        waveform_type = str(self._waveform_combobox.currentText())


        # type
        calc_psd = False
        if waveform_type=='PSD':
            calc_psd = True
      
        # update analysis config
        self._readout.update_analysis_config(calc_psd=calc_psd)

  


    def _handle_waveform_unit(self):
        """
        Handle waveform type and unit selection (Signal/Slot connection)
        """

        
        # unit
        unit =  str(self._unit_combobox.currentText())                                   
        norm = str(self._norm_combobox.currentText())
           
        # change norm display
        self._norm_combobox.clear()
        if unit=='ADC':
            self._norm_combobox.addItem('None')
            norm = 'NoNorm'
        elif (unit=='Volts' or unit=='mVolts' or unit=='nVolts'):
            self._norm_combobox.addItem('None')
            self._norm_combobox.addItem('OpenLoop PreAmp')
            self._norm_combobox.addItem('OpenLoop PreAmp+FB')
            if norm == 'OpenLoop PreAmp':
                self._norm_combobox.setCurrentIndex(1)
            elif norm == 'OpenLoop PreAmp+FB':
                self._norm_combobox.setCurrentIndex(2)
            else:
                self._norm_combobox.setCurrentIndex(0)
                norm = 'NoNorm'
        elif (unit=='Amps' or unit=='uAmps' or unit=='pAmps' or unit=='Watts' or unit=='pWatts'):
            self._norm_combobox.addItem('CloseLoop')
            self._norm_combobox.setCurrentIndex(0)
            norm = 'CloseLoop'
        elif unit=='g':
            self._norm_combobox.addItem('Gain=1')
            self._norm_combobox.addItem('Gain=10')
            self._norm_combobox.addItem('Gain=100')
            self._norm_combobox.setCurrentIndex(2)
            norm = 'Gain=100'
            

        # update analysis
        self._readout.update_analysis_config(unit=unit, norm_type=norm)
        

    def _handle_read_board(self):
        self._readout.read_from_board(read_norm=True, read_sg=True)
        print('INFO: Reading from board')


    def _handle_waveform_norm(self):
        """
        Handle waveform type and unit selection (Signal/Slot connection)
        """

             
        # norm 
        norm = str(self._norm_combobox.currentText())

        # update analysis
        self._readout.update_analysis_config(norm_type=norm)



    def _handle_auto_scale(self):
        
        enable_auto_scale = False
        if self._auto_scale_checkbox.isChecked():
            enable_auto_scale = True
        self._readout.set_auto_scale(enable_auto_scale)
        


    def _handle_running_avg(self):
        
        if self._running_avg_checkbox.isChecked():
            self._running_avg_spinbox.setEnabled(True)
            #self._pileup_cut_checkbox.setEnabled(True)
            value = int(self._running_avg_spinbox.value())
            self._readout.update_analysis_config(enable_running_avg=True, nb_events_avg=value)
        else:
            #self._running_avg_spinbox.setProperty('value', 1)
            self._running_avg_spinbox.setEnabled(False)
            #self._pileup_cut_checkbox.setEnabled(False)
            #self._pileup_cut_checkbox.setChecked(False)
            self._readout.update_analysis_config(enable_running_avg=False,
                                                 enable_pileup_rejection=False)

  


    def _init_main_frame(self):
        
       
        # add main widget
        self._central_widget = QtWidgets.QWidget(self)
        self._central_widget.setEnabled(True)
        self._central_widget.setObjectName('central_widget')
        self.setCentralWidget(self._central_widget)
        

        # add menubar and status 
        self._menu_bar = self.menuBar()
        self.statusBar().showMessage('Status information')
        

    def _init_title_frame(self):

        # add title frame
        self._title_frame = QtWidgets.QFrame(self._central_widget)
        self._title_frame.setGeometry(QtCore.QRect(10, 8, 877, 61))
        self._title_frame.setStyleSheet('background-color: rgb(0, 0, 255);')
        self._title_frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self._title_frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self._title_frame.setObjectName('titleWindow')

        # add title label
        self._title_label = QtWidgets.QLabel(self._title_frame)
        self._title_label.setGeometry(QtCore.QRect(26, 12, 261, 37))
        font = QtGui.QFont()
        font.setFamily('Sans Serif')
        font.setPointSize(23)
        font.setBold(True)
        font.setWeight(75)
        self._title_label.setFont(font)
        self._title_label.setStyleSheet('color: rgb(255, 255, 127);')
        self._title_label.setObjectName('titleLabel')
        self._title_label.setText('Pulse Display')

        # add device selection box + label
        
        # combo box
        self._device_combobox = QtWidgets.QComboBox(self._title_frame)
        self._device_combobox.setGeometry(QtCore.QRect(470, 16, 93, 29))
        self._device_combobox.setObjectName('deviceComboBox')
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(50)
        self._device_combobox.setFont(font)
        #self._device_combobox.setStyleSheet('background-color: rgb(226, 255, 219);')
        self._device_combobox.addItem('NI ADC1')



        # device label
        device_label = QtWidgets.QLabel(self._title_frame)
        device_label.setGeometry(QtCore.QRect(402, 20, 65, 17))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        device_label.setFont(font)
        device_label.setStyleSheet('color: rgb(200, 255, 255);')
        device_label.setObjectName('deviceLabel')
        device_label.setText('Device:')


        # status widget  
    
        '''
        # status label
        status_label = QtWidgets.QLabel(self._title_frame)
        status_label.setGeometry(QtCore.QRect(674, 24, 59, 15))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        status_label.setFont(font)
        status_label.setStyleSheet('color: rgb(200, 255, 255);')
        status_label.setObjectName('statusLabel')
        status_label.setText('Status:')

        # status widget
        self._status_textbox = QtWidgets.QLabel(self._title_frame)
        self._status_textbox.setGeometry(QtCore.QRect(736, 12, 77, 41))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self._status_textbox.setFont(font)
        self._status_textbox.setStyleSheet('background-color: rgb(255, 0, 0);')
        self._status_textbox.setObjectName('statusTextbox')
        self._status_textbox.setText('  Stopped')
        '''



    def _init_control_frame(self):
        
        # add control frame
        self._control_frame = QtWidgets.QFrame(self._central_widget)
        self._control_frame.setGeometry(QtCore.QRect(10, 76, 269, 269))
        self._control_frame.setStyleSheet('background-color: rgb(226, 255, 219);')
        self._control_frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self._control_frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self._control_frame.setObjectName('controlFrame')

        # data source tabs
        self._data_source_tabs = QtWidgets.QTabWidget(self._control_frame)
        self._data_source_tabs.setEnabled(True)
        self._data_source_tabs.setGeometry(QtCore.QRect(14, 92, 243, 157))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self._data_source_tabs.setFont(font)
        self._data_source_tabs.setAutoFillBackground(False)
        self._data_source_tabs.setStyleSheet('')
        self._data_source_tabs.setTabPosition(QtWidgets.QTabWidget.North)
        self._data_source_tabs.setTabShape(QtWidgets.QTabWidget.Rounded)
        self._data_source_tabs.setIconSize(QtCore.QSize(16, 16))
        self._data_source_tabs.setElideMode(QtCore.Qt.ElideNone)
        self._data_source_tabs.setUsesScrollButtons(False)
        self._data_source_tabs.setDocumentMode(False)
        self._data_source_tabs.setTabsClosable(False)
        self._data_source_tabs.setTabBarAutoHide(False)
        self._data_source_tabs.setObjectName('sourceTabs')
       

          
        # -------------
        # NI device tab
        # -------------
        self._niadc_tab = QtWidgets.QWidget()
        self._niadc_tab.setEnabled(True)
        self._niadc_tab.setStyleSheet('background-color: rgb(243, 255, 242);')
        self._niadc_tab.setObjectName('deviceTab')
        self._data_source_tabs.addTab(self._niadc_tab, 'Device')
      

        # Trace length
        trace_length_label = QtWidgets.QLabel(self._niadc_tab)
        trace_length_label.setGeometry(QtCore.QRect(5, 2, 131, 37))
        trace_length_label.setFont(font)
        trace_length_label.setText('Length [ms]')

        self._trace_length_spinbox = QtWidgets.QSpinBox(self._niadc_tab)
        self._trace_length_spinbox.setGeometry(QtCore.QRect(5, 32, 95, 21))
        self._trace_length_spinbox.setMaximum(100000)
        self._trace_length_spinbox.setProperty('value', 10.0)
        self._trace_length_spinbox.setObjectName('traceLengthSpinBox')
        
        # Sample Rate
        sample_rate_label = QtWidgets.QLabel(self._niadc_tab)
        sample_rate_label.setGeometry(QtCore.QRect(5, 60, 131, 37))
        sample_rate_label.setFont(font)
        sample_rate_label.setText('SampleRate [Hz]')
        
        self._sample_rate_spinbox = QtWidgets.QSpinBox(self._niadc_tab)
        self._sample_rate_spinbox.setGeometry(QtCore.QRect(5, 90, 95, 21))
        self._sample_rate_spinbox.setMaximum(3500000)
        self._sample_rate_spinbox.setProperty('value', 1250000)
        self._sample_rate_spinbox.setObjectName('sampleRateSpinBox')
        

        # separator
        
        separator = QtWidgets.QFrame(self._niadc_tab)
        separator.setFrameShape(QtWidgets.QFrame.VLine)
        separator.setFrameShadow(QtWidgets.QFrame.Sunken)
        separator.setGeometry(QtCore.QRect(125, 10, 2, 110))
      
    

        # trigger
        trigger_label = QtWidgets.QLabel(self._niadc_tab)
        trigger_label.setGeometry(QtCore.QRect(135, 2, 131, 37))
        trigger_label.setFont(font)
        trigger_label.setText('Trigger')


        self._trigger_combobox = QtWidgets.QComboBox(self._niadc_tab)
        self._trigger_combobox.setGeometry(QtCore.QRect(135, 33, 96, 20))
        self._trigger_combobox.setFont(font)
        self._trigger_combobox.addItem('Random')
        self._trigger_combobox.addItem('ExtTrig')
        self._trigger_combobox.addItem('Threshold')
        self._trigger_combobox.setCurrentIndex(0)



        self._voltage_min_combobox = QtWidgets.QComboBox(self._niadc_tab)
        self._voltage_min_combobox.setGeometry(QtCore.QRect(176, 70, 54, 23))
        self._voltage_min_combobox.setFont(font)
        self._voltage_min_combobox.addItem('-1')
        self._voltage_min_combobox.addItem('-2')
        self._voltage_min_combobox.addItem('-5')
        self._voltage_min_combobox.addItem('-10')
        self._voltage_min_combobox.setCurrentIndex(2)

        self._voltage_max_combobox = QtWidgets.QComboBox(self._niadc_tab)
        self._voltage_max_combobox.setGeometry(QtCore.QRect(176, 95, 54, 23))
        self._voltage_max_combobox.setFont(font)
        self._voltage_max_combobox.addItem('+1')
        self._voltage_max_combobox.addItem('+2')
        self._voltage_max_combobox.addItem('+5')
        self._voltage_max_combobox.addItem('+10')
        self._voltage_max_combobox.setCurrentIndex(2)

    
        voltage_min_label = QtWidgets.QLabel(self._niadc_tab)
        voltage_min_label.setGeometry(QtCore.QRect(134, 65, 38, 30))
        voltage_min_label.setFont(font)
        voltage_min_label.setText('Vmin:')

        voltage_max_label = QtWidgets.QLabel(self._niadc_tab)
        voltage_max_label.setGeometry(QtCore.QRect(131, 91, 41, 30))
        voltage_max_label.setFont(font)
        voltage_max_label.setText('Vmax:')

    

        # --------
        # HDF5 tab
        # --------
        self._hdf5_tab = QtWidgets.QWidget()
        self._hdf5_tab.setEnabled(True)
        self._hdf5_tab.setStyleSheet('background-color: rgb(243, 255, 242);')
        self._hdf5_tab.setObjectName('hdf5Tab')
        self._data_source_tabs.addTab(self._hdf5_tab, 'HDF5')
        
        
        self._hdf5_file_radiobutton =  QtWidgets.QRadioButton(self._hdf5_tab)
        self._hdf5_file_radiobutton.setGeometry(QtCore.QRect(120, 40, 101, 25))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self._hdf5_file_radiobutton.setFont(font)
        self._hdf5_file_radiobutton.setText('Files')
        self._hdf5_file_radiobutton.setChecked(True)

        self._hdf5_dir_radiobutton =  QtWidgets.QRadioButton(self._hdf5_tab)
        self._hdf5_dir_radiobutton.setGeometry(QtCore.QRect(120, 65, 101, 25))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self._hdf5_dir_radiobutton.setFont(font)
        self._hdf5_dir_radiobutton.setText('Directory')
        



        self._hdf5_select_button = QtWidgets.QPushButton(self._hdf5_tab)
        self._hdf5_select_button.setGeometry(QtCore.QRect(36, 32, 71, 65))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self._hdf5_select_button.setFont(font)
        self._hdf5_select_button.setStyleSheet('background-color: rgb(162, 162, 241);')
        self._hdf5_select_button.setObjectName('fileSelectButton')
        self._hdf5_select_button.setText('Select \n' 'Files/Dir')


      
        # ---------
        # Redis tab
        # ---------
        self._redis_tab = QtWidgets.QWidget()
        font = QtGui.QFont()
        font.setStrikeOut(False)
        font.setKerning(True)
        self._redis_tab.setFont(font)
        self._redis_tab.setLayoutDirection(QtCore.Qt.LeftToRight)
        self._redis_tab.setAutoFillBackground(False)
        self._redis_tab.setStyleSheet('background-color: rgb(243, 255, 242);')
        self._redis_tab.setObjectName('redisTab')
        self._data_source_tabs.addTab(self._redis_tab, 'Redis')
        
       
        # Set Visibility
        
        self._data_source_tabs.setTabVisible(0,True)
        self._data_source_tabs.setTabVisible(1,False)
        self._data_source_tabs.setTabVisible(2,False)


        
        # -----------------
        # source selection combox box
        # -----------------
        self._source_combobox = QtWidgets.QComboBox(self._control_frame)
        self._source_combobox.setGeometry(QtCore.QRect(10, 36, 110, 23))
        font = QtGui.QFont()
        font.setBold(False)
        font.setWeight(50)
        self._source_combobox.setFont(font)
        self._source_combobox.setObjectName('sourceComboBox')
        self._source_combobox.addItem('Device')
        self._source_combobox.addItem('HDF5')
        self._source_combobox.addItem('Redis')

        # combo box label
        source_label = QtWidgets.QLabel(self._control_frame)
        source_label.setGeometry(QtCore.QRect(12, 16, 100, 15))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        source_label.setFont(font)
        source_label.setObjectName('sourceLabel')
        source_label.setText('Data Source:')


        # --------------
        # display control
        # --------------
        self._display_control_button = QtWidgets.QPushButton(self._control_frame)
        self._display_control_button.setGeometry(QtCore.QRect(142, 15, 91, 65))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self._display_control_button.setFont(font)
        self._display_control_button.setStyleSheet('background-color: rgb(255, 0, 0);')
        self._display_control_button.setObjectName('displayControlButton')
        self._display_control_button.setText('Display \n Waveform')
    
        

        # ---------------
        # connect buttons
        # ---------------
        self._display_control_button.clicked.connect(self._handle_display)
        self._hdf5_select_button.clicked.connect(self._handle_hdf5_filedialog)
        self._hdf5_dir_radiobutton.toggled.connect(self._handle_hdf5_filedialog_type)
        self._source_combobox.activated.connect(self._handle_source_selection)
       
        
    def _init_display_frame(self):


        # frame
        self._display_frame = QtWidgets.QFrame(self._central_widget)
        self._display_frame.setGeometry(QtCore.QRect(290, 76, 597, 597))
        self._display_frame.setStyleSheet('background-color: rgb(254, 255, 216);')
        self._display_frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self._display_frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self._display_frame.setLineWidth(1)
        self._display_frame.setObjectName('DisplayFrame')
        

        font = QtGui.QFont()
        font.setBold(False)
        font.setWeight(75)

        # waveform type selection
        font.setBold(False)
        self._waveform_combobox = QtWidgets.QComboBox(self._display_frame)
        self._waveform_combobox.setGeometry(QtCore.QRect(10, 30, 100, 25))
        self._waveform_combobox.setFont(font)
        self._waveform_combobox.setStyleSheet("QComboBox"
                                              "{"
                                              "background-color: lightblue;"
                                              "}") 
        self._waveform_combobox.setObjectName('waveformComboBox')
        self._waveform_combobox.addItem('Waveform')
        self._waveform_combobox.addItem('PSD')
       

        # unit
        font.setBold(True)
        unit_label = QtWidgets.QLabel(self._display_frame)
        unit_label.setGeometry(QtCore.QRect(122, 30, 31, 25))
        unit_label.setFont(font)
        unit_label.setText('Unit:')


        font.setBold(False)
        self._unit_combobox = QtWidgets.QComboBox(self._display_frame)
        self._unit_combobox.setGeometry(QtCore.QRect(159, 30, 80, 25))
        self._unit_combobox.setFont(font)
        self._unit_combobox.setStyleSheet("QComboBox"
                                          "{"
                                          "background-color: lightgreen;"
                                          "}") 
        self._unit_combobox.setObjectName('unitComboBox')
        self._unit_combobox.addItem('ADC')
        self._unit_combobox.addItem('Volts')
        self._unit_combobox.addItem('mVolts')
        self._unit_combobox.addItem('nVolts')
        self._unit_combobox.addItem('Amps')
        self._unit_combobox.addItem('uAmps')
        self._unit_combobox.addItem('pAmps')
        self._unit_combobox.addItem('Watts')
        self._unit_combobox.addItem('pWatts')
        self._unit_combobox.addItem('g')
        
       
        # norm
        font.setBold(True)
        norm_label = QtWidgets.QLabel(self._display_frame)
        norm_label.setGeometry(QtCore.QRect(254, 30, 60, 25))
        norm_label.setFont(font)
        norm_label.setText('Norm:')


        font.setBold(False)
        self._norm_combobox = QtWidgets.QComboBox(self._display_frame)
        self._norm_combobox.setGeometry(QtCore.QRect(300, 30, 171, 25))
        self._norm_combobox.setStyleSheet("QComboBox"
                                          "{"
                                          "background-color: lightgreen;"
                                          "}") 
        self._norm_combobox.setFont(font)
        self._norm_combobox.setObjectName('normComboBox')
        self._norm_combobox.addItem('None')
        #self._norm_combobox.addItem('OpenLoop')
        #self._norm_combobox.addItem('CloseLoop')
    

        # auto_scale
        font.setBold(True)
        self._auto_scale_checkbox =  QtWidgets.QCheckBox(self._display_frame)
        self._auto_scale_checkbox.setGeometry(QtCore.QRect(490, 30, 101, 25))
        self._auto_scale_checkbox.setFont(font)
        self._auto_scale_checkbox.setText('Auto Scale')
        self._auto_scale_checkbox.setChecked(True)




        # canvas
        self._fig = Figure((2.7,2.7), dpi=100)
        #self._fig, self._axes = plt.subplots(sharex=False)
        self._axes = self._fig.add_subplot(111)
        #self._fig.subplots_adjust(hspace=.3)
        self._canvas = FigureCanvas(self._fig)
        #self._canvas.setParent(self._display_frame)
        self._canvas_toolbar = NavigationToolbar(self._canvas,self._display_frame)

        # canvas layout
        canvas_layout_widget = QtWidgets.QWidget(self._display_frame)
        canvas_layout_widget.setGeometry(QtCore.QRect(12, 61, 574, 520))
        vbox = QtWidgets.QVBoxLayout(canvas_layout_widget)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.addWidget(self._canvas)
        vbox.addWidget(self._canvas_toolbar)
    



        
        # connect
        self._waveform_combobox.currentIndexChanged.connect(self._handle_waveform_type)
        self._unit_combobox.currentIndexChanged.connect(self._handle_waveform_unit)
        self._norm_combobox.activated.connect(self._handle_waveform_norm)
        self._auto_scale_checkbox.toggled.connect(self._handle_auto_scale)

    def _init_channel_frame(self):
        
        # channel frame
        self._channel_frame = QtWidgets.QFrame(self._central_widget)
        self._channel_frame.setGeometry(QtCore.QRect(10, 352, 269, 161))
        self._channel_frame.setStyleSheet('background-color: rgb(226, 255, 219);')
        self._channel_frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self._channel_frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self._channel_frame.setLineWidth(2)
        self._channel_frame.setObjectName('ChannelFrame')

        # set grid layout
        channel_layout = QtWidgets.QWidget(self._channel_frame)
        channel_layout.setGeometry(QtCore.QRect(8, 11, 254, 137))
        channel_layout.setObjectName('layoutWidget')
     

        # add grid layout 
        channel_grid_layout = QtWidgets.QGridLayout(channel_layout)
        channel_grid_layout.setContentsMargins(0, 0, 0, 0)
        channel_grid_layout.setObjectName('gridLayout')
        
        # add buttons
        self._channel_buttons = dict()
        row_num = 0
        col_num = 0
        for ichan in range(8):
            # create button
            button = QtWidgets.QPushButton(channel_layout)
            
            # size policy
        
            size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, 
                                                QtWidgets.QSizePolicy.Expanding)
            size_policy.setHorizontalStretch(0)
            size_policy.setVerticalStretch(0)
            size_policy.setHeightForWidth(button.sizePolicy().hasHeightForWidth())
            button.setSizePolicy(size_policy)
        
            # text font
            font = QtGui.QFont()
            font.setBold(True)
            font.setWeight(75)
            button.setFont(font)
            button.setText('AI' + str(ichan))
            button.setCheckable(True)
            button.toggle()
            # background color
            #color = self._channels_color_map[ichan]
            #color_str = 'rgb(' + str(color[0]) + ',' + str(color[1]) + ',' + str(color[2]) + ')' 
            #button.setStyleSheet('background-color: ' + color_str +';')
            button.setObjectName('chanButton_' + str(ichan))
            
            # layout
            channel_grid_layout.addWidget(button, row_num, col_num, 1, 1)
            row_num+=1
            if ichan==3:
                row_num = 0
                col_num = 1

            # connect 
            button.clicked.connect(self._handle_channel_selection)
            
            # save
            self._channel_buttons[ichan] = button




    def _init_tools_frame(self):
        
        # create frame
        self._tools_frame = QtWidgets.QFrame(self._central_widget)
        self._tools_frame.setGeometry(QtCore.QRect(10, 520, 269, 153))
        self._tools_frame.setStyleSheet('background-color: rgb(226, 255, 219);')
        self._tools_frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self._tools_frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self._tools_frame.setObjectName('ToolsFrame')

        # Add tools button
        self._tools_button = QtWidgets.QPushButton(self._tools_frame)
        self._tools_button.setGeometry(QtCore.QRect(156, 11, 89, 35))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        font.setPointSize(8)
        self._tools_button.setFont(font)
        self._tools_button.setStyleSheet('background-color: rgb(162, 162, 241);')
        self._tools_button.setObjectName('toolsButton')
        self._tools_button.setText('Analysis \n Tools')
       

        self._save_button = QtWidgets.QPushButton(self._tools_frame)
        self._save_button.setGeometry(QtCore.QRect(156, 106, 89, 35))
        self._save_button.setFont(font)
        self._save_button.setStyleSheet('background-color: rgb(162, 162, 241);')
        self._save_button.setObjectName('saveButton')
        self._save_button.setText('Save Data')
        self._save_button.setEnabled(True)


        self._read_board_button = QtWidgets.QPushButton(self._tools_frame)
        self._read_board_button.setGeometry(QtCore.QRect(156, 58, 89, 35))
        self._read_board_button.setFont(font)
        self._read_board_button.setStyleSheet('background-color: rgb(162, 162, 241);')
        self._read_board_button.setObjectName('readBoard')
        self._read_board_button.setText('Read \n from board')
        #self._read_board_button.setEnabled(False)
        
        # add running avg box
        self._running_avg_checkbox = QtWidgets.QCheckBox(self._tools_frame)
        self._running_avg_checkbox.setGeometry(QtCore.QRect(13, 15, 109, 21))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self._running_avg_checkbox.setFont(font)
        self._running_avg_checkbox.setObjectName('runningAvgCheckBox')
        self._running_avg_checkbox.setText('Running Avg')

        # running avg spin box
        self._running_avg_spinbox = QtWidgets.QSpinBox(self._tools_frame)
        self._running_avg_spinbox.setEnabled(False)
        self._running_avg_spinbox.setGeometry(QtCore.QRect(31, 39, 85, 21))
        self._running_avg_spinbox.setMaximum(500)
        self._running_avg_spinbox.setProperty('value', 1)
        self._running_avg_spinbox.setObjectName('runningAvgSpinBox')
        self._running_avg_spinbox.setEnabled(False)

               
        # add lopw pass filter
        self._lpfilter_checkbox = QtWidgets.QCheckBox(self._tools_frame)
        self._lpfilter_checkbox.setGeometry(QtCore.QRect(13, 86, 119, 21))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self._lpfilter_checkbox.setFont(font)
        self._lpfilter_checkbox.setObjectName('lpFilterCheckBox')
        self._lpfilter_checkbox.setText('LP Filter [kHz]')
        self._lpfilter_checkbox.setEnabled(False)

        # lp filter spin box
        self._lpfilter_spinbox = QtWidgets.QSpinBox(self._tools_frame)
        self._lpfilter_spinbox.setEnabled(False)
        self._lpfilter_spinbox.setGeometry(QtCore.QRect(34, 110, 83, 21))
        self._lpfilter_spinbox.setMinimum(1)
        self._lpfilter_spinbox.setMaximum(500)
        self._lpfilter_spinbox.setObjectName('lpFilterSpinBox')
        self._lpfilter_spinbox.setEnabled(False)
        

        # connect 
        self._running_avg_checkbox.toggled.connect(self._handle_running_avg)
        self._running_avg_spinbox.valueChanged.connect(self._handle_running_avg)
        self._save_button.clicked.connect(self._handle_save_data)
        self._tools_button.clicked.connect(self._show_tools)
        self._read_board_button.clicked.connect(self._handle_read_board)
        #self._lpfilter_checkbox.toggled.connect(self._handle_lpfilter)
     

    def _set_display_button(self, do_run):
        
        if do_run:
            self._display_control_button.setStyleSheet('background-color: rgb(0, 255, 0);')
            self._display_control_button.setText('Stop \n Display')
        else:
            self._display_control_button.setStyleSheet('background-color: rgb(255, 0, 0);')
            self._display_control_button.setText('Display \n Waveform')
        
        


    def _show_tools(self,checked):
        if self._tools is None:
            self._tools = ToolsWindow(readout=self._readout,
                                      unit_combobox=self._unit_combobox,
                                      running_avg_checkbox=self._running_avg_checkbox,
                                      running_avg_spinbox=self._running_avg_spinbox)
            
        self._tools.show()
        self._tools.setWindowState(QtCore.Qt.WindowActive)
        self._tools.setWindowState(QtCore.Qt.WindowNoState)



        
class ToolsWindow(QtWidgets.QWidget):
    
    def __init__(self, readout=None, unit_combobox=None,
                 running_avg_checkbox=None, running_avg_spinbox=None):
        super().__init__()

        #layout = QtWidgets.QVBoxLayout()
        #self.label = QtWidgets.QLabel("Another Window")
        #layout.addWidget(self.label)
        #self.setLayout(layout)

        self.resize(500, 510)
        self.setStyleSheet('background-color: rgb(211, 252, 255);')
        self.setWindowTitle('Tools')


        # readout
        self._readout = readout

        #ui
        self._unit_combobox = unit_combobox
        self._running_avg_checkbox = running_avg_checkbox
        self._running_avg_spinbox = running_avg_spinbox

        # construct frame
        self._main_frame = None
        self._init_frame()

        # register
        self._readout.register_tools_ui(self._fit_button, self._text_field,
                                        self._rshunt_spinbox, self._rp_spinbox,
                                        self._dt_spinbox, self._pileup_selection)

        
        

    def _handle_fit(self):
        """
        Do dIdV fit
        """
        
        
        # setup (should be done already)
        self._setup_didv_fit()

        
        # Update Fit button
        self._fit_button.setStyleSheet('background-color: rgb(250, 255, 0);')
        self._fit_button.setText('Fitting \n Be Patient!')
        self._fit_button.setEnabled(False)


        # update pole
        # 1pole fit
        if self._didv_fit_1pole.isChecked():
            self._readout.update_analysis_config(didv_1pole=True)
        else:
            self._readout.update_analysis_config(didv_1pole=False)

        # 2pole fit 
        if self._didv_fit_2pole.isChecked():
            self._readout.update_analysis_config(didv_2pole=True)
        else:
            self._readout.update_analysis_config(didv_2pole=False)

        # 3pole fit 
        if self._didv_fit_3pole.isChecked():
            self._readout.update_analysis_config(didv_3pole=True)
        else:
            self._readout.update_analysis_config(didv_3pole=False)



        
        # update parameters
        rp = float(self._rp_spinbox.value())/1000
        self._readout.update_analysis_config(rp=rp)

        dt = float(self._dt_spinbox.value())*1e-6
        self._readout.update_analysis_config(dt=dt)

        rshunt = float(self._rshunt_spinbox.value())/1000
        self._readout.update_analysis_config(rshunt=rshunt)

        if self._phase180_checkbox.isChecked():
            self._readout.update_analysis_config(add_180phase=True)
        else:
            self._readout.update_analysis_config(add_180phase=False)
            

        r0 = float(self._r0_spinbox.value()/1000)
        self._readout.update_analysis_config(r0=r0)

        # clear field
        self._text_field.clear()

        # enable 
        self._readout.update_analysis_config(fit_didv=True)
        
        
        
    def _handle_fit_selection(self):

        # 1pole fit
        if self._didv_fit_1pole.isChecked():
            self._readout.update_analysis_config(didv_1pole=True)
        else:
            self._readout.update_analysis_config(didv_1pole=False)

        # 2pole fit 
        if self._didv_fit_2pole.isChecked():
            self._readout.update_analysis_config(didv_2pole=True)
        else:
            self._readout.update_analysis_config(didv_2pole=False)

        # 3pole fit 
        if self._didv_fit_3pole.isChecked():
            self._readout.update_analysis_config(didv_3pole=True)
        else:
            self._readout.update_analysis_config(didv_3pole=False)
      

    def _handle_cuts(self):
        """
        Handle cut selection
        """
        cut_dict = dict()
        if self._minmax_checkbox.isChecked():
            sigma = int(self._minmax_spinbox.value())
            cut_dict['minmax'] = sigma

        if self._ofamp_checkbox.isChecked():
            sigma = int(self._ofamp_spinbox.value())
            cut_dict['ofamp'] = sigma

        if self._slope_checkbox.isChecked():
            sigma = int(self._slope_spinbox.value())
            cut_dict['slope'] = sigma

        if self._baseline_checkbox.isChecked():
            sigma = int(self._baseline_spinbox.value())
            cut_dict['baseline'] = sigma

        if self._ofchi2_checkbox.isChecked():
            sigma = int(self._ofchi2_spinbox.value())
            cut_dict['ofchi2'] = sigma


        self._readout.update_analysis_config(pileup_cuts=cut_dict)


        
    def _handle_pileup_rejection(self):
        """
        Handle pileup rejection enabling
        """

        # enable
        do_pileup_rejection = False
        if self._pileup_selection.isChecked():
            self._tools_tabs.setTabVisible(1, True)
            self._tools_tabs.setCurrentIndex(1)
            self._handle_cuts()
            do_pileup_rejection = True
        else:
            self._tools_tabs.setTabVisible(1, False)
            
        self._readout.update_analysis_config(enable_pileup_rejection=do_pileup_rejection)

            
            
    def _handle_measurement(self):
        """
        Handle measurement selection
        """

          
        selection = self._measurement_combobox.currentText()

        measurement = 'Rp'
        if selection == 'SC dIdV Fit' or selection == 'Normal dIdV Fit':
            self._setup_didv_fit()
            self._didv_fit_2pole.setChecked(False)
            self._didv_fit_2pole.setEnabled(False)
            self._didv_fit_3pole.setChecked(False)
            self._didv_fit_3pole.setEnabled(False)
            self._didv_fit_1pole.setEnabled(True)
            self._didv_fit_1pole.setChecked(True)
            if selection == 'SC dIdV Fit':
                self._tools_tabs.setTabText(0,'Rp Fit')
                self._rp_spinbox.setEnabled(False)
            else:
                self._tools_tabs.setTabText(0,'Rn Fit')
                self._rp_spinbox.setEnabled(True)
                measurement = 'Rn'
            self._tools_tabs.setTabVisible(0,True)
            self._tools_tabs.setCurrentIndex(0)
            self._r0_spinbox.setEnabled(False)
            
        elif selection == 'Transition dIdV Fit':
            self._setup_didv_fit()
            self._didv_fit_1pole.setChecked(False)
            self._didv_fit_1pole.setEnabled(False)
            self._didv_fit_2pole.setEnabled(True)
            self._didv_fit_2pole.setChecked(True)
            self._didv_fit_3pole.setEnabled(True)
            self._didv_fit_3pole.setChecked(True)
            self._tools_tabs.setTabText(0,'R0 Fit')
            self._rp_spinbox.setEnabled(True)
            self._r0_spinbox.setEnabled(True)
            self._tools_tabs.setTabVisible(0,True)
            self._tools_tabs.setCurrentIndex(0)
            measurement = 'R0'
                       
        else:
            self._didv_fit_1pole.setChecked(False)
            self._didv_fit_2pole.setChecked(False)
            self._didv_fit_3pole.setChecked(False)
            self._tools_tabs.setTabVisible(0,False)
            self._tools_tabs.setCurrentIndex(0)

        # clear field
        self._text_field.clear()

        # update readout
        self._readout.update_analysis_config(didv_measurement=measurement)



        
    def _setup_didv_fit(self):
        """
        Set units and running avg for dIdV"
        """


        # unit
        unit = str(self._unit_combobox.currentText())
        if unit.find('Amps')==-1:
            index = self._unit_combobox.findText('uAmps', QtCore.Qt.MatchFixedString)
            if index >= 0:
                self._unit_combobox.setCurrentIndex(index)
            # reset running avg
            self._readout.update_analysis_config(reset_running_avg=True)
                
        # running avg
        if not self._running_avg_checkbox.isChecked():
            self._running_avg_checkbox.setChecked(True)
                
        if int(self._running_avg_spinbox.value())<25:
            self._running_avg_spinbox.setValue(25)
        

        
        
    def _init_frame(self):

        # add main frame
        self._main_frame = QtWidgets.QFrame(self)
        self._main_frame.resize(500, 510)
        #self._main_frame.setGeometry(QtCore.QRect(290, 76, 597, 597))
        self._main_frame.setStyleSheet('background-color: rgb(211, 252, 255);')
        self._main_frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self._main_frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self._main_frame.setLineWidth(1)
        self._main_frame.setObjectName('MainFrame')



        # add pileup
         # 1 pole enable fit
        self._pileup_selection = QtWidgets.QCheckBox(self._main_frame)
        self._pileup_selection.setGeometry(QtCore.QRect(380, 25, 139, 41))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self._pileup_selection.setFont(font)
        self._pileup_selection.setObjectName('Pileup')
        self._pileup_selection.setText(' Pileup \n Rejection')
        self._pileup_selection.setEnabled(False)


        # line separator
        line_separator = QtWidgets.QFrame(self._main_frame)
        line_separator.setFrameShape(QtWidgets.QFrame.HLine)
        line_separator.setFrameShadow(QtWidgets.QFrame.Sunken)
        line_separator.setGeometry(QtCore.QRect(10, 95, 470, 5))


        # SQUID 
        self._squid_button = QtWidgets.QPushButton(self._main_frame)
        self._squid_button.setGeometry(QtCore.QRect(30, 15, 89, 55))
        self._squid_button.setFont(font)
        self._squid_button.setStyleSheet('background-color: rgb(162, 162, 241);')
        self._squid_button.setObjectName('squidButton')
        self._squid_button.setText('SQUID\nCheck')
        self._squid_button.setEnabled(False)

        # Zero Once
        self._zero_button = QtWidgets.QPushButton(self._main_frame)
        self._zero_button.setGeometry(QtCore.QRect(140, 15, 89, 55))
        self._zero_button.setFont(font)
        self._zero_button.setStyleSheet('background-color: rgb(162, 162, 241);')
        self._zero_button.setObjectName('zeroButton')
        self._zero_button.setText('ZERO\nOnce')
        self._zero_button.setEnabled(False)

        # Place holder
        self._notsure_button = QtWidgets.QPushButton(self._main_frame)
        self._notsure_button.setGeometry(QtCore.QRect(250, 15, 89, 55))
        self._notsure_button.setFont(font)
        self._notsure_button.setStyleSheet('background-color: rgb(162, 162, 241);')
        self._notsure_button.setObjectName('notsureButton')
        #self._notsure_button.setText('Whatever')
        self._notsure_button.setEnabled(False)

        
        
        
        
        
        # Add fit selection
        self._measurement_combobox = QtWidgets.QComboBox(self._main_frame)
        self._measurement_combobox.setGeometry(QtCore.QRect(155, 122, 170, 29))
        self._measurement_combobox.setObjectName('measurementComboBox')
        self._measurement_combobox.setStyleSheet("QComboBox"
                                          "{"
                                          "background-color: lightgreen;"
                                          "}") 
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(50)
        self._measurement_combobox.setFont(font)
        #self._measurement_combobox.setStyleSheet('background-color: rgb(226, 255, 219);')
        self._measurement_combobox.addItem('Select Measurement')  
        self._measurement_combobox.addItem('SC dIdV Fit')
        self._measurement_combobox.addItem('Normal dIdV Fit')
        self._measurement_combobox.addItem('Transition dIdV Fit')
        #self._measurement_combobox.setEnabled(False)
        
        # add tab
        self._tools_tabs = QtWidgets.QTabWidget(self._main_frame)
        self._tools_tabs.setEnabled(True)
        self._tools_tabs.setGeometry(QtCore.QRect(12, 170, 475, 325))
        font.setBold(True)
        font.setWeight(75)
        self._tools_tabs.setFont(font)
        self._tools_tabs.setAutoFillBackground(False)
        self._tools_tabs.setStyleSheet('')
        
        self._init_didv_tab()
        self._init_cuts_tab()
        self._tools_tabs.setTabVisible(0, False)
        self._tools_tabs.setTabVisible(1, False)
        
        # connect
        self._measurement_combobox.activated.connect(self._handle_measurement)
        self._pileup_selection.toggled.connect(self._handle_pileup_rejection)


        
    def _init_didv_tab(self):
        """
        dIdV measurement Tab
        """
        self._didv_tab = QtWidgets.QWidget()
        self._didv_tab.setEnabled(True)
        self._didv_tab.setStyleSheet('background-color: rgb(231, 252, 255);')
        self._didv_tab.setObjectName('deviceTab')
        self._tools_tabs.addTab(self._didv_tab, 'dIdV Fit')

        # font
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
                
        # poles  
        pole_label = QtWidgets.QLabel(self._didv_tab)
        pole_label.setGeometry(QtCore.QRect(14, 15, 40, 15))
        pole_label.setFont(font)
        pole_label.setObjectName('poleLabel')
        pole_label.setText('Poles:')


               
        # 1 pole enable fit
        self._didv_fit_1pole = QtWidgets.QCheckBox(self._didv_tab)
        self._didv_fit_1pole.setGeometry(QtCore.QRect(65,13, 30, 21))
        self._didv_fit_1pole.setFont(font)
        self._didv_fit_1pole.setObjectName('1pole_fit')
        self._didv_fit_1pole.setText('1')

        # 2 pole enable fit
        self._didv_fit_2pole = QtWidgets.QCheckBox(self._didv_tab)
        self._didv_fit_2pole.setGeometry(QtCore.QRect(100, 13, 30, 21))
        self._didv_fit_2pole.setFont(font)
        self._didv_fit_2pole.setObjectName('2pole_fit')
        self._didv_fit_2pole.setText('2')


        # 3 pole enable fit
        self._didv_fit_3pole = QtWidgets.QCheckBox(self._didv_tab)
        self._didv_fit_3pole.setGeometry(QtCore.QRect(135, 13, 30, 21))
        self._didv_fit_3pole.setFont(font)
        self._didv_fit_3pole.setObjectName('3pole_fit')
        self._didv_fit_3pole.setText('3')


        
        # Rshunt
        rshunt_label = QtWidgets.QLabel(self._didv_tab)
        rshunt_label.setGeometry(QtCore.QRect(14, 45, 60, 15))
        rshunt_label.setFont(font)
        rshunt_label.setObjectName('rshuntLabel')
        rshunt_label.setText('Rshunt:')

        self._rshunt_spinbox = QtWidgets.QDoubleSpinBox(self._didv_tab)
        self._rshunt_spinbox.setGeometry(QtCore.QRect(70, 42, 70, 20))
        self._rshunt_spinbox.setMaximum(100000)
        self._rshunt_spinbox.setProperty('value', 5.0)
        self._rshunt_spinbox.setObjectName('rshuntSpinBox')
        self._rshunt_spinbox.setDecimals(1)

        step_type = QtWidgets.QAbstractSpinBox.AdaptiveDecimalStepType
        self._rshunt_spinbox.setStepType(step_type)
        
        # Rp
        rp_label = QtWidgets.QLabel(self._didv_tab)
        rp_label.setGeometry(QtCore.QRect(42, 70, 50, 15))
        rp_label.setFont(font)
        rp_label.setObjectName('rpLabel')
        rp_label.setText('Rp:')

        self._rp_spinbox = QtWidgets.QDoubleSpinBox(self._didv_tab)
        self._rp_spinbox.setGeometry(QtCore.QRect(70, 67, 70, 20))
        self._rp_spinbox.setMaximum(100000)
        self._rp_spinbox.setProperty('value', 2.5)
        self._rp_spinbox.setObjectName('rpSpinBox')
        self._rp_spinbox.setDecimals(1)
        self._rp_spinbox.setStepType(step_type)



        # R0
        r0_label = QtWidgets.QLabel(self._didv_tab)
        r0_label.setGeometry(QtCore.QRect(42, 96, 50, 15))
        r0_label.setFont(font)
        r0_label.setObjectName('r0Label')
        r0_label.setText('R0:')

        self._r0_spinbox = QtWidgets.QDoubleSpinBox(self._didv_tab)
        self._r0_spinbox.setGeometry(QtCore.QRect(70, 92, 70, 20))
        self._r0_spinbox.setMaximum(100000)
        self._r0_spinbox.setProperty('value', 200)
        self._r0_spinbox.setObjectName('r0SpinBox')
        self._r0_spinbox.setDecimals(1)
        self._r0_spinbox.setStepType(step_type)






        
        unit_label = QtWidgets.QLabel(self._didv_tab)
        unit_label.setGeometry(QtCore.QRect(150, 70, 60, 15))
        unit_label.setFont(font)
        unit_label.setObjectName('rshuntUniyLabel')
        unit_label.setText('[mOhms]')


        # dt
        dt_label = QtWidgets.QLabel(self._didv_tab)
        dt_label.setGeometry(QtCore.QRect(39, 120, 50, 15))
        dt_label.setFont(font)
        dt_label.setObjectName('dtLabel')
        dt_label.setText('dt0:')

        self._dt_spinbox = QtWidgets.QDoubleSpinBox(self._didv_tab)
        self._dt_spinbox.setGeometry(QtCore.QRect(70, 117, 70, 20))
        self._dt_spinbox.setMaximum(100000)
        self._dt_spinbox.setProperty('value', 2)
        self._dt_spinbox.setObjectName('dtSpinBox')
        self._dt_spinbox.setDecimals(1)
        self._dt_spinbox.setStepType(step_type)

        dt_unit_label = QtWidgets.QLabel(self._didv_tab)
        dt_unit_label.setGeometry(QtCore.QRect(150, 118, 60, 15))
        dt_unit_label.setFont(font)
        dt_unit_label.setObjectName('dtUniyLabel')
        dt_unit_label.setText('[mus]')
        
        # add phase
        self._phase180_checkbox = QtWidgets.QCheckBox(self._didv_tab)
        self._phase180_checkbox.setGeometry(QtCore.QRect(215, 117, 149, 21))
        self._phase180_checkbox.setFont(font)
        self._phase180_checkbox.setObjectName('phase180CheckBox')
        self._phase180_checkbox.setText('Add 180 Phase')

        


        self._fit_button = QtWidgets.QPushButton(self._didv_tab)
        self._fit_button.setGeometry(QtCore.QRect(295, 35, 89, 55))
        self._fit_button.setFont(font)
        self._fit_button.setStyleSheet('background-color: rgb(162, 162, 241);')
        self._fit_button.setObjectName('fitButton')
        self._fit_button.setText('FIT')
        self._fit_button.setEnabled(True)


        self._text_field = QtWidgets.QTextEdit(self._didv_tab)
        self._text_field.setGeometry(QtCore.QRect(80, 150, 365, 138))
        self._text_field.setReadOnly(True)

        self._save_result_button = QtWidgets.QPushButton(self._didv_tab)
        self._save_result_button.setGeometry(QtCore.QRect(10, 185, 50, 40))
        font.setPointSize(7)
        self._save_result_button.setFont(font)
        self._save_result_button.setStyleSheet('background-color: rgb(162, 162, 241);')
        self._save_result_button.setObjectName('saveButton')
        self._save_result_button.setText('Save \n Results')
        self._save_result_button.setEnabled(True)

        
        # connect
        #self._rshunt_spinbox.valueChanged.connect(self._handle_fit_parameter)
        #self._rp_spinbox.valueChanged.connect(self._handle_fit_parameter)
        #self._dt_spinbox.valueChanged.connect(self._handle_fit_parameter)
        #self._didv_fit_1pole.toggled.connect(self._handle_fit_selection)
        #self._didv_fit_2pole.toggled.connect(self._handle_fit_selection)
        #self._didv_fit_3pole.toggled.connect(self._handle_fit_selection)
        self._fit_button.clicked.connect(self._handle_fit)


    def _init_cuts_tab(self):
        """
        Pileup Rejection cuts
        """
        self._pileup_cuts_tab = QtWidgets.QWidget()
        self._pileup_cuts_tab.setEnabled(True)
        self._pileup_cuts_tab.setStyleSheet('background-color: rgb(231, 252, 255);')
        self._pileup_cuts_tab.setObjectName('pileupTab')
        self._tools_tabs.addTab(self._pileup_cuts_tab, 'Pileup Cuts')
        
        # font
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)


        # Title  Label
        
        cut_title_label = QtWidgets.QLabel(self._pileup_cuts_tab)
        cut_title_label.setGeometry(QtCore.QRect(10, 20, 250, 15))
        cut_title_label.setFont(font)
        cut_title_label.setObjectName('cutsLabel')
        cut_title_label.setText('Cut name and sigma (ordered!):')

        
        # Minmax cut
        self._minmax_checkbox = QtWidgets.QCheckBox(self._pileup_cuts_tab)
        self._minmax_checkbox.setGeometry(QtCore.QRect(15, 50, 120, 21))
        self._minmax_checkbox.setFont(font)
        self._minmax_checkbox.setObjectName('minmaxCheckBox')
        self._minmax_checkbox.setText('MinMax')
        self._minmax_checkbox.setChecked(True)

        # Minmax sigma
        self._minmax_spinbox = QtWidgets.QSpinBox(self._pileup_cuts_tab)
        self._minmax_spinbox.setGeometry(QtCore.QRect(150, 50, 40, 20))
        self._minmax_spinbox.setMaximum(10)
        self._minmax_spinbox.setProperty('value', 2)
        self._minmax_spinbox.setObjectName('minmaxSpinBox')
        

        # OF Amp cut
        self._ofamp_checkbox = QtWidgets.QCheckBox(self._pileup_cuts_tab)
        self._ofamp_checkbox.setGeometry(QtCore.QRect(15, 80, 120, 21))
        self._ofamp_checkbox.setFont(font)
        self._ofamp_checkbox.setObjectName('ofampCheckBox')
        self._ofamp_checkbox.setText('OF Amplitude')

        # OF Amp sigma
        self._ofamp_spinbox = QtWidgets.QSpinBox(self._pileup_cuts_tab)
        self._ofamp_spinbox.setGeometry(QtCore.QRect(150, 80, 40, 20))
        self._ofamp_spinbox.setMaximum(10)
        self._ofamp_spinbox.setProperty('value', 2)
        self._ofamp_spinbox.setObjectName('ofampSpinBox')
        
        # Slope cut
        self._slope_checkbox = QtWidgets.QCheckBox(self._pileup_cuts_tab)
        self._slope_checkbox.setGeometry(QtCore.QRect(15, 110, 120, 21))
        self._slope_checkbox.setFont(font)
        self._slope_checkbox.setObjectName('slopeCheckBox')
        self._slope_checkbox.setText('Slope')

        # Slope sigma
        self._slope_spinbox = QtWidgets.QSpinBox(self._pileup_cuts_tab)
        self._slope_spinbox.setGeometry(QtCore.QRect(150, 110, 40, 20))
        self._slope_spinbox.setMaximum(10)
        self._slope_spinbox.setProperty('value', 2)
        self._slope_spinbox.setObjectName('slopeSpinBox')
        


        # Baseline cut
        self._baseline_checkbox = QtWidgets.QCheckBox(self._pileup_cuts_tab)
        self._baseline_checkbox.setGeometry(QtCore.QRect(15, 140, 120, 21))
        self._baseline_checkbox.setFont(font)
        self._baseline_checkbox.setObjectName('baselineCheckBox')
        self._baseline_checkbox.setText('Baseline')

        # Baseline sigma
        self._baseline_spinbox = QtWidgets.QSpinBox(self._pileup_cuts_tab)
        self._baseline_spinbox.setGeometry(QtCore.QRect(150, 140, 40, 20))
        self._baseline_spinbox.setMaximum(10)
        self._baseline_spinbox.setProperty('value', 2)
        self._baseline_spinbox.setObjectName('baselineSpinBox')
        

        # OF chi2 cut
        self._ofchi2_checkbox = QtWidgets.QCheckBox(self._pileup_cuts_tab)
        self._ofchi2_checkbox.setGeometry(QtCore.QRect(15, 170, 120, 21))
        self._ofchi2_checkbox.setFont(font)
        self._ofchi2_checkbox.setObjectName('ofchi2CheckBox')
        self._ofchi2_checkbox.setText('OF Chi2')

        # Ofchi2 sigma
        self._ofchi2_spinbox = QtWidgets.QSpinBox(self._pileup_cuts_tab)
        self._ofchi2_spinbox.setGeometry(QtCore.QRect(150, 170, 40, 20))
        self._ofchi2_spinbox.setMaximum(10)
        self._ofchi2_spinbox.setProperty('value', 3)
        self._ofchi2_spinbox.setObjectName('ofchi2SpinBox')
        

        # connect
        self._minmax_checkbox.toggled.connect(self._handle_cuts)
        self._ofamp_checkbox.toggled.connect(self._handle_cuts)
        self._ofchi2_checkbox.toggled.connect(self._handle_cuts)
        self._slope_checkbox.toggled.connect(self._handle_cuts)
        self._baseline_checkbox.toggled.connect(self._handle_cuts)
        self._minmax_spinbox.valueChanged.connect(self._handle_cuts)
        self._ofamp_spinbox.valueChanged.connect(self._handle_cuts)
        self._ofchi2_spinbox.valueChanged.connect(self._handle_cuts)
        self._slope_spinbox.valueChanged.connect(self._handle_cuts)
        self._baseline_spinbox.valueChanged.connect(self._handle_cuts)

        
        
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    ui = MainWindow()
    sys.exit(app.exec_())
