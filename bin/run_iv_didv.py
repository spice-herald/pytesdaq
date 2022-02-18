import argparse
import numpy as np
import os
from pytesdaq.utils import arg_utils
from pytesdaq.sequencer.iv_didv import IV_dIdV

if __name__ == "__main__":


    # ========================
    # Input arguments
    # ========================

    parser = argparse.ArgumentParser(description='Launch Sequencer')
    parser.add_argument('-c','--channels','--sweep_channels', '--detector_channels', dest='channels',
                        nargs='+', type=str,
                        help='Sweep channels: comma and/or space separated "detector" or "TES readout" channels')
    parser.add_argument('--enable-iv',dest='enable_iv',action='store_true')
    parser.add_argument('--enable-didv',dest='enable_didv',action='store_true')
    parser.add_argument('--enable-rp',dest='enable_rp',action='store_true')
    parser.add_argument('--enable-rn',dest='enable_rn',action='store_true')
    parser.add_argument('--comment', dest='comment',
                        type = str, help = 'Comment (use quotes "")  [default: "No comment"]')
    parser.add_argument('--relock', dest='relock',action='store_true')
    parser.add_argument('--zero_once','--zero', '--zero_offset', dest='zero_offset', action='store_true')
    parser.add_argument('--snap', '--zap_tes', dest='zap_tes', action='store_true')
    parser.add_argument('--enable-temperature-sweep', dest='enable_temperature_sweep', action='store_true')
    parser.add_argument('--disable-bias-sweep', dest='disable_bias_sweep', action='store_true')
    parser.add_argument('--saved_channels',  dest='saved_channels', nargs='+', type=str,
                        help=('Comma and/or space separated detector or TES readout channels '
                              'saved in raw data\n(sweep channels automatically saved)'))
    parser.add_argument('--setup_file', type = str,
                        help = 'Setup configuration file name (full path) [default: pytesdaq/config/setup.ini]')
    parser.add_argument('--sequencer_file', type = str,
                        help = 'Sequencer configuration file name (full path) [default: pytesdaq/config/sequencer.ini]')
    parser.add_argument('--pickle_file', type = str,help='Pickle file with channel dependent sweep arrays')
    parser.add_argument('--dummy_mode', dest='dummy_mode', action='store_true')
   
    args = parser.parse_args()


    comment = 'No comment'
    if args.comment:
        comment = args.comment

    
    dummy_mode = False
    if args.dummy_mode:
        dummy_mode = True

    
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

    enable_temperature_sweep = False
    if args.enable_temperature_sweep:
        enable_temperature_sweep = True

    enable_bias_sweep = True
    if args.disable_bias_sweep:
        enable_bias_sweep = False
    

    enable_iv_didv = (enable_iv or enable_rp or enable_rn or enable_didv)


    do_relock = False
    if args.relock:
        do_relock = True
    do_zero = False
    if args.zero_offset:
        do_zero = True

    do_zap = False
    if args.zap_tes:
        do_zap = True
    
    # channels
    channels = None
    if args.channels:
        channels = arg_utils.extract_list(args.channels)
    else:
        print('Sweep channels required!')
        exit(1)

    # saved channels
    saved_channels = None
    if args.saved_channels:
        saved_channels = arg_utils.extract_list(args.saved_channels)
    
    
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
        sequencer_file = this_dir + '/../pytesdaq/config/iv_didv.ini'

    if not os.path.isfile(sequencer_file):
        print('ERROR: Sequencer file "' + sequencer_file + '" not found!')
        exit()

        
    pickle_file = str()
    if args.pickle_file:
        pickle_file = args.pickle_file
    

    # check arguments
    if not enable_iv_didv:
        print('Not measurement has been enabled! Type "python run_sequencer.py --help"')
        exit(0)

        
   
    # ========================
    # Start sequencer
    # ========================
    if enable_iv_didv:
        sequencer = IV_dIdV(dummy_mode=dummy_mode,
                            iv=enable_iv, didv=enable_didv,
                            rp=enable_rp, rn=enable_rn,
                            temperature_sweep=enable_temperature_sweep,
                            tes_bias_sweep=enable_bias_sweep,
                            comment=comment,
                            do_relock=do_relock,
                            do_zero=do_zero,
                            do_zap=do_zap,
                            sweep_channels=channels,
                            saved_channels=saved_channels,
                            sequencer_file=sequencer_file, setup_file=setup_file,
                            sequencer_pickle_file=pickle_file)
        sequencer.run()

