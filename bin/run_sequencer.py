import argparse
from pytesdaq.sequencer.iv_didv import IV_dIdV
import numpy as np


if __name__ == "__main__":


    # ========================
    # Input arguments
    # ========================

    parser = argparse.ArgumentParser(description='Launch Sequencer')
    parser.add_argument('--enable-iv',dest='enable_iv',action='store_true')
    parser.add_argument('--enable-didv',dest='enable_didv',action='store_true')
    parser.add_argument('--enable-rp',dest='enable_rp',action='store_true')
    parser.add_argument('--enable-rn',dest='enable_rn',action='store_true')
    parser.add_argument('--enable-tc',dest='enable_tc',action='store_true')
    parser.add_argument('--enable-temperature-sweep',dest='enable_temperature_sweep',action='store_true')
    
    parser.add_argument('--tes_channels', type = str,
                        help='Comma sepated TES channels (check connections in setup.ini are uptodate)')
    parser.add_argument('--detector_channels', type = str,
                        help='Comma sepated detector channels (check connections in setup.ini are uptodate)')
    parser.add_argument('--setup_file', type = str,
                        help = 'Setup configuration file name (full path) [default: pytesdaq/config/setup.ini]')
    parser.add_argument('--sequencer_file', type = str,
                        help = 'Sequencer configuration file name (full path) [default: pytesdaq/config/sequencer.ini]')
    parser.add_argument('--pickle_file', type = str,help='Pickle file with channel dependent sweep arrays')
    args = parser.parse_args()

  
    enable_iv = False
    if args.enable_iv:
        enable_iv = True
        
    enable_didv = False
    if args.enable_didv:
        enable_didv = True

    enable_rp = False
    if args.enable_rp:
        enable_rp = True
    
    enable_rn = False
    if args.enable_rn:
        enable_rn = True

    enable_tc = False
    if args.enable_tc:
        enable_tc = True

    enable_temperature_sweep = False
    if args.enable_temperature_sweep:
        enable_temperature_sweep = True



    enable_iv_didv = (enable_iv or enable_rp or enable_rn or enable_didv)
    
    # channels
    channels = list()
    if args.tes_channels:
        channels = args.tes_channels
    elif args.detector_channels:
        channels = args.detector_channels
        
    
    channels = [chan.strip() for chan in channels.split(',')]
   

    # setup file
    setup_file = str()
    if args.setup_file:
        setup_file = args.setup_file
    

    sequencer_file = str()
    if args.sequencer_file:
        sequencer_file = args.sequencer_file
        
    pickle_file = str()
    if args.pickle_file:
        pickle_file = args.pickle_file
    


    # check arguments
    if not (enable_iv_didv or enable_tc):
        print('Not measurement has been enabled! Type "python run_sequencer.py --help"')
        exit(0)

    if enable_tc and enable_iv_didv:
        print('Tc measurement cannot be done with Rp,Rn,IV, or dIdV')
        exit(0)

    if not args.tes_channels and not args.detector_channels:
        print('No channels (TES or Detector) have been selected! Type "python run_sequencer.py --help"')
        exit(0)

    if args.tes_channels and args.detector_channels:
        print('please choose between channel type (TES or Detector). Not both')
        exit(0)
        
   
    # ========================
    # Start sequencer
    # ========================
    
    if enable_iv_didv:
        sequencer = IV_dIdV(iv=enable_iv, didv=enable_didv,
                            rp=enable_rp, rn=enable_rn,
                            temperature_sweep=enable_temperature_sweep, 
                            channel_list=channels,
                            sequencer_file=sequencer_file, setup_file=setup_file,
                            pickle_file=pickle_file)

        
        sequencer.verbose = True
        sequencer.dummy_mode = True
        sequencer.run()

