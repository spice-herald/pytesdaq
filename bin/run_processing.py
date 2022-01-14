import argparse
import numpy as np
import os
import time
from datetime import datetime
from glob import glob
from pathlib import Path
from pytesdaq.processing.trigger import ContinuousData
import pytesdaq.config.settings as settings
from pytesdaq.utils import arg_utils
import stat
from pytesdaq.display import SeriesGroup
from pprint import pprint


if __name__ == "__main__":

    # ------------------
    # Input arguments
    # ------------------
    parser = argparse.ArgumentParser(description='Launch Trigger Processing')
    
    parser.add_argument('--acquire-rand', '--acquire_rand', dest='acquire_random',
                        action='store_true', help='Acquire randoms')
    parser.add_argument('--acquire-trig', '--acquire_trig', dest='acquire_trigger',
                        action='store_true', help='Acquire randoms')
    parser.add_argument('--calc-filter', '--calc_filter', dest='calc_filter',
                        action='store_true', help='Calculate filter informations (PSD and template)')

    parser.add_argument('--input_group_path', '--raw_path', dest='input_group_path', type=str,
                        help='Path to continuous raw data group (including group name)')
    parser.add_argument('-s', '--series''--input_series', dest='input_series', nargs='+', type=str, 
                        help=('Continous data series name(s) (format string Ix_Dyyyymmdd_Thhmmss,'
                              'space or comma seperated)' 
                              '[Default: all series]'))

    parser.add_argument('--nb_randoms', type=int,
                        help='Number random events [Default=500]')
    parser.add_argument('--nb_triggers', type=int,
                        help='Number trigger events [Default=all available]')

    parser.add_argument('--trace_length_ms', type=float, help='Trace length [ms]')
    parser.add_argument('--pretrigger_length_ms', type=float,
                        help='Pretrigger length [ms] [default: 1/2 trace length]')

    parser.add_argument('--nb_samples', type=float, help='Trace length (# samples)')
    parser.add_argument('--nb_samples_pretrigger', type=float,
                        help='Pretrigger length (# samples)  [Default: 1/2 trace length]')

    
    parser.add_argument('--fall_time', nargs='+', type=str,
                        help=('Template fall time in usec '
                              '(if different values between channels: '
                              'space or comma seperated,  following "chan_to_trigger" channels) '
                              '[Default: 30 usec]'))

    parser.add_argument('--rise_time', nargs='+', type=str,
                        help=('Template rise time in usec '
                              '(if different values between channels: '
                              'space or comma seperated,  following "chan_to_trigger" channels) '
                              '[Default: 20 usec]'))

    parser.add_argument('--threshold', nargs='+', type=str,
                        help=('Trigger sigma threshold '
                              '(if different values between channels: '
                              'space or comma seperated,  following "chan_to_trigger" channels) '
                              '[Default: 10]'))

    parser.add_argument('--chan_to_trigger',  nargs='+', type=str,
                        help=('Detector channel name or ADC channel(s) to individually trig on, '
                              'space or comma separated '
                              '(If ADC number, range using "-" allowed, example 0,2-4). '
                              '[Default: all channels available in raw data]'))

    parser.add_argument('--pileup_window', type=float,
                        help=('Window in usec for removing pileup on individual channels '
                              '[default = 0 usec]'))

    parser.add_argument('--coincident_window', type=float,
                        help=('Window in usec for merging coincident events on channels '
                              'from chan_to_trigger (default = 50 usec)'))

    parser.add_argument('--is_negative_pulse', action='store_true', help='Negative pulse')

    parser.add_argument('--save-filter', '--save_filter', dest='save_filter',
                        action='store_true',
                        help='Save PSD/Template in a pickle file')

    parser.add_argument('--filter_file', type=str,
                        help='Full path to noise pickle file')

    parser.add_argument('--prefix', '--output_prefix', '--output_group_prefix',
                        dest='output_group_prefix', type=str,
                        help='Output group prefix [Default: "threshtrigger"]')

    parser.add_argument('--comment', '--output_comment','--output_group_comment',
                        dest='output_group_comment', type=str,
                        help='Output group comment [Default: same as continuous data]')

    parser.add_argument('--output_base_path',
                        type=str,
                        help=('Base path to output group (if different than continuous data)'))

    parser.add_argument('--output_group_name','--output_group_path',
                        dest='output_group_name',
                        type=str,
                        help=('Name to output group (if exist already)'
                              'path can be included (optional)'))
    
    parser.add_argument('--processing_setup', type=str,
                        help='Processing setup file (full path if not in pytesdaq/config)')
                        
    parser.add_argument('--nb_cores', type=int,
                        help='Maximum number of cores used for trigger processing [Default=1]')
    
    args = parser.parse_args()

    
    # check some arguments
    if not args.acquire_random and not args.acquire_trigger and not args.calc_filter:
        print('ERROR: Randoms ("--acquire-rand") and/or Triggers ("--acquire-trig") ' +
              ' and/or calc PSD ("--calc-psd") need to be enabled!')
        exit(0)
    

   
    # ---------------------------
    # Processing type(s)
    # ---------------------------
    acquire_random = False
    acquire_trigger = False
    calc_filter = False

    if args.acquire_random:
        acquire_random = True
    if args.acquire_trigger:
        acquire_trigger = True
    if args.calc_filter:
        calc_filter = True

    if not (acquire_random
            or acquire_trigger
            or  calc_filter):
        print('An action is required!')
        print('("acquire_random", "calc_filter", and/or "acquire_trigger")')
        exit()
        
    
    # ---------------------------
    # Default processing settings
    # ---------------------------
    proc_config = dict()
    proc_config['input_group_path'] = None
    proc_config['input_series'] = None
    proc_config['chan_to_trigger'] = 'all'
    proc_config['nb_randoms'] = 500
    proc_config['nb_triggers'] = -1
    proc_config['rise_time'] = [20]
    proc_config['fall_time'] = [30]
    proc_config['threshold'] = [10]
    proc_config['pileup_window'] = 0
    proc_config['coincident_window'] = 50
    proc_config['trace_length_ms'] = None
    proc_config['pretrigger_length_ms'] = None
    proc_config['nb_samples'] = None
    proc_config['nb_samples_pretrigger'] = None
    proc_config['save_filter'] = False
    proc_config['is_negative_pulse'] = False
    proc_config['output_group_name'] = None
    proc_config['output_group_prefix'] = None
    proc_config['output_group_comment'] = None
    proc_config['output_base_path'] = None
    proc_config['filter_file'] = None
    proc_config['nb_cores'] = 1
    

    # ------------------
    # Load setup file
    # ------------------

    if args.processing_setup:
        processing_setup = args.processing_setup

        if not os.path.isfile(processing_setup) and processing_setup.find('/')==-1:
            this_dir = os.path.dirname(os.path.realpath(__file__))
            processing_setup = this_dir + '/../pytesdaq/config/' + processing_setup 

        if not os.path.isfile(processing_setup ):
            print('ERROR: Processing setup file "' + processing_setup  + '" not found!')
            exit()

        config_reader = settings.Config(setup_file=processing_setup)
        config_from_file = config_reader.get_processing_setup()
        if config_from_file is None:
            print('ERROR: Unable to get information from processing setup file "' + processing_setup  + '"!')
            exit()

        # check config names
        param_list = proc_config.keys()
        for key in config_from_file.keys():
            if key not in param_list:
                print('ERROR: Parameter "'
                      +  key 
                      + '" from processing file is not recognized!')
                exit()

            
        # overwrite default
        for item,val in config_from_file.items():
            proc_config[item] = val
            

    # ------------------
    # input Arguments
    # (overwrite default or 
    # values from setup file)
    # ------------------
    
    if  args.input_group_path:
        proc_config['input_group_path'] = args.input_group_path
    if args.input_series:
        proc_config['input_series'] = arg_utils.extract_list(args.input_series)
    if args.nb_randoms:
        proc_config['nb_randoms'] = int(args.nb_randoms)
    if args.nb_triggers:
        proc_config['nb_triggers'] = int(args.nb_triggers)
    if args.trace_length_ms:
        proc_config['trace_length_ms'] = float(args.trace_length_ms)
    if args.pretrigger_length_ms:
        proc_config['pretrigger_length_ms'] = float(args.pretrigger_length_ms)
    if args.nb_samples:
        proc_config['nb_samples'] = int(args.nb_samples)
    if args.nb_samples_pretrigger:
        proc_config['nb_samples_pretrigger'] = int(args.nb_samples_pretrigger)
    if args.chan_to_trigger:
        proc_config['chan_to_trigger'] = arg_utils.extract_list(args.chan_to_trigger)
    if args.threshold:
        proc_config['threshold'] = [float(i) for i in arg_utils.extract_list(args.threshold)]
    if args.rise_time:
        proc_config['rise_time'] = [float(i) for i in arg_utils.extract_list(args.rise_time)]
    if args.fall_time:
        proc_config['fall_time'] = [float(i) for i in arg_utils.extract_list(args.fall_time)]
    if args.save_filter:
        proc_config['save_filter'] = True
    if args.is_negative_pulse:
        proc_config['is_negative_pulse'] = True
    if args.pileup_window:
        proc_config['pileup_window'] = args.pileup_window
    if args.coincident_window:
        proc_config['coincident_window'] = args.coincident_window
    if args.output_group_name:
        proc_config['output_group_name'] = args.output_group_name
    if args.output_group_prefix:
        proc_config['output_group_prefix'] = args.output_group_prefix
    if args.output_group_comment:
        proc_config['output_group_comment'] = args.output_group_comment
    if args.output_base_path:
        proc_config['output_base_path'] = args.output_base_path
    if args.filter_file:
        proc_config['filter_file'] = args.filter_file
    if args.nb_cores:
        proc_config['nb_cores'] = args.nb_cores

    # ------------------
    # input/output path
    # ------------------

    input_path = Path(proc_config['input_group_path'])
    if not input_path.is_dir():
        print('ERROR: No directory found for "' + proc_config['input_group_path']
              + '". Check input path!')
        exit(0)
        
    # group name/path
    if proc_config['output_base_path'] is None:
        proc_config['output_base_path'] = str(input_path.parent)
        

    if proc_config['output_group_name'] is not None:
        output_path =  Path(proc_config['output_group_name'])
        proc_config['output_group_name'] = str(output_path.name)
        if len(list(output_path.parts))>1:
             proc_config['output_base_path'] = str(output_path.parent)



    # case only PSD calculation
    if (calc_filter and not acquire_random
        and output_group_name is None):
        print(('ERROR: A group name with randoms needs to be provided '
               ' (--output_group_name) or randoms need to be acquired'
               ' (--acquire-rand)'))
        exit()

    if (acquire_trigger and not calc_filter
        and proc_config['filter_file'] is None):
        print(('ERROR: A filter file needs be provided (--filter_file)'
               ' or calculated (--calc-filter)'))
        exit()


    if calc_filter and proc_config['filter_file'] is not None:
        print(('ERROR: PSD/Template calculation is enabled (--calc-filter)'
               ', no filter file should be given (--filter_file)'))
        exit()
    
    if (proc_config['nb_samples'] is not None
        and proc_config['trace_length_ms'] is not None):
        print('ERROR: Either "nb_samples" or "trace_length_ms" can be used, not both!')
        exit()

    if (proc_config['nb_samples_pretrigger'] is not None
        and proc_config['pretrigger_length_ms'] is not None):
        print(('ERROR: Either "nb_samples_pretrigger" or "trace_length_ms" '
               'can be used, not both!'))
        exit()



    # ------------------
    # Launch
    # ------------------

    data_inst = ContinuousData(
        proc_config['input_group_path'],
        input_series=proc_config['input_series'],
        output_group_prefix=proc_config['output_group_prefix'],
        output_group_comment=proc_config['output_group_comment'],
        output_base_path=proc_config['output_base_path'],
        output_group_name=proc_config['output_group_name'],
        trigger_channels=proc_config['chan_to_trigger'],
        trace_length_ms=proc_config['trace_length_ms'],
        pretrigger_length_ms=proc_config['pretrigger_length_ms'],
        nb_samples=proc_config['nb_samples'],
        nb_samples_pretrigger=proc_config['nb_samples_pretrigger'],
        negative_pulse=proc_config['is_negative_pulse'],
        filter_file=proc_config['filter_file']
    )
    

    # acquire randoms
    if acquire_random:
        data_inst.acquire_randoms(nb_events=int(proc_config['nb_randoms']))

    # calc filter
    if calc_filter:
        data_inst.create_template(proc_config['rise_time'],  proc_config['fall_time'])
        data_inst.calc_psd(save_filter=proc_config['save_filter'])
        
                        
    # acquire trigger
    if acquire_trigger:
        data_inst.acquire_trigger(nb_events=int(proc_config['nb_triggers']),
                                  threshold=proc_config['threshold'],
                                  pileup_window=proc_config['pileup_window'],
                                  coincident_window=proc_config['coincident_window'],
                                  nb_cores=int(proc_config['nb_cores']))
                                  
   
            
