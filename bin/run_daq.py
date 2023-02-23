import argparse
import pytesdaq.daq as daq
from pytesdaq.config import settings
from pytesdaq.instruments import control as instrument
from pytesdaq.utils import arg_utils
from pytesdaq.utils import connection_utils
import numpy as np
import os
from datetime import datetime
import stat
import time

if __name__ == "__main__":


    # ==============================
    # Input arguments
    # ==============================
    parser = argparse.ArgumentParser(description="Launch DAQ")

    # channels
    parser.add_argument('-c','--channels', dest='channels',
                        nargs= '+', type=str, 
                        help=('(required) Comma and/or space separated "detector" '
                              'OR "readout" TES wiring channels'))
    
    parser.add_argument('--adc_channels', 
                        nargs= '+', type=str,
                        help=('ADC index with format: a,b,c-d '
                              '(arg can be used instead of "-c")'))
    
    # duration 
    parser.add_argument('--duration', type=str, required=True,
                        help=('Total duration in seconds(s)/minutes(m) or hours(h), '
                              'example: 10s, 10m, or 10h'))
    
    # trigger type
    parser.add_argument('--acquire-cont', '--acquire-continuous',
                        dest="acquire_cont", action="store_true",
                        help='Acquire continuous data')
    
    parser.add_argument('--acquire-rand','--acquire-randoms',
                        dest="acquire_rand", action="store_true",
                        help='Acquire randoms data')

    parser.add_argument('--acquire-didv',
                        dest="acquire_didv", action="store_true",
                        help='Acquire didv data')

    parser.add_argument('--acquire-thresh','--acquire-threshold',
                        dest="acquire_thresh", action="store_true",
                        help='Acquire threshold trigger data')

    # Run purpose
    parser.add_argument('--run_purpose', type=int,
                        help = 'Run purpose/type [default: 1 = "test"]')
    # comment
    parser.add_argument('--comment', '--run_comment', dest='comment',
                        type = str, help = 'Comment (use quotes "")  [default: "No comment"]')

    # config
    parser.add_argument('--daq_config_file', type=str,
                        help = ('Data taking configuration file name (full path) '
                                '[default: pytesdaq/config/daq.ini]'))
    
    parser.add_argument('--setup_file', '--instruments_setup_file',
                        dest='setup_file',type=str,
                        help = ('intruments/detectors setup file name (full path) '
                                '[default: pytesdaq/config/setup.ini]'))

    # For testing, disable controlling/reading instruments
    parser.add_argument('--disable-control', dest="disable_control", action="store_true",
                        help='Disable instrument control/reading')

    # verbose
    parser.add_argument('--quiet', action="store_true", help='Remove Screen output')            
        
    args = parser.parse_args()


    # -----------------------------
    # A few default parameters
    # -----------------------------
    comment = 'No comment'
    daq_driver = 'polaris'
    disable_control = False
    run_type = 1
    log_file = str()
    verbose = True
    duration_sec = None
    series_max_time_sec = 1200 # 20 min
    signal_gen_amp_mV = None
    signal_gen_freq_hz = None
    added_didv_time_sec = 60

    
    # config
    this_dir = os.path.dirname(os.path.realpath(__file__))
    setup_file = this_dir + '/../pytesdaq/config/setup.ini'
    daq_config_file = this_dir + '/../pytesdaq/config/daq.ini'

    # ----------------------------
    # Parse arguments
    # ----------------------------

    # setup file
    if args.setup_file:
        setup_file = args.setup_file

    if args.daq_config:
        daq_config_file = args.daq_config_file
        
    # comment
    if args.comment:
        comment = args.comment

    # run type
    if args.run_type:
        run_type = int(args.run_type)

    # disable control
    if args.disable_control:
        disable_control = True


    # log file
    #if args.log_file:
    #    log_file =  args.log_file
    
    if args.quiet:
        verbose = False


    # duration
    duration_sec = arg_utils.convert_to_seconds(args.duration)
    
    # check acquisition
    trigger_types = {'continuous':1,'didv':2,'randoms':3,'threshold':4}
    trigger_list = list(trigger_types.keys())
    
    acquisition_args = [args.acquire_cont,
                        args.acquire_rand
                        args.acquire_didv
                        args.acquire_thresh]

    trigger_inds = list(np.where(acquisition_args)[0])
    if len(trigger_inds)!=1:
        print('ERROR: A (single) acquisition type '
              + ' needs to be enabled!')
        exit()

    trigger_type = trigger_list[trigger_inds[0]]
            


    # ----------------------------
    # Intruments/DAQ config
    # ----------------------------

    # check files exist
    if not os.path.isfile(setup_file):
        print('ERROR: Experimental setup file "'
              + setup_file
              + '" not found!')
        exit()
        
    if not os.path.isfile(daq_config_file):
        print('ERROR: Data taking file "'
              + daq_config_file
              + '" not found!')
        exit()
        
    exp_config = settings.Config(setup_file=setup_file,
                                 daq_file=daq_config_file)
        
    
    # default ADC value (from setup file)  
    adc_list = exp_config.get_adc_list()
    if len(adc_list) != 1:
        print('ERROR: Only 1 ADC should be enabled for now!')
        exit()
    adc_name = adc_list[0]
    adc_config  = dict()
    adc_config[adc_name] = exp_config.get_adc_setup(adc_name)
        
    # Thermometers
    disable_temperature_reading = False
    temperature_controllers = exp_config.get_temperature_controllers()
    if not temperature_controllers:
        disable_temperature_reading = True

    thermometer_list = list()
    if not disable_temperature_reading:
        for temp_control in temperature_controllers:
            temp_setup = exp_config.get_temperature_controller_setup(
                temp_control
            )
            thermometer_list += temp_setup['thermometers']
            
    # get data taking config    
    daq_config = exp_config.get_daq_config(trigger_type)

    # connection table
    connection_table = exp_config.get_adc_connections()
    connection_dict = connection_utils.get_items(connection_table)
    


    # ----------------------------
    # Channels
    # ----------------------------
    adc_channels = list()
    if args.adc_channels:
        channels = arg_utils.extract_list(args.adc_channels)
        for channel in channels:
            adc_channels.extend(arg_utils.hyphen_range(channel))
            
    elif args.channels:
        channels = arg_utils.extract_list(args.channels)
        for channel in channels:
        
            channel_type = None
            if channel in connection_dict['detector_channel']:
                channel_type = 'detector_channel'
            elif channel in connection_dict['tes_channel']:
                channel_type = 'tes_channel'

            if channel_type is  None:
                print('ERROR: Unable to identify channel type')
                exit()

            # convert to ADC
            adc_channel = connection_table.query(
                channel_type + ' == @channel'
            )['adc_channel'].values

            if len(adc_channel) !=  1:
                print('ERROR: Channel ' + channel
                      + ' is not unique or does not exist!'
                      + 'Please check input or connections map in setup.ini)')
                
            adc_channels.append(int(adc_channel[0]))
                                 
    


            
    # ----------------------------
    # ADC configuration
    # ----------------------------

    # voltage
    if 'voltage_min' in daq_config.keys():
        adc_config[adc_name]['voltage_min'] = (
            float(daq_config['voltage_min'])
        )

    if 'voltage_max' in daq_config.keys():
        adc_config[adc_name]['voltage_max'] = (
            float(daq_config['voltage_max'])
        )

    # sample rate
    if 'sample_rate' in daq_config.keys():
        adc_config[adc_name]['sample_rate'] = (
            float(daq_config['sample_rate'])
        )

    # number of samples
    nb_samples = None
    if  trigger_type != 'didv':
        if 'trace_length' in daq_config.keys():
            trace_length_sec = (
                arg_utils.convert_to_seconds(
                    daq_config['trace_length']
                )
            )
            nb_samples = int(
                round(int(adc_config[adc_name]['sample_rate'])
                      *trace_length_sec)
            )
        elif 'nb_samples' in  daq_config.keys():
            nb_samples = int(adc_config[adc_name]['sample_rate'])
        else:
            print('\nERROR: "trace_length" or "nb_samples" required!')
            exit()
            
        adc_config[adc_name]['nb_samples'] = nb_samples    
                

    # ADC channel list
    adc_config[adc_name]['channel_list'] = adc_channels


    # trigger type
    adc_config[adc_name]['trigger_type'] = int(
        trigger_types[trigger_type]
    )



        
    # ====================================
    # Read instruments settings
    # ====================================
    detector_config = dict()
    if not disable_control:
        
        myinstrument = instrument.Control(
            setup_file=setup_file,
            dummy_mode=False,
            verbose=verbose
        )

        for adc_name in adc_list:
            config_dict = adc_config[adc_name]
            detector_config[adc_name] = (
                myinstrument.read_all(
                    adc_id=adc_name,
                    adc_channel_list=adc_config[adc_name]['channel_list']
                )
            )

        # temperature reading
        if not disable_temperature_reading:
            
            for thermometer in thermometer_list:
                temperature = myinstrument.get_temperature(
                    channel_name=thermometer)
                time.sleep(1)
                detector_config[adc_name][
                    'temperature_' + thermometer.lower()
                ] = temperature

                # display
                if verbose:
                    if temperature<1:
                        print('Current ' + thermometer
                              + ' temperature = '
                              + str(temperature*1000) + ' mK')
                    else:
                        print('Current ' + thermometer
                              + ' temperature = '
                              + str(temperature) + ' K')

    # ====================================
    # dIdV specific configuration
    # ====================================

    # let's just copy ADC config
    didv_adc_config = adc_config.copy()

    # false by default
    add_bor_didv = False
    add_eor_didv = False
    
    if trigger_type != 'didv':
        if 'add_series_start_didv' in daq_config.keys():
            add_bor_didv = daq_config['add_series_start_didv']
        if 'add_series_end_didv' in daq_config.keys():
            add_eor_didv = daq_config['add_series_end_didv']

    # case didv added: replace config
    if add_bor_didv or add_eor_didv:
        didv_config = exp_config.get_daq_config('didv')

    # get settings
    if (add_bor_didv or add_eor_didv
        or  trigger_type=='didv'):

        # voltage range
        if 'voltage_min' in didv_config.keys():
            didv_adc_config[adc_name]['voltage_min'] = (
                float(didv_config['voltage_min'])
        )

        if 'voltage_max' in didv_config.keys():
            didv_adc_config[adc_name]['voltage_max'] = (
                float(didv_config['voltage_max'])
            )

        # sample rate
        if 'sample_rate' in didv_config.keys():
            didv_adc_config[adc_name]['sample_rate'] = (
                float(didv_config['sample_rate'])
            )

        # signal generator
        if 'signal_gen_voltage' in didv_config.keys():
            signal_gen_amp_mV = float(
                didv_config['signal_gen_voltage'] 
            )
            
        if 'signal_gen_frequency' in didv_config.keys():
            signal_gen_freq_hz = float(
                didv_config['signal_gen_frequency'] 
            )

        # check
        if (signal_gen_amp_mV is None
            or signal_gen_freq_hz is None):
        
            if (add_bor_didv or add_eor_didv):
                print('ERROR: For added dIdV, "signal_gen_voltage" '
                      + 'and "signal_gen_frequency" arguments are '
                      + 'required!')
                exit()
                
            elif trigger_type=='didv':

                if signal_gen_amp_mV is None:
                    signal_gen_amp_mV = (
                        detector_config[adc_name]['signal_gen_voltage'][0]
                    )

                if signal_gen_freq_hz is None:
                    signal_gen_freq_hz = (
                        detector_config[adc_name]['signal_gen_frequency'][0]
                    )

        # trace length
        if 'nb_cycles' in didv_config.keys():
            nb_cycles = float(
                didv_config['nb_cycles']
            )
            fs = didv_adc_config['sample_rate']
            didv_adc_config['nb_samples'] = int(
                round(
                    nb_cycles*fs/signal_gen_freq_hz
                )
            )            
            
        # run time
        if 'didv_run_time' in daq_config.keys():
            added_didv_time_sec = (
                arg_utils.convert_to_seconds(
                    daq_config['didv_run_time']
                )
            )


            
                            
    # ====================================
    # Build output Data path
    # ====================================

    facility = str(exp_config.get_facility_num())
    data_path = exp_config.get_data_path()
    fridge_run  = 'run' + str(exp_config.get_fridge_run())
    if data_path.find(fridge_run)==-1:
        data_path += '/' + fridge_run

    # make base directory
    arg_utils.make_directories(data_path)

    # make raw directory
    data_path += '/raw'
    arg_utils.make_directories(data_path)

    group_prefix = trigger_type
    if 'group_prefix' in daq_config.keys():
        group_prefix = str(
            daq_config['group_prefix']
        )

    # make output group directory
    now = datetime.now()
    series_day = now.strftime('%Y') +  now.strftime('%m') + now.strftime('%d') 
    series_time = now.strftime('%H') + now.strftime('%M') +  now.strftime('%S')
    group_name = group_prefix + '_I' + facility + '_D' + series_day + '_T' + series_time
    data_path += '/' + group_name
    arg_utils.make_directories(data_path)

    if verbose:
        print('INFO: Data taking group = ' + group_name)
        print('INFO: Ouput Directory = ' +  data_path)
      
    
    # Output data file prefix
    data_prefix = 'raw'
    if trigger_type == 'continuous':
         data_prefix = 'cont'
    elif trigger_type == 'didv':
        data_prefix = 'didv'
    elif trigger_type == 'threshold':
        data_prefix = 'thresh'
    elif trigger_type == 'randoms':
        data_prefix = 'rand'
       

    # ====================================
    # Nb of series/runs
    # ====================================

    run_time_sec = duration_sec
    if 'series_max_time' in daq_config.keys():
        series_max_time_sec = (
            arg_utils.convert_to_seconds(
                daq_config['series_max_time']
            )
        )
        
    nb_runs = int(
        round(duration_sec/series_max_time_sec)
    )

    if nb_runs<1:
        nb_runs = 1
    else:
        run_time_sec = series_max_time_sec
        if verbose:
            print('INFO: Number of runs = '
                  + str(nb_runs)
                  + ' (' + str(run_time_sec*60)
                  + ' minutes each)')
            
        
  
    # ====================================
    # Run DAQ
    # ====================================
    mydaq = daq.DAQ(driver_name=daq_driver,
                    verbose=verbose,
                    setup_file=setup_file)

    
    # data taking process lock 
    mydaq.lock_daq = True

    # log file
    #if log_file:
     #   mydaq.log_file = log_file

    # set configuration
    if trigger_type == 'didv':
        mydaq.set_adc_config_from_dict(didv_adc_config)
    else:
        mydaq.set_adc_config_from_dict(adc_config)

    if detector_config:
        mydaq.set_detector_config(detector_config)



    def run_added_didv():
        """
        dIdV added run
        """

        # set signal generator
        for channel in self._detector_channels:
            
                        # signal generator
                        
                        self._instrument.set_signal_gen_params(detector_channel=channel,source='tes', 
                                                               voltage=didv_config['signal_gen_voltage'],
                                                               current=didv_config['signal_gen_current'],
                                                               frequency=didv_config['signal_gen_frequency'],
                                                               shape='square')


                    
                        self._instrument.set_signal_gen_onoff('on', detector_channel=channel)

                        # connect to TES
                        self._instrument.connect_signal_gen_to_tes(True, detector_channel=channel)



        
        # run main data
        success = mydaq.run(run_time=run_time_sec ,
                            run_type=run_type,
                            run_comment=comment,
                            group_name= group_name,
                            group_comment=comment,
                            data_prefix=series_prefix,
                            data_path=data_path)
        if not success:
            print('ERROR: Data taking error. Exiting!')
            mydaq.clear()
            exit()
        
        

        
    # loop run
    for irun in range(nb_runs):


        # display
        if verbose:
            print('\nINFO: Starting Data taking run ' + str(irun+1)
                  + ' out of ' + str(nb_runs)
                  + ' total runs')
            
        
        # begin of run didv
        if add_bor_didv:
            run_added_didv()
            

        #  even/odd series handling
        series_prefix = data_prefix
        
        if split_series:         
            if (irun % 2):
                series_prefix = 'even_' + series_prefix
            else:
                series_prefix = 'odd_' + series_prefix


        # run main data
        success = mydaq.run(run_time=run_time_sec ,
                            run_type=run_purpose,
                            run_comment=comment,
                            group_name= group_name,
                            group_comment=comment,
                            data_prefix=series_prefix,
                            data_path=data_path)
        if not success:
            print('ERROR: Data taking error. Exiting!')
            mydaq.clear()
            exit()


        # end of run dIdV
        if add_eor_didv:
            run_added_didv()
            

    print('INFO: Data taking run successfully done!')   
    mydaq.clear()  


