import argparse
import pytesdaq.config.settings as settings
import pytesdaq.instruments.control as instrument
from pytesdaq.utils import  arg_utils, connection_utils
import os
from math import nan
from pprint import pprint

if __name__ == "__main__":

    # ========================
    # Input arguments
    # ========================
    parser = argparse.ArgumentParser(description="Instruments controller")

    # channels
    parser.add_argument('-c','--channels', dest='channels',
                        nargs= '+', type=str, 
                        help=('Comma and/or space separated "detector" '
                              'OR "readout" TES wiring channels. '))
    # Detector settings
    parser.add_argument('--tes_bias_uA', nargs='?', type=float, const=nan, default=None,
                       help='Read/write TES bias in units of "uA"')
    parser.add_argument('--squid_bias_uA', nargs='?', type=float, const=nan, default=None,
                       help='Read/write SQUID bias in units of "uA"')
    parser.add_argument('--lock_point_mV', nargs='?', type=float, const=nan, default=None,
                       help='Read/write Lock point voltage [mV]')
    parser.add_argument('--preamp_gain', nargs='?', type=float, const=nan, default=None,
                       help='Read/write Variable preamp gain')
    parser.add_argument('--output_gain', nargs='?', type=float, const=nan, default=None,
                       help='Read/write Variable output gain')
    
    parser.add_argument('--read_all', action="store_true",help='Read all settings')


    # signal generator
    parser.add_argument('--signal_gen_on', action="store_true", 
                        help='Turn on signal gen')
    parser.add_argument('--signal_gen_off', action="store_true", help='Turn off signal gen')
    parser.add_argument('--signal_gen_autorange_on', action="store_true",
                        help='Turn on signal gen auto range')
    parser.add_argument('--signal_gen_autorange_off', action="store_true",
                        help='Turn off signal gen auto range')
    
    parser.add_argument('--signal_gen_amplitude_mV', '--signal_gen_voltage_mV',
                        dest='signal_gen_voltage_mV',
                        nargs='?', type=float, const=nan, default=None,
                       help='Signal generator voltage amplitude [mV]')
    parser.add_argument('--signal_gen_offset_mV', nargs='?', type=float,
                        const=nan, default=None,
                       help='Signal generator DC offset [mV]')
    parser.add_argument('--signal_gen_frequency_Hz', nargs='?', type=float,
                        const=nan, default=None,
                       help='Signal generator frequency [Hz]')
    
    parser.add_argument('--signal_gen_shape', nargs='?', type=str, default=None, const=nan,
                       help='Signal generator shape [sine, square, triangle, ramp, dc]')
    parser.add_argument('--signal_gen_phase', nargs='?', type=float, default=None, const=nan,
                       help='Signal generator phase')
    
    # verbose
    parser.add_argument('--verbose', action="store_true", help='Screen output')
    
    # setup file
    parser.add_argument('--setup_file', type=str,
                       help='Configuration setup file name (full path) [default: pytesdaq/config/setup.ini]')
    
    args = parser.parse_args()

    verbose = False
    if args.verbose:
        verbose = True
    
    
    # ========================
    # Instrument Configuration
    # ========================

    # file name
    setup_file = None
    if args.setup_file:
        setup_file = args.setup_file
    else:
        # config file, check default
        this_dir = os.path.dirname(os.path.realpath(__file__))
        setup_file = os.path.normpath(this_dir + '/../pytesdaq/config/setup.ini')

    if not os.path.isfile(setup_file):
        print(f'ERROR: Setup file "{setup_file}" not found!')
        exit()


    # read
    config = settings.Config(setup_file=setup_file)


    # ========================
    # Channels
    # ========================
    
    is_signal_gen = False
    if (args.signal_gen_on or args.signal_gen_off
        or args.signal_gen_autorange_on
        or args.signal_gen_autorange_off
        or args.signal_gen_offset_mV is not None
        or args.signal_gen_voltage_mV is not None
        or args.signal_gen_frequency_Hz is not None
        or args.signal_gen_shape is not None
        or args.signal_gen_phase is not None):
        is_signal_gen = True


    # check if channels selected
    if  (args.channels is None and not is_signal_gen):
        print('Please select a channel(s)! Type --help for channel argument')
        exit()
            
    # channels
    channels = []
    nb_channels = 0
    if args.channels:
        channels = arg_utils.extract_list(args.channels)
        nb_channels = len(channels)
   
    # convert to detector_channels
    connection_df = config.get_adc_connections()
    connection_dict = connection_utils.get_items(connection_df)
    detector_channels = []

    for chan in channels:
        
        if chan in connection_dict['detector_channel']:
            detector_channels.append(chan)
        elif chan in connection_dict['tes_channel']:
            detector_chan = connection_df.query(
                'tes_channel == @chan'
            )['detector_channel'].values

            if len(detector_chan) != 1:
                print(f'ERROR: Multiple "detector_channel" names found '
                      f'for channel {chan}! You need to modify setup file. '
                      f'to have unique names')
            else:
                detector_channels.append(detector_chan[0])
        else:
            print(f'ERROR: channel {chan} not recognized. '
                  f'Modify setup file!')
            

    if not is_signal_gen and nb_channels==0:
        print('Please select a channel(s)! Type --help for channel argument.')
        exit()
        
    # ========================
    # Instantiate Instrument
    # ========================

    myinstruments = instrument.Control(setup_file=setup_file,
                                       dummy_mode=False, verbose=verbose)



    
    # ========================
    # SQUID/TES controller
    # ========================

    
    # loop channels
    for ichan, chan in enumerate(detector_channels):

        chan_display = channels[ichan]
     
        # -----------
        # TES bias
        # -----------
        if args.tes_bias_uA is not None:

            #  write to board
            if args.tes_bias_uA is not nan:
                
                myinstruments.set_tes_bias(float(args.tes_bias_uA), unit='uA',
                                          detector_channel=chan)

            # read from board
            readback = myinstruments.get_tes_bias(detector_channel=chan,
                                                 unit='uA')
                
            print(f'TES bias for channel {chan_display}  = {readback} uA')
                    
            
        # -----------
        # SQUID bias
        # -----------
        if args.squid_bias_uA is not None:

            #  write to board
            if args.squid_bias_uA is not nan:
                myinstruments.set_squid_bias(float(args.squid_bias_uA),
                                            unit='uA',
                                            detector_channel=chan)

            # read from board
            readback = myinstruments.get_squid_bias(detector_channel=chan,
                                                   unit='uA')

            print(f'SQUID bias for channel {chan_display} = {readback} uA')
            
        
        # -----------
        # Lock point
        # -----------
        if args.lock_point_mV is not None:

            #  write to board
            if args.lock_point_mV is not nan:
                myinstruments.set_lock_point(float(args.lock_point_mV),
                                            unit='mV',
                                            detector_channel=chan)
                
            # read from board
            readback = myinstruments.get_lock_point(detector_channel=chan,
                                                   unit='mV')

            print(f'Lock point  for channel {chan_display} = {readback} mV') 
                         
    
        # -----------
        # Preamp Gain
        # -----------
        if args.preamp_gain is not None:

            #  write to board
            if args.preamp_gain is not nan:
                myinstruments.set_preamp_gain_bandwidth(args.preamp_gain,
                                                       detector_channel=chan)
                
            # read from board
            readback = myinstruments.get_preamp_total_gain(detector_channel=chan)

            # display
            print(f'Total preamp gain (fix*variable gains) '
                  f'for channel {chan_display} = {readback}') 
          
                    
    
        # -----------
        # Output Gain
        # -----------
        if args.output_gain is not None:

            #  write to board
            if args.output_gain is not nan:
                myinstruments.set_output_gain(args.output_gain,
                                             detector_channel=chan)
                                
            # read from board
            readback = myinstruments.get_output_total_gain(detector_channel=chan)
            
            print(f'Total output gain (fix*variable gains) '
                  f'for channel {chan_display} = {readback}') 
                                
    # -----------
    # Read all 
    # -----------

    
    if args.read_all:

        if nb_channels>0:
            settings = myinstruments.read_all(detector_channel_list=detector_channels)
            pprint(settings)
        else:
            print('ERROR: channel required to read all settings!')
            exit()
        

        
            
    # -----------------
    # Signal generator
    # -----------------
    if args.signal_gen_on and args.signal_gen_off:
        print('ERROR: Turn signal generator on or off, not both!')
    
    if args.signal_gen_on:
        myinstruments.set_signal_gen_onoff('on')
        
    if args.signal_gen_off:
        myinstruments.set_signal_gen_onoff('off')

    if args.signal_gen_autorange_on:
        myinstruments.get_signal_gen_controller().set_auto_range('on')

    if args.signal_gen_autorange_off:
        myinstruments.get_signal_gen_controller().set_auto_range('off')


    if args.signal_gen_voltage_mV is not None:

        #  write to sg
        if args.signal_gen_voltage_mV is not nan:
            
            print(f'INFO: Setting amplitude to {args.signal_gen_voltage_mV} mV')
            
            myinstruments.set_signal_gen_params(
                voltage=float(args.signal_gen_voltage_mV),
                voltage_unit='mV'
                )
                            
        # read from board
        readback = myinstruments.get_signal_gen_params()
       
        # display
        print(f'Signal generator amplitude = {readback["voltage"]*1e3} mV')
        
    if args.signal_gen_frequency_Hz is not None:

        #  write to sg
        if args.signal_gen_frequency_Hz is not nan:
            myinstruments.set_signal_gen_params(frequency=args.signal_gen_frequency_Hz)
                            
        # read from board
        readback = myinstruments.get_signal_gen_params()

        # display
        print(f'Signal generator frequency = {readback["frequency"]} Hz')
                
    if args.signal_gen_offset_mV is not None:
        
        #  write to board
        if args.signal_gen_offset_mV is not nan:
            print(f'INFO: Setting offset to {args.signal_gen_offset_mV} mV')
            
            myinstruments.set_signal_gen_params(
                offset=args.signal_gen_offset_mV,
                offset_unit='mV'
            )
                            
        # read from board
        readback = myinstruments.get_signal_gen_params()

        # display
        print(f'Signal generator offset = {readback["offset"]*1e3} mV')
                 
        
    if args.signal_gen_shape is not None:

        #  write to board
        if args.signal_gen_shape is not nan:
            
            print(f'INFO: Setting shape to "{args.signal_gen_shape}"')
            
            myinstruments.set_signal_gen_params(shape=args.signal_gen_shape)
                                        
        # read from board
        readback = myinstruments.get_signal_gen_params()

        # display
        shape = readback['shape']
        print(f'Signal generator shape = "{shape}"')
                         
    if args.signal_gen_phase is not None:
        
        #  write to board
        if args.signal_gen_phase is not nan:
            
            print(f'INFO: Setting phase to {args.signal_gen_phase} Deg')
            
            myinstruments.set_signal_gen_params(
                phase=args.signal_gen_phase
            )
                            
        # read from board
        readback = myinstruments.get_signal_gen_params()

        # display
        print(f'Signal generator phase = {readback["phase"]} degrees')
        
