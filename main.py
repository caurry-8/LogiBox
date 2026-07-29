import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


def load_theme(app: QApplication) -> None:
    theme_file = Path(__file__).parent / 'styles' / 'dark.qss'
    if theme_file.exists():
        app.setStyleSheet(theme_file.read_text(encoding='utf-8'))


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName('LogiBox')
    app.setApplicationVersion('2.2.0')
    app.setOrganizationName('LogiBox')

    load_theme(app)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
