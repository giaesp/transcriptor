import multiprocessing
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from app import APP_NAME
from app.ui import MainWindow


def main() -> int:
    multiprocessing.freeze_support()
    if sys.platform == "darwin":
        # Su macOS 27 l'NSAlert nativo (QMessageBox) va in crash rasterizzando l'icona:
        # usiamo le finestre di dialogo disegnate da Qt. Windows resta nativo.
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_DontUseNativeDialogs, True)
    qapp = QApplication(sys.argv)
    qapp.setApplicationName(APP_NAME)
    qapp.setStyle("Fusion")
    win = MainWindow()
    win.show()
    return qapp.exec()


if __name__ == "__main__":
    sys.exit(main())
