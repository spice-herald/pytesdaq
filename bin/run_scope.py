from PyQt5 import QtCore, QtGui, QtWidgets
import pytesdaq.scope.scope as scope
import sys


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    ui = scope.MainWindow()
    sys.exit(app.exec_())
