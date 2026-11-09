import multiprocessing
import sys

from PySide6.QtWidgets import QApplication

from app import APP_NAME
from app.ui import MainWindow


def main() -> int:
    multiprocessing.freeze_support()
    qapp = QApplication(sys.argv)
    qapp.setApplicationName(APP_NAME)
    qapp.setStyle("Fusion")
    win = MainWindow()
    win.show()
    return qapp.exec()


if __name__ == "__main__":
    sys.exit(main())
