import argparse
import numpy as np
import os
import time
from datetime import datetime
from glob import glob
from pathlib import Path
import pytesdaq as ptd
from pytesdaq.processing.trigger import ContinuousData
import pytesdaq.config.settings as settings
from pytesdaq.utils import arg_utils
import stat
from pytesdaq.display import SeriesGroup



if __name__ == "__main__":

    # ------------------
    # Input arguments
    # ------------------
    parser = argparse.ArgumentParser(description='Launch Trigger Processing')
    parser.add_argument('--raw_path', '--group_path', dest='raw_path', type=str,
                        help='Path to raw data group (including group name)')
    parser.add_argument('-s','--series', dest='series', nargs='+', type=str, 
                        help=('Series name(s) (format string Ix_Dyyyymmdd_Thhmmss,'
                              'space or comma seperated)' 
                              '[Default: all series]'))
    #parser.add_argument('--enable-rand', '--enable-random', dest='enable_random',
    #                    action='store_true', help='Acquire randoms')
    #parser.add_argument('--enable-trig', '--enable-trigger', dest='enable_trigger',
    #                    action='store_true', help='Acquire randoms')
    parser.add_argument('--nb_randoms', type=float, help='Number random events [Default=500]')
    parser.add_argument('--nb_triggers', type=float,
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
                        help=('Detector channel name or ADC channel(s) to trig on, space or comma separated '
                              '(If ADC number, range using "-" allowed, example 0,2-4). '
                              '[Default: all channels available in raw data]'))
    parser.add_argument('--pileup_window', type=float,
                        help=('Window in usec for removing pileup on individual channels '
                              '[default = 0 usec]'))
    parser.add_argument('--coincident_window', type=float,
                        help=('Window in usec for merging coincident events on channels '
                              'from chan_to_trigger (default = 50 usec)'))
    parser.add_argument('--is_negative_pulse', action='store_true', help='Negative pulse')
    parser.add_argument('--save_filter', action='store_true',
                        help='Save PSD/Template in a pickle file')
    parser.add_argument('--filter_file', type = str,
                        help = 'Full path to noise pickle file')
    parser.add_argument('--output_group_name', type = str,
                        help = ('Output group name if using previously created group name '
                                '(use full path if different base path than continuous data)'))
    parser.add_argument('--output_group_prefix', type = str,
                        help = 'Output group prefix [Default: "threshtrigger"]')
    parser.add_argument('--output_group_comment', type = str,
                        help = 'Output group comment [Default: same as continuous data]')
    
    
    args = parser.parse_args()

    
    # check arguments
    #if not args.enable_random and not args.enable_trigger:
    #    print('ERROR: Randoms ("--enable-rand") and/or Triggers ("--enable-trig") need to be enabled!')
    #    exit(0)
    if not args.raw_path:
        print('ERROR: Data path needs to be provided')
        exit(0)
    if not args.trace_length_ms and not args.nb_samples:
        print('ERROR: Either "trace_length_ms" or "nb_samples" needs to be provided')
        exit(0)
    if args.pretrigger_length_ms and  args.nb_samples_pretrigger:
        print('ERROR: Either "pretrigger_length_ms" or "nb_samples" needs to be provided, not both!')
        exit(0)


   
    # ------------------
    # Default 
    # ------------------
    enable_random = False
    enable_trigger = False
    chan_to_trigger = 'all'
    nb_randoms = 500
    nb_triggers = -1
    rise_time = [20e-6]
    fall_time = [30e-6]
    threshold = [10]
    pileup_window = 0
    coincident_window = 50e-6
    trace_length_ms = None
    pretrigger_length_ms = None
    nb_samples = None
    nb_samples_pretrigger = None
    save_filter = False
    is_negative_pulse = False
    group_name = None
    output_group_name = None
    output_group_prefix = None
    output_group_comment = None
    
    # ------------------
    # Parse arguments 
    # ------------------
    raw_path = args.raw_path
    series = None
    if args.series:
        series = arg_utils.extract_list(args.series)
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
    if args.chan_to_trigger:
        chan_to_trigger = arg_utils.extract_list(args.chan_to_trigger)
    if args.threshold:
        threshold = [float(i) for i in arg_utils.extract_list(args.threshold)]
    if args.rise_time:
        rise_time = [float(i)*1e-6 for i in arg_utils.extract_list(args.rise_time)]
    if args.fall_time:
        fall_time = [float(i)*1e-6 for i in arg_utils.extract_list(args.fall_time)]
    if args.save_filter:
        save_filter = True
    if args.is_negative_pulse:
        is_negative_pulse = True
    if args.pileup_window:
        pileup_window = args.pileup_window * 1e-6
    if args.coincident_window:
        coincident_window = args.coincident_window * 1e-6
    if args.output_group_name:
        output_group_name = args.output_group_name
    if args.output_group_prefix:
        output_group_prefix = args.output_group_prefix
    if args.output_group_comment:
        output_group_comment = args.output_group_comment
    #if args.enable_random:
    #    enable_random = True
    #if args.enable_trigger:
    #    enable_trigger = True
        
     
    # ------------------
    # input path
    # ------------------

    input_path = Path(raw_path)
    
    if not input_path.is_dir():
        print('ERROR: No directory found for "' + raw_path +'". Check input path!')
        exit(0)
        
    # group name/path
    group_name = str(input_path.name)
    group_path = str(input_path.parent)

    
    # ------------------
    # file list
    # ------------------
    
    file_list = []
    file_name_wildcard = '*.hdf5'
    if series is not None:
        for serie in series:
            file_name_wildcard = '*'+serie+'_*.hdf5'
            file_list.extend(glob(raw_path + '/' + file_name_wildcard))
    else:
        file_list = glob(raw_path + '/' + file_name_wildcard)
    
    if not file_list:
        print('ERROR: No raw data found in "' + raw_path + '"')
        exit()

    # sort
    file_list.sort()
         

    # ------------------
    # Get info from
    # first file
    # ------------------
    print(' ')
    print('Checking raw data group "' + group_name + '"')
    group = SeriesGroup(group_name, group_path)
    group_info, series_info = group.get_group_info(include_series_info=True)
    facility = group_info['facility']
    group_comment = group_info['group_comment']

    # get channel mapping (assume same for all series)
    connection_table = None
    for series_key in series_info.keys():
        if 'connection_table' in series_info[series_key]:
            connection_table = series_info[series_key]['connection_table']
            break

    if (chan_to_trigger is not 'all' and connection_table is None):
        print('ERROR: Unable to find connection table in raw data! ')
        exit()
    
            
    # ------------------
    # output directory
    # ------------------
    output_dir = None
    if output_group_name is not None:
        if os.path.idir(output_group_name):
            output_dir = output_group_name
        else:
            output_dir = group_path + '/' + output_group_name
            if not os.path.idir(output_dir):
                print('ERROR: Unable to find output directory "'
                      + output_dir + '"')
                exit()
    else:
                     
        # output name
        now = datetime.now()
        series_day = now.strftime('%Y') +  now.strftime('%m') + now.strftime('%d') 
        series_time = now.strftime('%H') + now.strftime('%M')
        series_name = 'I' + str(facility) +'_D' + series_day + '_T' +  series_time + now.strftime('%S')

        # output directory
        if output_group_prefix is None:
            output_group_prefix = 'threshtrigger'
        
        output_dir = group_path + '/' + output_group_prefix + '_' + series_name
        
        if not os.path.isdir(output_dir):
            try:
                os.makedirs(output_dir)
                os.chmod(output_dir, stat.S_IRWXG | stat.S_IRWXU | stat.S_IROTH | stat.S_IXOTH)
            except OSError:
                print('\nERROR: Unable to create directory "'+ output_dir  + '"!\n')
                exit()



    
                
    # ------------------
    # trigger channels
    # ------------------

    if chan_to_trigger is not 'all':

        chan_to_trigger_list = list()
        for chan in chan_to_trigger:
            
            # check if ADC channels
            chan_trigger_check = chan.replace('-','')
            if chan_trigger_check.isdigit():
                chan_list = arg_utils.hyphen_range(chan)
                chan_to_trigger_list.extend(chan_list)
            else:
                if connection_table is None:
                    print('ERROR: Unable to find connection table in raw data!' +
                          ' Use ADC channels for chan_to_trigger argument instead')
                    exit()
                adc_channel = connection_table.query('detector_channel == @chan')["adc_channel"].values
                if(len(adc_channel)!=1):
                    print('ERROR: chan_to_trigger input does not match an ADC channel. ' + 
                          'Check input or config/setup file')
                    exit()
                chan_to_trigger_list.append(int(adc_channel.astype(np.int)))

        nb_channels = len(chan_to_trigger_list)
        if nb_channels>1:
            if len(rise_time)==1:
                rise_time *= nb_channels
            if len(fall_time)==1:
                fall_time *= nb_channels
            if len(threshold)==1:
                threshold *= nb_channels            
    else:
        chan_to_trigger_list = 'all'

    
    #print(f'rise_time = {rise_time}')
    #print(f'threshold = {threshold}')
    #print(f'len(threshold) = {len(threshold)}')
    #print(f'len(chan_to_trigger_list) = {len(chan_to_trigger_list)}')
    #print('chan_to_trigger_list = ', chan_to_trigger_list)    

    
    if ((len(threshold) != len(chan_to_trigger_list)) and (chan_to_trigger_list is not 'all')):
        raise ValueError("Threshold must be the same size as chan_to_trigger")



    # ------------------
    # Launch
    # ------------------
    data_inst = ContinuousData(file_list,
                               nb_events_randoms=nb_randoms,
                               nb_events_trigger=nb_triggers,
                               trace_length_ms=trace_length_ms,
                               pretrigger_length_ms=pretrigger_length_ms,
                               nb_samples=nb_samples,
                               nb_samples_pretrigger=nb_samples_pretrigger,
                               chan_to_trigger=chan_to_trigger_list,
                               threshold=threshold,
                               series_name=series_name,
                               data_path=output_dir,
                               negative_pulse=is_negative_pulse,
                               save_filter=save_filter,
                               pileup_window=pileup_window,
                               coincident_window=coincident_window)
    data_inst.create_template(rise_time, fall_time)
    data_inst.acquire_randoms()
    data_inst.acquire_trigger()
            
