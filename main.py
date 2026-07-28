import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    style = Path(__file__).parent / "styles" / "dark.qss"
    app.setStyleSheet(style.read_text(encoding="utf-8"))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
