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
                              '[default: pytesdaq/config/setup.ini]'))
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
    parser.add_argument('--dry-run', '--dry_run', dest='dry_run',
                        action='store_true',
                        help=('Print sweep plan (frequencies, amplitudes, '
                              'timing) without any hardware interaction'))
    parser.add_argument('--quiet', action='store_true',
                        help='Remove screen output')
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
        setup_file = this_dir + '/../pytesdaq/config/setup.ini'

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
        print(f'   - Sweep config: {sequencer_file}\n')

    measurement = TransducerSweep(
        detector_channels=detector_channels,
        sequencer_file=sequencer_file,
        setup_file=setup_file,
        comment=comment,
        data_purpose=data_purpose,
        dry_run=dry_run,
        verbose=verbose
    )

    measurement.run()
