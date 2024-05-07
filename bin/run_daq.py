import argparse
import pytesdaq.daq as daq
from pytesdaq.utils import arg_utils
from pytesdaq.daq import DAQControl
import numpy as np
import os
from datetime import datetime
import stat
import time
from pprint import pprint
import copy

if __name__ == "__main__":


    # ==============================
    # Input arguments
    # ==============================
    parser = argparse.ArgumentParser(description="Launch DAQ")

    # channels
    parser.add_argument('-c','--channels', dest='channels',
                        nargs= '+', type=str, 
                        help=('Comma and/or space separated "detector" '
                              'OR "readout" TES wiring channels. '))

    parser.add_argument('--adc_channels',
                        nargs= '+', type=str,
                        help=('ADC index with format: a,b,c-d (no space)'
                        '(Only if a single ADC connected!)'))
        
    # duration 
    parser.add_argument('--duration', type=str, required=True,
                        help=('Total duration in seconds(s)/minutes(m) or hours(h), '
                              'example: 10s, 10m, or 10h'))
    # trigger type
    parser.add_argument('--acquire-cont', '--acquire-continuous',
                        dest="acquire_cont", action="store_true",
                        help='Acquire continuous data')
    
    parser.add_argument('--acquire-rand','--acquire_rand',
                        '--acquire-randoms',
                        dest="acquire_rand", action="store_true",
                        help='Acquire randoms data')

    parser.add_argument('--acquire-didv','--acquire_didv',
                        dest="acquire_didv", action="store_true",
                        help='Acquire dIdV data')
    
    parser.add_argument('--acquire-iv','--acquire_iv',
                        dest="acquire_iv", action="store_true",
                        help='Acquire IV data')
    
    parser.add_argument('--acquire-exttrig','--acquire_exttrig',
                        dest="acquire_exttrig", action="store_true",
                        help='Acquire external trigger data')

    #parser.add_argument('--acquire-thresh','--acquire_thresh',
    #                    '--acquire-threshold',
    #                    dest="acquire_thresh", action="store_true",
    #                    help='Acquire threshold trigger data')
        
    # Run purpose
    parser.add_argument('--data_purpose', '--run_purpose',  dest='data_purpose',
                        help = 'Data purpose [string or int], default="test"')
    # comment
    parser.add_argument('--comment', dest='comment',
                        type = str, help = 'Comment (use quotes "")  [default: "No comment"]')

    # config
    parser.add_argument('--daq_config_file', type=str,
                        help = ('Data taking configuration file name (full path) '
                                '[default: pytesdaq/config/daq.ini]'))
    
    parser.add_argument('--setup_file', '--instruments_setup_file',
                        dest='setup_file',type=str,
                        help = ('intruments/detectors setup file name (full path) '
                                '[default: pytesdaq/config/setup.ini]'))
    # verbose
    parser.add_argument('--quiet', action="store_true", help='Remove Screen output')            
        
    args = parser.parse_args()

    # TEMP
    args.acquire_thresh = False
  

    # -----------------------------
    # A few default parameters
    # -----------------------------
    comment = 'No comment'
    data_purpose = 'test'
    verbose = True
    duration = None
        
    # config file, check default
    this_dir = os.path.dirname(os.path.realpath(__file__))
    setup_file = os.path.normpath(this_dir + '/../pytesdaq/config/setup.ini')
    daq_config_file = os.path.normpath(this_dir + '/../pytesdaq/config/daq.ini')

    
    # ----------------------------
    # Parse arguments
    # ----------------------------

    # setup file
    if args.setup_file:
        setup_file = args.setup_file
    if args.daq_config_file:
        daq_config_file = args.daq_config_file

    # comment
    if args.comment:
        comment = args.comment

    # run type
    if args.data_purpose:
        data_purpose = int(args.data_purpose)
    
    if args.quiet:
        verbose = False
        
    # duration
    duration  = args.duration

    # channels
    if args.channels and args.adc_channels:
        print('ERROR: Choose between "-c" or "-adc_channels", '
              'not both!')
    channels = None
    adc_channels = None
    if args.channels:
        channels = arg_utils.extract_list(args.channels)
    elif args.adc_channels:
        adc_channels = arg_utils.extract_list(args.adc_channels)
        adc_channels = ','.join(adc_channels)
        adc_channels = arg_utils.hyphen_range(adc_channels)
                
    # check acquisition
    acquisition_types = ['continuous',
                         'didv', 'iv',
                         'exttrig', 'randoms',
                         'threshold']

    acquisition_args = [args.acquire_cont,
                        args.acquire_didv,
                        args.acquire_iv,
                        args.acquire_exttrig,
                        args.acquire_rand,
                        args.acquire_thresh]

    inds = list(np.where(acquisition_args)[0])
    if len(inds) > 1:
        print('ERROR: Only a single acquisition type '
              + ' can be enabled!')
        exit()
    elif  len(inds) != 1:
        print('ERROR: An acquisition type '
              + ' needs to be enabled!')
        exit()
        
    acquisition_type = acquisition_types[inds[0]]
    

    if verbose:
        print('======================================')
        print(f'Data Acquisition: "{ acquisition_type}"')
        print('======================================\n')
        print(f'The following configuration files '
              f'will be used: ')
        print(f'   - Instruments setup: {setup_file}')
        print(f'   - Data acquisition setup: {daq_config_file}\n')



    daq_control = DAQControl(acquisition_type,
                             setup_file=setup_file,
                             daq_config_file=daq_config_file ,
                             channels=channels,
                             adc_channels=adc_channels,
                             data_purpose=data_purpose,
                             driver_name='polaris',
                             verbose=verbose)


    
    daq_control.run(duration=duration, comment=comment)


        
