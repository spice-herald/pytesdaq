import argparse
import numpy as np
import os
import time
from datetime import datetime
from glob import glob
from pytesdaq.processing.trigger import ContinuousData

if __name__ == "__main__":


    parser = argparse.ArgumentParser(description='Launch Processing')
    parser.add_argument('-s','--series', dest="series", type = str, help='Series name (format string Ix_Dyyyymmdd_Thhmmss)')
    parser.add_argument('--raw_path', type = str, help='Raw data path')
    parser.add_argument('--nb_randoms', type=float, help='Number random events (default=500)')
    parser.add_argument('--nb_triggers', type=float, help='Number trigger events (default=all)')
    parser.add_argument('--trace_length_ms', type=float, help='Trace length [ms] [default: ')
    parser.add_argument('--pretrigger_length_ms', type=float,
                        help='Pretrigger length [ms] [default: 1/2 trace lenght]')
    parser.add_argument('--nb_samples', type=float, help='Trace length [# samples]')
    parser.add_argument('--nb_samples_pretrigger', type=float,
                        help='Pretrigger length [# samples]  (default: 1/2 trace lenght)')
    parser.add_argument('--threshold', type=float, help='Trigger sigma threshold (default=10)')
    parser.add_argument('--rise_time', type=float, help='Template rise time in usec [20 usec]')
    parser.add_argument('--fall_time', type=float, help='Template fall time in usec [30 usec]')
    parser.add_argument('--is_negative_pulse', action='store_true', help='Nagative pulse')
    parser.add_argument('--save_filter', action='store_true', help='Save PSD/Template in a pickle file')
    parser.add_argument('--facility', type = int, help='Facility number [default=2]')
    args = parser.parse_args()

    
    # check arguments
    if not args.raw_path:
        print('ERROR: Data path needs to be provided')
        exit(0)
    if not args.trace_length_ms and not args.nb_samples:
        print('ERROR: Either "trace_length_ms" or "nb_samples" needs to be provided')
        exit(0)
    if args.pretrigger_length_ms and  args.nb_samples_pretrigger:
        print('ERROR: Either "pretrigger_length_ms" or "nb_samples" needs to be provided, not both!')
        exit(0)


    # default
    facility = 2
    threshold = 10
    nb_randoms = 500
    nb_triggers = -1
    rise_time = 20e-6
    fall_time = 30e-6
    trace_length_ms = None
    pretrigger_length_ms = None
    nb_samples = None
    nb_samples_pretrigger = None
    save_filter = False
    is_negative_pulse = False
    

    # input
    series = None
    if args.series:
        series = args.series
    raw_path = args.raw_path
    if args.nb_randoms:
        nb_randoms = int(args.nb_randoms)
    if args.nb_triggers:
        nb_triggers = int(args.nb_triggers)
    if args.trace_length_ms:
        trace_length_ms = float(args.trace_length_ms)
    if args.pretrigger_length_ms:
        pretrigger_length_ms = float(args.pretrigger_length_ms)
    if args.nb_samples:
        nb_samples = int(args.nb_samples)
    if args.nb_samples_pretrigger:
        nb_samples_pretrigger = int(args.nb_samples_pretrigger)
    if args.rise_time:
        rise_time = float(args.rise_time) * 1e-6
    if args.fall_time:
        fall_time = float(args.fall_time) * 1e-6
    if args.save_filter:
        save_filter = True
    if args.is_negative_pulse:
        is_negative_pulse = True
    if args.facility:
        facility = args.facility


    # input directory
    input_data_dir = raw_path
    input_data_dir_split = input_data_dir.split('/')
    if series is not None and input_data_dir_split[-1]!=series:
        input_data_dir_temp = input_data_dir + '/' + series
        if os.path.isdir(input_data_dir_temp):
            input_data_dir = input_data_dir_temp

    if not os.path.isdir(input_data_dir):
        print('ERROR: No directory found for "' + input_data_dir +'". Check input path!')
        exit(0)

    if input_data_dir.find('continuous_')==-1:
        print('ERROR: Directory "' + input_data_dir + '" does not appear to be continuous data')
        exit(0)

    
        
              
    # file list
    file_list = []
    file_name_wildcard = '*.hdf5'
    if series is not None:
        file_name_wildcard = '*'+series+'_*.hdf5'
        
    file_list = glob(input_data_dir + '/' + file_name_wildcard)
    if not file_list:
        
        print('ERROR: No raw data found in "' + input_data_dir + '"')
        if series:
            print('with series name "' + series +'"!')
        exit(0)


            
    # output name
    now = datetime.now()
    series_day = now.strftime('%Y') +  now.strftime('%m') + now.strftime('%d') 
    series_time = now.strftime('%H') + now.strftime('%M')
    series_name= 'I' + str(facility) +'_D' + series_day + '_T' +  series_time + now.strftime('%S')

    # output directory
    output_dir = raw_path
    pos_cont = input_data_dir_split[-1].find('continuous_')
    if pos_cont!=-1:
        series_dir = input_data_dir_split[-1][11:]
        output_dir = raw_path[0:-len(input_data_dir_split[-1])] + 'trigger_' + series_dir 
           
    if not os.path.isdir(output_dir):
        os.mkdir(output_dir)

    
    data_inst = ContinuousData(file_list,
                               nb_events_randoms=nb_randoms,
                               nb_events_trigger=nb_triggers,
                               trace_length_ms=trace_length_ms,
                               pretrigger_length_ms=pretrigger_length_ms,
                               nb_samples=nb_samples,
                               nb_samples_pretrigger=nb_samples_pretrigger,
                               series_name=series_name,
                               data_path=output_dir,
                               negative_pulse=is_negative_pulse,
                               save_filter=save_filter)
    
    data_inst.create_template(rise_time, fall_time)
    data_inst.acquire_randoms()
    data_inst.acquire_trigger()
            
