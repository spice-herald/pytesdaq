from PyQt5 import QtCore, QtGui, QtWidgets
import pytesdaq.scope.scope as scope
import sys
import argparse
import os

if __name__ == "__main__":

    # ========================
    # Input arguments
    # ========================
    parser = argparse.ArgumentParser(description="Pulse Display GUI")
    parser.add_argument('--setup_file', type = str,
                        help = 'Configuration setup file name (full path) [default: pytesdaq/config/setup.ini]')
  
    args = parser.parse_args()


    # setup file 
    setup_file = None
    if args.setup_file:
        setup_file = args.setup_file
    else:
        this_dir = os.path.dirname(os.path.realpath(__file__))
        setup_file = this_dir + '/../pytesdaq/config/setup.ini'


    # ========================
    # Start GUI
    # ========================
    
    app = QtWidgets.QApplication(sys.argv)
    ui = scope.MainWindow(setup_file=setup_file)
    sys.exit(app.exec_())
