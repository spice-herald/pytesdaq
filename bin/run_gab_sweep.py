import argparse
import os

from pytesdaq.sequencer import GabSweep

if __name__ == "__main__":

    # ========================
    # Input arguments
    # ========================

    parser = argparse.ArgumentParser(
        description=(
            'Gab thermal conductance sweep automation. '
            'Preconditions: PID pre-set manually, thermometer TES '
            'biased in transition. The heater TES can be left at its '
            'usual operating bias: the script raises it to bias_min '
            '(which must keep the heater TES normal, above its '
            'critical current) and restores the pre-run bias at '
            'shutdown. If the feedback cannot converge, first suspect '
            'that one of the TESs went superconducting or normal '
            'during the sweep.'
        )
    )
    parser.add_argument('--setup_file', type=str,
                        help=('Setup configuration file name (full path) '
                              '[default: pytesdaq/config/setup.ini]'))
    parser.add_argument('--sequencer_file', type=str,
                        help=('Gab sweep configuration file name '
                              '(full path) '
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

    # sequencer file
    sequencer_file = None
    if args.sequencer_file:
        sequencer_file = args.sequencer_file
    else:
        this_dir = os.path.dirname(os.path.realpath(__file__))
        sequencer_file = this_dir + '/../pytesdaq/config/gab_sweep.ini'

    if not os.path.isfile(sequencer_file):
        print('ERROR: Sequencer file "' + sequencer_file
              + '" not found!')
        exit()

    # ========================
    # Start sequencer
    # ========================

    measurement = GabSweep(
        sequencer_file=sequencer_file,
        setup_file=setup_file,
        comment=comment,
        dry_run=dry_run,
        dummy_mode=dummy_mode
    )

    measurement.run()
