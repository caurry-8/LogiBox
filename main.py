import sys
from pathlib import Path

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


BASE_DIR = Path(__file__).resolve().parent


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("LogiBox")
    app.setApplicationDisplayName("LogiBox · Logistics Analytics Platform")
    app.setOrganizationName("LogiBox")
    app.setStyle("Fusion")

    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)

    window = MainWindow(base_dir=BASE_DIR)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
