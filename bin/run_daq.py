import argparse
import pytesdaq.daq as daq
import pytesdaq.config.settings as settings
import pytesdaq.instruments.control as instrument
from pytesdaq.utils import  arg_utils
import numpy as np
import os

if __name__ == "__main__":


    # ========================
    # Input arguments
    # ========================
    parser = argparse.ArgumentParser(description="Launch DAQ")

    parser.add_argument('--run_time', type = str,help = 'Run time in minutes [default = 1 min]')
    parser.add_argument('--run_type', type = str,help = 'Run type [default: 1 = "Test"]')
    parser.add_argument('--run_comment', type = str, help = 'Run comment [default: "No comment"]')
    parser.add_argument('--duration',  type = str,
                        help = 'Total duration of data taking in hours (nb runs = duration/run time)  [default = run time]')
    parser.add_argument('--daq_driver',help='DAQ driver ("polaris","pydaqmx", "tektronix","midas") [default "polaris"]')
    parser.add_argument('--log_file',help='Log file name [default: no log file]')
    parser.add_argument('--disable-lock',dest="disable_lock",action="store_true",help='Disable daq process lock')
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
    parser.add_argument('--channels', type = str,
                        help='Channels number (same all devices!):  string "a,b,c-d" [default from configuration setup file] ')
    parser.add_argument('--devices',help='ADC Devices number: string "a,b,c-d" [default from configuration setup file] ')
 
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
    for adc_name in adc_list:
        config = adc_config[adc_name]
        if args.sample_rate:
            config['sample_rate'] = int(args.sample_rate)
        if args.nb_samples:
            config['nb_samples'] = int(args.nb_samples)
        if args.voltage_min:
            config['voltage_min'] = float(args.voltage_min)
        if args.voltage_max:
            config['voltage_max'] = float(args.voltage_max)
        if args.channels:
            config['channel_list'] = args.channels
        if args.trigger_type:
            config['trigger_type'] = int(args.trigger_type)

        config['channel_list'] =  arg_utils.hyphen_range(config['channel_list'])
        adc_config[adc_name] = config

    # ========================
    # Detector config
    # ======================== 
    det_config = dict()
    myinstrument = instrument.Control(setup_file=setup_file, dummy_mode=True, verbose=verbose)
    for adc_name in adc_list:
        config = adc_config[adc_name]
#        det_config[adc_name] = myinstrument.read_all(adc_id=adc_name, adc_channel_list=config['channel_list'])
        
    
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
    if det_config:
        mydaq.set_detector_config(det_config)

    # run
    for irun in range(nb_runs):
        success = mydaq.run(run_time_seconds, run_type, run_comment)
        if not success:
            print('ERROR: Data taking error. Exiting!')
            mydaq.clear()
            exit()
        elif nb_runs>1:
            print('INFO: Data taking run ' + str(irun+1) + ' out of total '
                  + str(nb_runs) + ' successfully done!')


    print('INFO: Data taking run successfully done!')   
    mydaq.clear()  


