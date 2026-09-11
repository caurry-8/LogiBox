import sys
from pathlib import Path

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QMessageBox

from core.config import APP_CONFIG
from core.logging_config import configure_logging
from ui.main_window import MainWindow


BASE_DIR = Path(__file__).resolve().parent
LOGGER = configure_logging(BASE_DIR)

# 中文字体优先，避免缺字时显示成方框；后面两个是不同 Windows 版本的回退项。
UI_FONT_FAMILIES = ("Microsoft YaHei UI", "Microsoft YaHei", "SimHei", "Segoe UI")


def _handle_exception(exc_type, exc_value, exc_traceback) -> None:
    LOGGER.exception(
        "Unhandled exception",
        exc_info=(exc_type, exc_value, exc_traceback),
    )
    QMessageBox.critical(
        None,
        "LogiBox 运行错误",
        f"程序遇到未处理的错误：\n{exc_value}\n\n详细日志已写入 logs/logibox.log。",
    )


def main() -> int:
    sys.excepthook = _handle_exception

    app = QApplication(sys.argv)
    app.setApplicationName(APP_CONFIG.name)
    app.setApplicationDisplayName(APP_CONFIG.display_name)
    app.setOrganizationName(APP_CONFIG.organization)
    app.setStyle("Fusion")

    font = QFont()
    font.setFamilies(list(UI_FONT_FAMILIES))
    font.setPointSize(10)
    app.setFont(font)

    LOGGER.info("Starting LogiBox %s", APP_CONFIG.version)
    window = MainWindow(base_dir=BASE_DIR)
    window.show()
    exit_code = app.exec()
    LOGGER.info("LogiBox exited with code %s", exit_code)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
