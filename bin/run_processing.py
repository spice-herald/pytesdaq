import argparse
import numpy as np
import os
import time
from datetime import datetime
from glob import glob
from pytesdaq.processing.trigger import ContinuousData

if __name__ == "__main__":


    parser = argparse.ArgumentParser(description='Launch Processing')
    parser.add_argument('--series_dir', type = str, help='Continuous data directory name')
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
    args = parser.parse_args()

    
    # check arguments
    if not args.series_dir:
        print('ERROR: Continuous data directory name needs to be provided')
        exit(0)
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
    series_dir = args.series_dir
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


    # File list 
    data_dir = raw_path + '/' + series_dir
    file_list = []
    if os.path.isdir(data_dir):
        file_list = glob(data_dir+'/*.hdf5')
    else:
        print('ERROR: No continuous data found in "' + data_dir +'". Check input path!')
        exit(0)

    # output name
    now = datetime.now()
    series_day = now.strftime('%Y') +  now.strftime('%m') + now.strftime('%d') 
    series_time = now.strftime('%H') + now.strftime('%M')

    directory_path = raw_path + '/trigger_' +  series_day + '_' + series_time
    series = 'I' + str(facility) +'_D' + series_day + '_T' +  series_time + now.strftime('%S')


    if not os.path.isdir(directory_path ):
        os.mkdir(directory_path)

    
    data_inst = ContinuousData(file_list,
                               nb_events_randoms=nb_randoms,
                               nb_events_trigger=nb_triggers,
                               trace_length_ms=trace_length_ms,
                               pretrigger_length_ms=pretrigger_length_ms,
                               nb_samples=nb_samples,
                               nb_samples_pretrigger=nb_samples_pretrigger,
                               series_name=series,
                               data_path=directory_path,
                               negative_pulse=is_negative_pulse,
                               save_filter=save_filter)
    
    data_inst.create_template(rise_time, fall_time)
    data_inst.acquire_randoms()
    data_inst.acquire_trigger()
            
