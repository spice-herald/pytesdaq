"""
Main Frame Window
"""
import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from matplotlib import pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT  as NavigationToolbar
from matplotlib.figure import Figure
from pytesdaq.viewer import readout


class MainWindow(QtWidgets.QMainWindow):
    
    def __init__(self):
        super().__init__()
        
       
        # initalize main window
        self.setWindowModality(QtCore.Qt.NonModal)
        self.resize(900, 700)
        self.setStyleSheet("background-color: rgb(211, 252, 255);")
        self.setTabShape(QtWidgets.QTabWidget.Rounded)
        self.setWindowTitle("Pulse Viewer")



        # channel color map
        self._channels_color_map = {0:(0, 85, 255),
                                    1:(255, 0, 0),
                                    2:(0, 170, 127),
                                    3:(170, 0, 255),
                                    4:(170, 116, 28),
                                    5:(15, 235, 255),
                                    6:(255, 207, 32),
                                    7:(121, 121, 121)}
        

        # setup frames
        self._setup_main_frame()
        self._setup_title_frame()
        self._setup_control_frame()
        self._setup_display_frame()
        self._setup_channel_frame()
        self._setup_tools_frame()
        self.show()
        

        # run control
        self._is_running = False
        self._stop_request = False
        self._data_source = 'niadc'


        # initialize readout
        self._readout = []
        self.initialize_readout()



    def initialize_readout(self):
        self._readout = readout.Readout(data_source = self._data_source)
        self._readout.register_ui(self._axes,self._canvas,
                                  self._channels_color_map)
        
    
    def closeEvent(self,event):
        """
        This function is called when exiting window
        superse base class
        """

        print("Exiting Pulse Display UI")
        



    def _handle_display(self):
        """
        Handle display. Called when clicking on display waveform 
        """
        self.statusBar().showMessage('Display Stopped')
        if self._is_running:
            self._readout.stop_run()
            self._is_running=False
            self.statusBar().showMessage('Display Stopped')
        else:
            self.statusBar().showMessage('Running...')
            self._is_running=True
            self._readout.configure(adc_name='adc1',channel_list=[0,1,2],
                                    sample_rate=1250000)
            self._readout.run(do_plot=True)
            
            




    def _setup_main_frame(self):
        
       
        # add main widget
        self._central_widget = QtWidgets.QWidget(self)
        self._central_widget.setEnabled(True)
        self._central_widget.setObjectName("central_widget")
        self.setCentralWidget(self._central_widget)
        

        # add menubar and status 
        self._menu_bar = self.menuBar()
        self.statusBar().showMessage('Status information')
        

    def _setup_title_frame(self):

        # add title frame
        self._title_frame = QtWidgets.QFrame(self._central_widget)
        self._title_frame.setGeometry(QtCore.QRect(10, 8, 877, 61))
        self._title_frame.setStyleSheet("background-color: rgb(0, 0, 255);")
        self._title_frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self._title_frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self._title_frame.setObjectName("titleWindow")

        # add title label
        self._title_label = QtWidgets.QLabel(self._title_frame)
        self._title_label.setGeometry(QtCore.QRect(26, 12, 261, 37))
        font = QtGui.QFont()
        font.setFamily("Sans Serif")
        font.setPointSize(23)
        font.setBold(True)
        font.setWeight(75)
        self._title_label.setFont(font)
        self._title_label.setStyleSheet("color: rgb(255, 255, 127);")
        self._title_label.setObjectName("titleLabel")
        self._title_label.setText("Pulse Display")

        # add device selection box + label
        
        # combo box
        self._device_combobox = QtWidgets.QComboBox(self._title_frame)
        self._device_combobox.setGeometry(QtCore.QRect(470, 16, 93, 29))
        self._device_combobox.setObjectName("deviceComboBox")

        # device label
        device_label = QtWidgets.QLabel(self._title_frame)
        device_label.setGeometry(QtCore.QRect(402, 20, 65, 17))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        device_label.setFont(font)
        device_label.setStyleSheet("color: rgb(200, 255, 255);")
        device_label.setObjectName("deviceLabel")
        device_label.setText("Device:")


        # status widget  
    
        '''
        # status label
        status_label = QtWidgets.QLabel(self._title_frame)
        status_label.setGeometry(QtCore.QRect(674, 24, 59, 15))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        status_label.setFont(font)
        status_label.setStyleSheet("color: rgb(200, 255, 255);")
        status_label.setObjectName("statusLabel")
        status_label.setText("Status:")

        # status widget
        self._status_textbox = QtWidgets.QLabel(self._title_frame)
        self._status_textbox.setGeometry(QtCore.QRect(736, 12, 77, 41))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self._status_textbox.setFont(font)
        self._status_textbox.setStyleSheet("background-color: rgb(255, 0, 0);")
        self._status_textbox.setObjectName("statusTextbox")
        self._status_textbox.setText("  Stopped")
        '''

    def _setup_control_frame(self):
        
        # add control frame
        self._control_frame = QtWidgets.QFrame(self._central_widget)
        self._control_frame.setGeometry(QtCore.QRect(10, 76, 269, 269))
        self._control_frame.setStyleSheet("background-color: rgb(226, 255, 219);")
        self._control_frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self._control_frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self._control_frame.setObjectName("controlFrame")

        # data source tabs
        self._data_source_tabs = QtWidgets.QTabWidget(self._control_frame)
        self._data_source_tabs.setEnabled(True)
        self._data_source_tabs.setGeometry(QtCore.QRect(14, 92, 243, 157))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self._data_source_tabs.setFont(font)
        self._data_source_tabs.setAutoFillBackground(False)
        self._data_source_tabs.setStyleSheet("")
        self._data_source_tabs.setTabPosition(QtWidgets.QTabWidget.North)
        self._data_source_tabs.setTabShape(QtWidgets.QTabWidget.Rounded)
        self._data_source_tabs.setIconSize(QtCore.QSize(16, 16))
        self._data_source_tabs.setElideMode(QtCore.Qt.ElideNone)
        self._data_source_tabs.setUsesScrollButtons(False)
        self._data_source_tabs.setDocumentMode(False)
        self._data_source_tabs.setTabsClosable(False)
        self._data_source_tabs.setTabBarAutoHide(False)
        self._data_source_tabs.setObjectName("sourceTabs")

        # Redis tab
        self._redis_tab = QtWidgets.QWidget()
        font = QtGui.QFont()
        font.setStrikeOut(False)
        font.setKerning(True)
        self._redis_tab.setFont(font)
        self._redis_tab.setLayoutDirection(QtCore.Qt.LeftToRight)
        self._redis_tab.setAutoFillBackground(False)
        self._redis_tab.setStyleSheet("background-color: rgb(243, 255, 242);")
        self._redis_tab.setObjectName("redisTab")
        self._data_source_tabs.addTab(self._redis_tab, "Redis")

        # HDF5 tab
        self._hdf5_tab = QtWidgets.QWidget()
        self._hdf5_tab.setEnabled(True)
        self._hdf5_tab.setStyleSheet("background-color: rgb(243, 255, 242);")
        self._hdf5_tab.setObjectName("hdf5Tab")
        self._data_source_tabs.addTab(self._hdf5_tab, "HDF5")

        # NI device tab
        self._niadc_tab = QtWidgets.QWidget()
        self._niadc_tab.setEnabled(True)
        self._niadc_tab.setStyleSheet("background-color: rgb(243, 255, 242);")
        self._niadc_tab.setObjectName("deviceTab")
        self._data_source_tabs.addTab(self._niadc_tab, "NIADC")



        # source selection combox box
        self._source_combobox = QtWidgets.QComboBox(self._control_frame)
        self._source_combobox.setGeometry(QtCore.QRect(10, 36, 87, 23))
        font = QtGui.QFont()
        font.setBold(False)
        font.setWeight(50)
        self._source_combobox.setFont(font)
        self._source_combobox.setObjectName("sourceComboBox")
        self._source_combobox.addItem("Redis")
        self._source_combobox.addItem("HDF5")
        self._source_combobox.addItem("NI ADC")

        # combo box label
        source_label = QtWidgets.QLabel(self._control_frame)
        source_label.setGeometry(QtCore.QRect(12, 16, 59, 15))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        source_label.setFont(font)
        source_label.setObjectName("sourceLabel")
        source_label.setText("Source:")



        # display control button
        self._display_control_button = QtWidgets.QPushButton(self._control_frame)
        self._display_control_button.setGeometry(QtCore.QRect(136, 12, 91, 65))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self._display_control_button.setFont(font)
        self._display_control_button.setStyleSheet("background-color: rgb(255, 0, 0);")
        self._display_control_button.setObjectName("displayControlButton")
        self._display_control_button.setText("Display \n" "Waveform")
    


        # connect buttobs
        self._display_control_button.clicked.connect(self._handle_display)


    def _setup_display_frame(self):


        # frame
        self._display_frame = QtWidgets.QFrame(self._central_widget)
        self._display_frame.setGeometry(QtCore.QRect(290, 76, 597, 597))
        self._display_frame.setStyleSheet("background-color: rgb(254, 255, 216);")
        self._display_frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self._display_frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self._display_frame.setLineWidth(1)
        self._display_frame.setObjectName("DisplayFrame")
        

        

        # canvas
        self._fig = Figure((3.0,3.0), dpi=100)
        #self._fig, self._axes = plt.subplots(sharex=False)
        self._axes = self._fig.add_subplot(111)
        #self._fig.subplots_adjust(hspace=.3)
        self._canvas = FigureCanvas(self._fig)
        #self._canvas.setParent(self._display_frame)
        self._canvas_toolbar = NavigationToolbar(self._canvas,self._display_frame)

        # canvas layout
        canvas_layout_widget = QtWidgets.QWidget(self._display_frame)
        canvas_layout_widget.setGeometry(QtCore.QRect(12, 11, 574, 537))
        canvas_layout = QtWidgets.QVBoxLayout(canvas_layout_widget)
        canvas_layout.setContentsMargins(0, 0, 0, 0)
        canvas_layout.addWidget(self._canvas)
        canvas_layout.addWidget(self._canvas_toolbar)
        


    def _setup_channel_frame(self):
        
        # channel frame
        self._channel_frame = QtWidgets.QFrame(self._central_widget)
        self._channel_frame.setGeometry(QtCore.QRect(10, 352, 269, 161))
        self._channel_frame.setStyleSheet("background-color: rgb(226, 255, 219);")
        self._channel_frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self._channel_frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self._channel_frame.setLineWidth(2)
        self._channel_frame.setObjectName("ChannelFrame")

        # set grid layout
        channel_layout = QtWidgets.QWidget(self._channel_frame)
        channel_layout.setGeometry(QtCore.QRect(8, 11, 254, 137))
        channel_layout.setObjectName("layoutWidget")
        channel_grid_layout = QtWidgets.QGridLayout(channel_layout)
        channel_grid_layout.setContentsMargins(0, 0, 0, 0)
        channel_grid_layout.setObjectName("gridLayout")

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
            button.setText("AI" + str(ichan))
            # background color
            color = self._channels_color_map[ichan]
            color_str = "rgb(" + str(color[0]) + "," + str(color[1]) + "," + str(color[2]) + ")" 
            button.setStyleSheet("background-color: " + color_str +";")
            button.setObjectName("chanButton_" + str(ichan))
            
            # layout
            channel_grid_layout.addWidget(button, row_num, col_num, 1, 1)
            row_num+=1
            if ichan==3:
                row_num = 0
                col_num = 1


            # save
            button.setObjectName("chanButton_" + str(ichan))
            self._channel_buttons[ichan] = button

    def _setup_tools_frame(self):
        
        # create frame
        self._tools_frame = QtWidgets.QFrame(self._central_widget)
        self._tools_frame.setGeometry(QtCore.QRect(10, 520, 269, 153))
        self._tools_frame.setStyleSheet("background-color: rgb(226, 255, 219);")
        self._tools_frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self._tools_frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self._tools_frame.setObjectName("ToolsFrame")

        # Add tools button
        self._tools_button = QtWidgets.QPushButton(self._tools_frame)
        self._tools_button.setGeometry(QtCore.QRect(156, 32, 89, 65))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self._tools_button.setFont(font)
        self._tools_button.setStyleSheet("background-color: rgb(162, 162, 241);")
        self._tools_button.setObjectName("toolsButton")
        self._tools_button.setText("Tools")
        
        # add running avg box
        self._running_avg_checkbox = QtWidgets.QCheckBox(self._tools_frame)
        self._running_avg_checkbox.setGeometry(QtCore.QRect(16, 16, 109, 21))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self._running_avg_checkbox.setFont(font)
        self._running_avg_checkbox.setObjectName("runningAvgCheckBox")
        self._running_avg_checkbox.setText("Running Avg")

        # running avg spin box
        self._running_avg_spinbox = QtWidgets.QSpinBox(self._tools_frame)
        self._running_avg_spinbox.setEnabled(False)
        self._running_avg_spinbox.setGeometry(QtCore.QRect(34, 40, 85, 21))
        self._running_avg_spinbox.setMaximum(20000)
        self._running_avg_spinbox.setProperty("value", 1)
        self._running_avg_spinbox.setObjectName("runningAvgSpinBox")

        # add lopw pass filter
        self._lpfilter_checkbox = QtWidgets.QCheckBox(self._tools_frame)
        self._lpfilter_checkbox.setGeometry(QtCore.QRect(16, 76, 119, 21))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self._lpfilter_checkbox.setFont(font)
        self._lpfilter_checkbox.setObjectName("lpFilterCheckBox")
        self._lpfilter_checkbox.setText("LP Filter [kHz]")

        # lp filter spin box
        self._lpfilter_spinbox = QtWidgets.QSpinBox(self._tools_frame)
        self._lpfilter_spinbox.setEnabled(False)
        self._lpfilter_spinbox.setGeometry(QtCore.QRect(34, 100, 83, 21))
        self._lpfilter_spinbox.setMinimum(1)
        self._lpfilter_spinbox.setMaximum(500)
        self._lpfilter_spinbox.setObjectName("lpFilterSpinBox")
      

    def closeEvent(self,event):
        print("Exiting Pulse Display UI")
        


        




if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    ui = MainWindow()
    sys.exit(app.exec_())
