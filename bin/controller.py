import argparse
import pytesdaq.config.settings as settings
import pytesdaq.instruments.control as instrument
from pytesdaq.utils import  arg_utils
import os
from math import nan

if __name__ == "__main__":

    # ========================
    # Input arguments
    # ========================
    parser = argparse.ArgumentParser(description="Instruments controller")

    # channels
    parser.add_argument('--tes_channels', dest='tes_channels', type = str, default=None,
                        help = 'TES readout channel(s) name (commas sepearated)')
    parser.add_argument('--detector_channels', dest='detector_channels', type = str, default=None,
                        help = 'Detector channel(s) name (commas sepearated)')
      
    # Detector settings
    parser.add_argument('--tes_bias', nargs='?', type=float, const=nan, default=None,
                        help = 'Read/write TES bias [uA]')
    parser.add_argument('--squid_bias', nargs='?', type = float, const=nan, default=None,
                        help = 'Read/write SQUID bias [uA]')
    parser.add_argument('--lock_point', nargs='?', type = float, const=nan, default=None,
                        help = 'Read/write Lock point voltage [mV]')
    parser.add_argument('--preamp_gain', nargs='?', type = float, const=nan, default=None,
                        help = 'Read/write Variable preamp gain')
    parser.add_argument('--output_gain', nargs='?', type = float, const=nan, default=None,
                        help = 'Read/write Variable output gain')
    
    parser.add_argument('--read_all', action="store_true", help = 'Read all settings')
    
    #parser.add_argument('--signal_gen_connection', nargs='?', type = str, const=nan, default=None,
    #                    help = 'Read/write signal generator connection(s): "tes" or "feedback" or both (comma seprated)')
    # parser.add_argument('--feedback_mode', nargs='?', type = str, const=nan, default=None, help = 'Feedback mode: "close" or "open"')

    # verbose
    parser.add_argument('--verbose',action="store_true",help='Screen output')
    
    # setup file
    parser.add_argument('--setup_file', type = str,
                        help = 'Configuration setup file name (full path) [default: pytesdaq/config/setup.ini]')
    
    args = parser.parse_args()


    # check if channels selected
    if  args.tes_channels is None and args.detector_channels is None and args.all is None:
        print('Please select TES or detector channel(s)! Type --help for channel arguments.')
        exit()
        

    verbose = False
    if args.verbose:
        verbose = True


    
    
    # ========================
    # Connection check
    # ========================

    # file name
    setup_file = None
    if args.setup_file:
        setup_file = args.setup_file
    else:
        this_dir = os.path.dirname(os.path.realpath(__file__))
        setup_file = this_dir + '/../pytesdaq/config/setup.ini'

    if not os.path.isfile(setup_file):
        print('ERROR: Setup file "' + setup_file + '" not found!')
        exit()


    # read
    config = settings.Config(setup_file=setup_file)


    # channels
    tes_channel_list = None
    detector_channel_list = None
    nb_channels = 0
    if args.tes_channels is not None:
        tes_channel_list = args.tes_channels.split(',')
        nb_channels = len(tes_channel_list)
    elif args.detector_channels is not None:
        detector_channel_list = args.detector_channels.split(',')
        nb_channels = len(detector_channel_list)


    if nb_channels==0:
        print('Please select TES or detector channel(s)! Type --help for channel arguments.')
        exit()
    

    
    # ========================
    # Read/Write board
    # ========================


    # instantiate
    myinstrument = instrument.Control(setup_file=setup_file, dummy_mode=False, verbose=verbose)


    # loop channels
    for ichan in range(nb_channels):

        # channel name
        tes_channel = None
        detector_channel = None
        channel = str()
        if tes_channel_list is not None:
            tes_channel =  str(tes_channel_list[ichan])
            channel = tes_channel 
        elif detector_channel_list is not None:
            detector_channel = str(detector_channel_list[ichan])
            channel = tes_channel 

        # -----------
        # TES bias
        # -----------
        if args.tes_bias is not None:

            #  write to board
            if args.tes_bias is not nan:
                myinstrument.set_tes_bias(args.tes_bias,
                                          tes_channel=tes_channel,
                                          detector_channel=detector_channel)

            # read from board
            readback = myinstrument.get_tes_bias(tes_channel=tes_channel,
                                                 detector_channel=detector_channel)
                
            print('TES bias for channel ' + channel + ' = ' + str(readback) + ' uA')
                    
            
        # -----------
        # SQUID bias
        # -----------
        if args.squid_bias is not None:

            #  write to board
            if args.squid_bias is not nan:
                myinstrument.set_squid_bias(args.squid_bias,
                                            tes_channel=tes_channel,
                                            detector_channel=detector_channel)

            # read from board
            readback = myinstrument.get_squid_bias(tes_channel=tes_channel,
                                                   detector_channel=detector_channel)
                
            print('SQUID bias for channel ' + channel + ' = ' + str(readback) + ' uA')
                    
    
        
        # -----------
        # Lock point
        # -----------
        if args.lock_point is not None:

            #  write to board
            if args.lock_point is not nan:
                myinstrument.set_lock_point(args.lock_point,
                                            tes_channel=tes_channel,
                                            detector_channel=detector_channel)

            # read from board
            readback = myinstrument.get_lock_point(tes_channel=tes_channel,
                                                   detector_channel=detector_channel)
                
            print('Lock point for channel ' + channel + ' = ' + str(readback) + ' mV')
                    
    
        # -----------
        # Preamp Gain
        # -----------
        if args.preamp_gain is not None:

            #  write to board
            if args.preamp_gain is not nan:
                myinstrument.set_preamp_gain_bandwidth(args.preamp_gain,
                                                       tes_channel=tes_channel,
                                                       detector_channel=detector_channel)
                
            # read from board
            readback = myinstrument.get_preamp_total_gain(tes_channel=tes_channel,
                                                          detector_channel=detector_channel)
                
            print('Total preamp gain (fix*variable gains) for channel ' + channel + ' = ' + str(readback))
                    
    
        # -----------
        # Output Gain
        # -----------
        if args.output_gain is not None:

            #  write to board
            if args.output_gain is not nan:
                myinstrument.set_output_gain(args.output_gain,
                                             tes_channel=tes_channel,
                                             detector_channel=detector_channel)
                
            # read from board
            readback = myinstrument.get_output_total_gain(tes_channel=tes_channel,
                                                          detector_channel=detector_channel)
                
            print('Total output gain (fix*variable gains) for channel ' + channel + ' = ' + str(readback))
                    


    # -----------
    # Read all 
    # -----------
    '''
    if args.read_all:
        settings = myinstrument.set_output_gain(tes_channel=tes_channel,
                                                detector_channel=detector_channel)
                
            # read from board
            readback = myinstrument.get_output_total_gain(tes_channel=tes_channel,
                                                          detector_channel=detector_channel)
                
            print('Total output gain (fix*variable gains) for channel ' + channel + ' = ' + str(readback))
    '''              

        
            
    # --------------
    # Sig gen
    # --------------
    #myinstrument.set_signal_gen_params(tes_channel=2, source='feedback', shape='triangle', frequency=110, amplitude=150)
    #data = myinstrument.get_signal_gen_params(tes_channel=2)
    #myinstrument.set_signal_gen_onoff('off',tes_channel=2)

    #data = myinstrument.get_signal_gen_onoff(tes_channel=2)
    #print(data)
    #print(bias)


    
