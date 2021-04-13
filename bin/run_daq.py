import argparse
import pytesdaq.daq as daq
from pytesdaq.config import settings
from pytesdaq.instruments import control as instrument
from pytesdaq.utils import arg_utils
import numpy as np
import os
from datetime import datetime
import stat

if __name__ == "__main__":


    # ========================
    # Input arguments
    # ========================
    parser = argparse.ArgumentParser(description="Launch DAQ")

    parser.add_argument('--run_time', type = str, help = 'Run time in minutes [default = 1 min]')
    parser.add_argument('--run_type', type = str, help = 'Run type [default: 1 = "Test"]')
    parser.add_argument('--run_comment', type = str, help = 'Run comment (use quotes "")  [default: "No comment"]')
    parser.add_argument('--total_duration', '--duration', dest='duration', type = str,
                        help = 'Total duration of data taking in hours (nb runs = duration/run time)  [default = run time]')
    parser.add_argument('--daq_driver',help='DAQ driver ("polaris","pydaqmx", "tektronix","midas") [default "polaris"]')
    parser.add_argument('--log_file', help='Log file name [default: no log file]')
    parser.add_argument('--verbose', action="store_true", help='Screen output')
    parser.add_argument('--setup_file', type = str,
                        help = 'Configuration setup file name (full path) [default: pytesdaq/config/setup.ini]')
  
    # arguments with default value in configuration file
    parser.add_argument('--trigger_type',
                        help='1=continuous, 2=ext trigger, 3=randoms, 4=threshold [default from configuration setup file] ')
    parser.add_argument('--sample_rate',help='Sample rate [default from configuration setup file] ')
    parser.add_argument('--nb_samples',help='Number of samples [default from configuration setup file] ')
    parser.add_argument('--voltage_min',help='Minimum ADC voltage [default from configuration setup file] ')
    parser.add_argument('--voltage_max',help='Maximum ADC voltage [default from configuration setup file] ')
    parser.add_argument('--adc_channels', '--channels', dest='adc_channels', type = str,
                        help='ADC channels number/index (same all devices!), format="a,b,c-d" [default from configuration setup file] ')
    parser.add_argument('--devices', help='ADC Devices number. Format="a,b,c-d" [default from configuration setup file] ')
    parser.add_argument('--disable-lock', dest="disable_lock",action="store_true",help='Disable daq process lock')
    parser.add_argument('--disable-control', dest="disable_control", action="store_true",
                        help='Disable instrument control. Require "detector_config" field in setup.ini!')
    
    
    args = parser.parse_args()


    # ------------------
    # Default 
    # ------------------
  
    
    # hardcoded default
    run_time_seconds = 60
    run_comment = 'No comment'
    run_type = 1
    daq_driver = 'polaris'
    log_file = str()
    disable_lock = False
    disable_control = False
    verbose = False
       
    # Setup file:
    setup_file = None
    if args.setup_file:
        setup_file = args.setup_file
    else:
        this_dir = os.path.dirname(os.path.realpath(__file__))
        setup_file = this_dir + '/../pytesdaq/config/setup.ini'

    if not os.path.isfile(setup_file):
        print('ERROR: Setup file "' + setup_file + '" not found!')
        exit()

        
    config = settings.Config(setup_file=setup_file)
    adc_list = config.get_adc_list()
    adc_config  = dict()
    for adc_name in adc_list:
        adc_config[adc_name] =  config.get_adc_setup(adc_name)


    # ------------------
    # Parse arguments 
    # ------------------

    if args.run_time:
        run_time_seconds = float(args.run_time)*60
    if args.run_type:
        run_type = int(args.run_type)
    if args.run_comment:
        run_comment = args.run_comment
    if args.daq_driver:
        daq_driver = args.daq_driver
    if args.log_file:
        log_file =  args.log_file
    if args.disable_lock:
        disable_lock = True
    if args.verbose:
        verbose = True
    if args.disable_control:
        disable_control = True
    
    # nb of runs
    nb_runs = 1
    if args.duration:
        duration_seconds =  float(args.duration)*60*60
        if duration_seconds>0:
            nb_runs = int(round(duration_seconds/run_time_seconds))

    if nb_runs>1:
        print('INFO: Data taking: Number of runs = ' + str(nb_runs)
              + ' (' + str(int(duration_seconds)) + ' seconds each). Total duration = '
              + str(args.duration) + ' hours!')

    
    # ADC configuration
    if args.devices:
        adc_list = list()
        adc_config = dict()
        adc_num_list =  arg_utils.hyphen_range(args.devices)
        for adc_num in adc_num_list:
            adc_name = 'adc' + str(adc_num)
            adc_list.append(adc_name)
            adc_config[adc_name] = config.get_adc_setup(adc_name)
        


    # replace with user parameters
    trigger_type = list()
    for adc_name in adc_list:
        config_dict = adc_config[adc_name]
        if args.sample_rate:
            config_dict['sample_rate'] = int(args.sample_rate)
        if args.nb_samples:
            config_dict['nb_samples'] = int(args.nb_samples)
        if args.voltage_min:
            config_dict['voltage_min'] = float(args.voltage_min)
        if args.voltage_max:
            config_dict['voltage_max'] = float(args.voltage_max)
        if args.adc_channels:
            config_dict['channel_list'] = args.adc_channels
        if args.trigger_type:
            config_dict['trigger_type'] = int(args.trigger_type)

        config_dict['channel_list'] =  arg_utils.hyphen_range(config_dict['channel_list'])
        adc_config[adc_name] = config_dict
        trigger_type.append(int(config_dict['trigger_type']))
        
        

    # ========================
    # Get detector config
    # ======================== 
    detector_config = dict()
    if not disable_control:
        myinstrument = instrument.Control(setup_file=setup_file, dummy_mode=False, verbose=verbose)
        for adc_name in adc_list:
            config_dict = adc_config[adc_name]
            detector_config[adc_name] = myinstrument.read_all(adc_id=adc_name,
                                                              adc_channel_list=config_dict['channel_list'])
    else:
        for adc_name in adc_list:
            config_dict = adc_config[adc_name]
            detector_config[adc_name] = config.get_detector_config(adc_id=adc_name,
                                                                   adc_channel_list=config_dict['channel_list'])
            
        

    # ========================
    # Data path
    # ======================== 
    data_path = config.get_data_path()
    fridge_run = 'run' + str(config.get_fridge_run())
    if data_path.find(fridge_run)==-1:
        data_path += '/' + fridge_run

    dir_prefix = 'continuous'  
    if trigger_type[0]==2 or trigger_type[0]==4:
        dir_prefix = 'trigger'


    now = datetime.now()
    series_day = now.strftime('%Y') +  now.strftime('%m') + now.strftime('%d') 
    series_time = now.strftime('%H') + now.strftime('%M')
    data_path += '/' + dir_prefix + '_' + series_day + '_' + series_time

    try:
        os.makedirs(data_path)
        os.chmod(data_path, stat.S_IRWXG | stat.S_IRWXU | stat.S_IROTH | stat.S_IXOTH)
    except OSError:
        print('\nERROR: Unable to create directory "'+ data_path  + '"!\n')
        exit()
    
    # ========================
    # Data prefix
    # ========================
    data_prefix = 'cont'
    if trigger_type[0]==2:
        data_prefix = 'exttrig'
    elif trigger_type[0]==4:
        data_prefix = 'threshtrig'
        
    
    # ========================
    # Run DAQ
    # ======================== 
    mydaq = daq.DAQ(driver_name = daq_driver,
                    verbose = verbose,
                    setup_file=setup_file)
    
    # process lock 
    if disable_lock:
        mydaq.lock_daq = False

    # log file
    if log_file:
        mydaq.log_file = log_file
        
    # configuration
    mydaq.set_adc_config_from_dict(adc_config)
    if detector_config:
        mydaq.set_detector_config(detector_config)

    # run
    for irun in range(nb_runs):
        success = mydaq.run(run_time=run_time_seconds,
                            run_type=run_type,
                            run_comment=run_comment,
                            data_prefix=data_prefix,
                            data_path=data_path)
        if not success:
            print('ERROR: Data taking error. Exiting!')
            mydaq.clear()
            exit()
        elif nb_runs>1:
            print('INFO: Data taking run ' + str(irun+1) + ' out of total '
                  + str(nb_runs) + ' successfully done!')


    print('INFO: Data taking run successfully done!')   
    mydaq.clear()  


