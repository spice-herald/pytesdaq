import argparse
from pytesdaq.sequencer import TransducerSweep
from pytesdaq.utils import arg_utils
import os

if __name__ == "__main__":


    # ========================
    # Input arguments
    # ========================

    parser = argparse.ArgumentParser(
        description='Transducer frequency/amplitude sweep'
    )
    parser.add_argument('-c', '--channels', '--detector_channels',
                        dest='detector_channels',
                        nargs='+', type=str,
                        help=('Comma and/or space separated detector '
                              'channel names'))
    parser.add_argument('--setup_file', type=str,
                        help=('Setup configuration file name (full path) '
                              '[default: pytesdaq/config/setup_accel.ini]'))
    parser.add_argument('--config_file', type=str,
                        help=('Transducer sweep configuration file name '
                              '(full path) '
                              '[default: pytesdaq/config/transducer_sweep.ini]'))
    parser.add_argument('--comment', dest='comment',
                        type=str,
                        help='Comment (use quotes "") [default: "No comment"]')
    parser.add_argument('--data_purpose', '--run_purpose',
                        dest='data_purpose',
                        help='Data purpose [string or int], default="test"')
    parser.add_argument('--filename_override', type=str,
                        help=('Override the run directory name. Data will be '
                              'saved to <data_path>/<filename_override>/... '
                              'instead of <data_path>/run<fridge_run>/...'))
    parser.add_argument('--dry-run', '--dry_run', dest='dry_run',
                        action='store_true',
                        help=('Print sweep plan (frequencies, amplitudes, '
                              'timing) without any hardware interaction'))
    parser.add_argument('--quiet', action='store_true',
                        help='Remove screen output')
    parser.add_argument('--enable-iv', dest='enable_iv', action='store_true',
                        help='Take an IV sweep at every transducer step')
    parser.add_argument('--enable-didv', dest='enable_didv', action='store_true',
                        help='Take a dIdV sweep at every transducer step')
    parser.add_argument('--iv_didv_channels', nargs='+', type=str,
                        help=('IV/dIdV sweep channels (detector or TES names '
                              'from the TES setup file) '
                              '[default: "iv_didv_channels" in config file]'))
    parser.add_argument('--tes_setup_file', type=str,
                        help=('Setup file for TES readout and dIdV signal '
                              'generator (full path) '
                              '[default: pytesdaq/config/setup.ini]'))
    parser.add_argument('--iv_config_file', type=str,
                        help=('iv_didv-style config file for the IV sweeps '
                              '[default: pytesdaq/config/iv_didv.ini]'))
    parser.add_argument('--didv_config_file', type=str,
                        help=('iv_didv-style config file for the dIdV sweeps '
                              '[default: pytesdaq/config/iv_didv.ini]'))
    parser.add_argument('--disable-online-iv', dest='disable_online_iv',
                        action='store_true')
    parser.add_argument('--relock', dest='relock', action='store_true',
                        help='Relock at every IV/dIdV bias point')
    parser.add_argument('--zero_once', '--zero', '--zero_offset',
                        dest='zero_offset', action='store_true',
                        help='Zero offsets at the start of each IV/dIdV sweep')
    args = parser.parse_args()


    # ========================
    # Parse arguments
    # ========================

    # dry run
    dry_run = False
    if args.dry_run:
        dry_run = True

    # verbose
    verbose = True
    if args.quiet:
        verbose = False

    # comment
    comment = 'No comment'
    if args.comment:
        comment = args.comment

    # data purpose
    data_purpose = 'test'
    if args.data_purpose:
        data_purpose = args.data_purpose

    # filename override
    filename_override = None
    if args.filename_override:
        filename_override = args.filename_override

    # channels
    detector_channels = None
    if args.detector_channels:
        detector_channels = arg_utils.extract_list(args.detector_channels)

    # setup file
    setup_file = None
    if args.setup_file:
        setup_file = args.setup_file
    else:
        this_dir = os.path.dirname(os.path.realpath(__file__))
        setup_file = this_dir + '/../pytesdaq/config/setup_accel.ini'

    if not os.path.isfile(setup_file):
        print('ERROR: Setup file "' + setup_file + '" not found!')
        exit()

    # config file
    sequencer_file = None
    if args.config_file:
        sequencer_file = args.config_file
    else:
        this_dir = os.path.dirname(os.path.realpath(__file__))
        sequencer_file = (this_dir
                          + '/../pytesdaq/config/transducer_sweep.ini')

    if not os.path.isfile(sequencer_file):
        print('ERROR: Config file "' + sequencer_file + '" not found!')
        exit()


    # IV/dIdV
    enable_iv = False
    if args.enable_iv:
        enable_iv = True

    enable_didv = False
    if args.enable_didv:
        enable_didv = True

    enable_iv_didv = (enable_iv or enable_didv)

    online_iv = True
    if args.disable_online_iv:
        online_iv = False

    do_relock = False
    if args.relock:
        do_relock = True

    do_zero = False
    if args.zero_offset:
        do_zero = True

    iv_didv_channels = None
    if args.iv_didv_channels:
        iv_didv_channels = arg_utils.extract_list(args.iv_didv_channels)

    this_dir = os.path.dirname(os.path.realpath(__file__))

    tes_setup_file = None
    iv_sequencer_file = None
    didv_sequencer_file = None
    if enable_iv_didv:

        if args.tes_setup_file:
            tes_setup_file = args.tes_setup_file
        else:
            tes_setup_file = this_dir + '/../pytesdaq/config/setup.ini'

        if args.iv_config_file:
            iv_sequencer_file = args.iv_config_file
        else:
            iv_sequencer_file = this_dir + '/../pytesdaq/config/iv_didv.ini'

        if args.didv_config_file:
            didv_sequencer_file = args.didv_config_file
        else:
            didv_sequencer_file = this_dir + '/../pytesdaq/config/iv_didv.ini'

        for file_name in [tes_setup_file, iv_sequencer_file, didv_sequencer_file]:
            if not os.path.isfile(file_name):
                print('ERROR: File "' + file_name + '" not found!')
                exit()


    # ========================
    # Start sequencer
    # ========================

    if verbose:
        print('======================================')
        print('Transducer Sweep')
        print('======================================\n')
        print('The following configuration files '
              'will be used: ')
        print(f'   - Instruments setup: {setup_file}')
        print(f'   - Sweep config: {sequencer_file}')
        if enable_iv_didv:
            print(f'   - TES setup: {tes_setup_file}')
        if enable_iv:
            print(f'   - IV config: {iv_sequencer_file}')
        if enable_didv:
            print(f'   - dIdV config: {didv_sequencer_file}')
        print('')

    measurement = TransducerSweep(
        detector_channels=detector_channels,
        sequencer_file=sequencer_file,
        setup_file=setup_file,
        comment=comment,
        data_purpose=data_purpose,
        filename_override=filename_override,
        enable_iv=enable_iv,
        enable_didv=enable_didv,
        iv_didv_channels=iv_didv_channels,
        tes_setup_file=tes_setup_file,
        iv_sequencer_file=iv_sequencer_file,
        didv_sequencer_file=didv_sequencer_file,
        online_iv=online_iv,
        do_relock=do_relock,
        do_zero=do_zero,
        dry_run=dry_run,
        verbose=verbose
    )

    measurement.run()
