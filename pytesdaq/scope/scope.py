"""
Main Frame Window
"""
import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from matplotlib import pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT  as NavigationToolbar
from matplotlib.figure import Figure
from pytesdaq.scope import readout
from glob import glob
import os,time

class MainWindow(QtWidgets.QMainWindow):
    
    def __init__(self):
        super().__init__()
        
       

        # initialize attribute
        self._data_source = 'niadc'
        self._file_list = list()
        self._select_hdf5_dir = False
        self._default_data_dir = './'


        # initalize main window
        self.setWindowModality(QtCore.Qt.NonModal)
        self.resize(900, 700)
        self.setStyleSheet('background-color: rgb(211, 252, 255);')
        self.setTabShape(QtWidgets.QTabWidget.Rounded)
        self.setWindowTitle('Pulse Viewer')



        # channel color map
        self._channels_color_map = {0:(0, 85, 255),
                                    1:(255, 0, 0),
                                    2:(0, 170, 127),
                                    3:(170, 0, 255),
                                    4:(170, 116, 28),
                                    5:(15, 235, 255),
                                    6:(255, 207, 32),
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

        # tools
        self._tools = None


        
        # show
        self.show()
        

        # run control
        self._is_running = False
        self._stop_request = False
   
        
        # initialize readout
        self._readout = readout.Readout()
        self._readout.register_ui(self._axes,self._canvas, self.statusBar(),
                                  self._channels_color_map)
        


   
        
    def closeEvent(self,event):
        """
        This function is called when exiting window
        superse base class
        """

               
        if self._is_running:
            self._readout.stop_run()
            
            # wait (needed?)
            for ii in range(10):
                time.sleep(0.01)
                
        
        self._tools = None
        print('Exiting Pulse Display UI')
        



    def _handle_display(self):
        """
        Handle display. Called when clicking on display waveform 
        """


        if self._is_running:

            # Stop run
            self._readout.stop_run()
            self._is_running=False

            # change button display
            self._set_display_button(False)

            # enable
            self._data_source_tabs.setEnabled(True)
            self._source_combobox.setEnabled(True)

            # status bar
            self.statusBar().showMessage('Display Stopped')
          
            
        else:

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
                status = self._readout.configure('niadc',adc_name=adc_name,channel_list=channel_list,
                                                 sample_rate=sample_rate, trace_length=trace_length,
                                                 voltage_min=voltage_min, voltage_max=voltage_max,
                                                 trigger_type=trigger_type)
                
                # error
                if isinstance(status,str):
                    self.statusBar().showMessage(status)
                    return

            elif self._data_source  == 'hdf5':
                
                # check selection done
                if not self._file_list:
                    self.statusBar().showMessage('WARNING: No files selected!')  
                    return

                status = self._readout.configure('hdf5', file_list = self._file_list)

                # error
                if isinstance(status,str):
                    self.statusBar().showMessage(status)
                    return
            
            else:
                self.statusBar().showMessage('WARNING: Redis not implemented')  
                return


            # reset runing avg
            self._readout.update_analysis_config(reset_running_avg=True)


            
            # status bar
            self.statusBar().showMessage('Running...')
          

            # disable 
            self._data_source_tabs.setEnabled(False)
            self._source_combobox.setEnabled(False)


            # run 
            self._set_display_button(True)
            self._is_running=True
            self._readout.run(do_plot=True)


            # status bar
            self.statusBar().showMessage('Run stopped...')
          

            # change status
            self._set_display_button(False)
            self._is_running=False
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
            
            
        elif data_source== 'HDF5':
            
            self._data_source  = 'hdf5'
            
            # visibility
            self._data_source_tabs.setTabVisible(0,False)
            self._data_source_tabs.setTabVisible(1,True)
            self._data_source_tabs.setTabVisible(2,False)

            # set current
            self._data_source_tabs.setCurrentWidget(self._hdf5_tab)

        elif data_source== 'Device':
            
            self._data_source  = 'niadc'

            # visibility
            self._data_source_tabs.setTabVisible(0,True)
            self._data_source_tabs.setTabVisible(1,False)
            self._data_source_tabs.setTabVisible(2,False)

            # set current
            self._data_source_tabs.setCurrentWidget(self._niadc_tab)

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
            files, _ = QtWidgets.QFileDialog.getOpenFileNames(self,'Select File (s)',self._default_data_dir,
                                                              'HDF5 Files (*.hdf5)', options=options)
        else:
            options |= QtWidgets.QFileDialog.ShowDirsOnly  | QtWidgets.QFileDialog.DontResolveSymlinks
            dir = QtWidgets.QFileDialog.getExistingDirectory(self,'Select Directory',
                                                             self._default_data_dir,options=options)
                                 

            if os.path.isdir(dir):
                files = glob(dir+'/*_F*.hdf5')

        if not files:
            self.statusBar().showMessage('No file have been selected!')
        else:
            self.statusBar().showMessage('Number of files selected = ' + str(len(files)))
            self._file_list = files
            self._file_list.sort()



    def _handle_save_data(self):

        # select directory
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(self,'Choose file name to save to',self._default_data_dir,
                                                        'Numpy File (*.npy)', options=options)
        

        self._readout.save_data(filename)
        


            

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

        if self._readout:
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
            norm = 'None'
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
                norm = 'None'
        elif (unit=='Amps' or unit=='pAmps' or unit=='Watts' or unit=='pWatts'):
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
        self._readout.update_analysis_config(unit=unit, norm=norm)
        




    def _handle_waveform_norm(self):
        """
        Handle waveform type and unit selection (Signal/Slot connection)
        """

             
        # norm 
        norm = str(self._norm_combobox.currentText())

        # update analysis
        self._readout.update_analysis_config(norm=norm)



    def _handle_auto_scale(self):
        
        enable_auto_scale = False
        if self._auto_scale_checkbox.isChecked():
            enable_auto_scale = True
        self._readout.set_auto_scale(enable_auto_scale)
        


    def _handle_running_avg(self):
        
        if self._running_avg_checkbox.isChecked():
            self._running_avg_spinbox.setEnabled(True)
            value = int(self._running_avg_spinbox.value())
            self._readout.update_analysis_config(enable_running_avg = True, nb_events_avg=value)
        else:
            #self._running_avg_spinbox.setProperty('value', 1)
            self._running_avg_spinbox.setEnabled(False)
            self._readout.update_analysis_config(enable_running_avg = False)



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
        self._trace_length_spinbox.setProperty('value', 10)
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
        self._display_control_button.setText('Display \n' 'Waveform')
    
        

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
        self._waveform_combobox.activated.connect(self._handle_waveform_type)
        self._unit_combobox.activated.connect(self._handle_waveform_unit)
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
        self._tools_button.setGeometry(QtCore.QRect(156, 25, 89, 50))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self._tools_button.setFont(font)
        self._tools_button.setStyleSheet('background-color: rgb(162, 162, 241);')
        self._tools_button.setObjectName('toolsButton')
        self._tools_button.setText('Tools')
        #self._tools_button.setEnabled(False)

        self._save_button = QtWidgets.QPushButton(self._tools_frame)
        self._save_button.setGeometry(QtCore.QRect(156, 90, 89, 40))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self._save_button.setFont(font)
        self._save_button.setStyleSheet('background-color: rgb(162, 162, 241);')
        self._save_button.setObjectName('saveButton')
        self._save_button.setText('Save Data')
        self._save_button.setEnabled(True)



        
        # add running avg box
        self._running_avg_checkbox = QtWidgets.QCheckBox(self._tools_frame)
        self._running_avg_checkbox.setGeometry(QtCore.QRect(16, 16, 109, 21))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self._running_avg_checkbox.setFont(font)
        self._running_avg_checkbox.setObjectName('runningAvgCheckBox')
        self._running_avg_checkbox.setText('Running Avg')

        # running avg spin box
        self._running_avg_spinbox = QtWidgets.QSpinBox(self._tools_frame)
        self._running_avg_spinbox.setEnabled(False)
        self._running_avg_spinbox.setGeometry(QtCore.QRect(34, 40, 85, 21))
        self._running_avg_spinbox.setMaximum(500)
        self._running_avg_spinbox.setProperty('value', 1)
        self._running_avg_spinbox.setObjectName('runningAvgSpinBox')
        self._running_avg_spinbox.setEnabled(False)


        # add lopw pass filter
        self._lpfilter_checkbox = QtWidgets.QCheckBox(self._tools_frame)
        self._lpfilter_checkbox.setGeometry(QtCore.QRect(16, 76, 119, 21))
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
        self._lpfilter_spinbox.setGeometry(QtCore.QRect(34, 100, 83, 21))
        self._lpfilter_spinbox.setMinimum(1)
        self._lpfilter_spinbox.setMaximum(500)
        self._lpfilter_spinbox.setObjectName('lpFilterSpinBox')
        self._lpfilter_spinbox.setEnabled(False)
        

        # connect 
        self._running_avg_checkbox.toggled.connect(self._handle_running_avg)
        self._running_avg_spinbox.valueChanged.connect(self._handle_running_avg)
        self._save_button.clicked.connect(self._handle_save_data)
        self._tools_button.clicked.connect(self._show_tools)
        #self._lpfilter_checkbox.toggled.connect(self._handle_lpfilter)



    def _set_display_button(self,do_run):
        
        if do_run:
            self._display_control_button.setStyleSheet('background-color: rgb(0, 255, 0);')
            self._display_control_button.setText('Stop \n' 'Display')
        else:
            self._display_control_button.setStyleSheet('background-color: rgb(255, 0, 0);')
            self._display_control_button.setText('Display \n' 'Waveform')
        
        


    def _show_tools(self,checked):
        if self._tools is None:
            self._tools = ToolsWindow(readout=self._readout)
            
        self._tools.show()
        self._tools.setWindowState(QtCore.Qt.WindowActive)
        self._tools.setWindowState(QtCore.Qt.WindowNoState)



        
class ToolsWindow(QtWidgets.QWidget):
    
    def __init__(self, readout=None):
        super().__init__()

        #layout = QtWidgets.QVBoxLayout()
        #self.label = QtWidgets.QLabel("Another Window")
        #layout.addWidget(self.label)
        #self.setLayout(layout)

        self.resize(400, 300)
        self.setStyleSheet('background-color: rgb(211, 252, 255);')
        self.setWindowTitle('Tools')


        # readout
        self._readout = readout

        # construct frame
        self._main_frame = None
        self._init_frame()
    


    def _handle_read_board(self):
        self._readout.read_from_board()
        
        print('Read from board')
        


        
    def _init_frame(self):

        # add main frame
        self._main_frame = QtWidgets.QFrame(self)
        self._main_frame.resize(400, 300)
        #self._main_frame.setGeometry(QtCore.QRect(290, 76, 597, 597))
        self._main_frame.setStyleSheet('background-color: rgb(211, 252, 255);')
        self._main_frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self._main_frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self._main_frame.setLineWidth(1)
        self._main_frame.setObjectName('MainFrame')
        

        
        # Add tools button
        self._read_board_button = QtWidgets.QPushButton(self._main_frame)
        self._read_board_button.setGeometry(QtCore.QRect(156, 15, 89, 50))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self._read_board_button.setFont(font)
        self._read_board_button.setStyleSheet('background-color: rgb(162, 162, 241);')
        self._read_board_button.setObjectName('readBoard')
        self._read_board_button.setText('Read \n from board')



        # connect
        self._read_board_button.clicked.connect(self._handle_read_board)

        
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    ui = MainWindow()
    sys.exit(app.exec_())
