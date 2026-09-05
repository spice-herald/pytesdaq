import argparse
import os

from pytesdaq.sequencer import GabSweep

if __name__ == "__main__":

    # ========================
    # Input arguments
    # ========================

    parser = argparse.ArgumentParser(
        description=(
            'Gab thermal conductance sweep automation. At each MC '
            'temperature the heater TES bias is walked down a fixed '
            'vector and the thermometer R0 is recorded at every '
            'point, so the operating R0 is chosen offline rather than '
            'at run time. Preconditions: PID pre-set manually, '
            'thermometer TES biased in transition. Both TES biases '
            'are restored at shutdown. Run --dry_run first to check '
            'the bias vector and the estimated duration, and confirm '
            'with a short test sweep that the vector actually reaches '
            'a usable R0 at the coldest temperature: nothing checks '
            'that during the run.'
        )
    )
    parser.add_argument('--setup_file', type=str,
                        help=('Setup configuration file name (full path) '
                              '[default: pytesdaq/config/setup.ini]'))
    parser.add_argument('--config_file', '--sequencer_file', type=str,
                        help=('Gab sweep configuration file name '
                              '(full path). This is the [gab_sweep] '
                              'config, not setup.ini '
                              '[default: pytesdaq/config/gab_sweep.ini]'))
    parser.add_argument('--comment', dest='comment', type=str,
                        help='Comment (use quotes "") '
                             '[default: "No comment"]')
    parser.add_argument('--dry_run', dest='dry_run',
                        action='store_true',
                        help='Print the sweep plan without any '
                             'hardware interaction')
    parser.add_argument('--dummy_mode', dest='dummy_mode',
                        action='store_true',
                        help='Instrument calls become no-ops where '
                             'supported. Does not fake the DAQ or '
                             'thermometry, so a full off-DAQ rehearsal '
                             'is not possible; use --dry_run to check '
                             'the sweep plan')
    args = parser.parse_args()

    comment = 'No comment'
    if args.comment:
        comment = args.comment

    dry_run = False
    if args.dry_run:
        dry_run = True

    dummy_mode = False
    if args.dummy_mode:
        dummy_mode = True

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

    # config file. --sequencer_file is kept as an alias so the older
    # spelling, and anything already scripted around it, keeps working
    config_file = None
    if args.config_file:
        config_file = args.config_file
    else:
        this_dir = os.path.dirname(os.path.realpath(__file__))
        config_file = this_dir + '/../pytesdaq/config/gab_sweep.ini'

    if not os.path.isfile(config_file):
        print('ERROR: Config file "' + config_file + '" not found!')
        exit()

    # ========================
    # Start sequencer
    # ========================

    measurement = GabSweep(
        sequencer_file=config_file,
        setup_file=setup_file,
        comment=comment,
        dry_run=dry_run,
        dummy_mode=dummy_mode
    )

    measurement.run()
