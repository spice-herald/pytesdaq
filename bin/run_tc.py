import argparse
from pytesdaq.sequencer import Tc
import numpy as np
import os

if __name__ == "__main__":


    # ========================
    # Input arguments
    # ========================

    parser = argparse.ArgumentParser(description='Tc automation')
    parser.add_argument('--tc_channels', type = str,
                        help='Comma sepated Tc sample channels (Channels with no SQUID readout)')
    parser.add_argument('--detector_channels', type = str,
                        help='Comma sepated detector channels (check connections in setup.ini are up to date)')
    parser.add_argument('--setup_file', type = str,
                        help = 'Setup configuration file name (full path) [default: pytesdaq/config/setup.ini]')
    parser.add_argument('--sequencer_file', type = str,
                        help = 'Tc configuration file name (full path) [default: pytesdaq/config/tc.ini]')
    parser.add_argument('--pickle_file', type = str,help='Pickle file with channel dependent sweep arrays')
    parser.add_argument('--dummy_mode',dest='dummy_mode',action='store_true')
    args = parser.parse_args()



    # dummy mode (for testing, no instrument io)
    dummy_mode = False
    if args.dummy_mode:
        dummy_mode = True
    
    
    # channels
    tc_channels = None
    if args.tc_channels:
        tc_channels = [chan.strip() for chan in args.tc_channels.split(',')]


    detector_channels = None
    if args.detector_channels:
        detector_channels = [chan.strip() for chan in args.detector_channels.split(',')]

        
    # setup file:
    setup_file = None
    if args.setup_file:
        setup_file = args.setup_file
    else:
        this_dir = os.path.dirname(os.path.realpath(__file__))
        setup_file = this_dir + '/../pytesdaq/config/setup.ini'

    if not os.path.isfile(setup_file):
        print('ERROR: Setup file "' + setup_file + '" not found!')
        exit()

        
    # sequencer file:
    sequencer_file = None
    if args.sequencer_file:
        sequencer_file = args.sequencer_file
    else:
        this_dir = os.path.dirname(os.path.realpath(__file__))
        sequencer_file = this_dir + '/../pytesdaq/config/tc.ini'

    if not os.path.isfile(sequencer_file):
        print('ERROR: Sequencer file "' + sequencer_file + '" not found!')
        exit()

        
   
    # ========================
    # Start sequencer
    # ========================
    
   
    measurement = Tc(tc_channels=tc_channels,
                     detector_channels=detector_channels,
                     sequencer_file=sequencer_file,
                     setup_file=setup_file,
                     dummy_mode=dummy_mode)

    
    measurement.run()
