import argparse
import os
import sys

from pytesdaq.sequencer import GtaSweep

if __name__ == "__main__":

    # ========================
    # Input arguments
    # ========================

    parser = argparse.ArgumentParser(
        description=(
            'Gta thermal conductance sweep automation. This is the '
            '"clean" Gta measurement: an IV sweep is taken at each '
            'bath temperature and interpolated offline to a common R0, '
            'giving I0 and so P0 at the same TES resistance for every '
            'temperature. Preconditions: PID pre-set manually, and a '
            'configured tes_bias_vect that brackets the target R0 at '
            'every bath temperature in the sweep. Every other TES '
            'channel is set to 0 uA for the duration of the sweep and '
            'restored at shutdown. If the IV curves at the cold end do '
            'not reach the target R0, first suspect that the '
            'configured bias vector no longer brackets the transition '
            'at that temperature.'
        )
    )
    parser.add_argument('--setup_file', type=str,
                        help=('Setup configuration file name (full path) '
                              '[default: pytesdaq/config/setup.ini]'))
    parser.add_argument('--config_file', '--sequencer_file', type=str,
                        help=('Gta sweep configuration file name '
                              '(full path). This is the [gta_sweep] '
                              'config, not setup.ini '
                              '[default: pytesdaq/config/gta_sweep.ini]'))
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
        sys.exit(1)

    # config file. --sequencer_file is kept as an alias so the older
    # spelling, and anything already scripted around it, keeps working
    config_file = None
    if args.config_file:
        config_file = args.config_file
    else:
        this_dir = os.path.dirname(os.path.realpath(__file__))
        config_file = this_dir + '/../pytesdaq/config/gta_sweep.ini'

    if not os.path.isfile(config_file):
        print('ERROR: Config file "' + config_file + '" not found!')
        sys.exit(1)

    # ========================
    # Start sequencer
    # ========================

    measurement = GtaSweep(
        sequencer_file=config_file,
        setup_file=setup_file,
        comment=comment,
        dry_run=dry_run,
        dummy_mode=dummy_mode
    )

    measurement.run()
