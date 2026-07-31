from pathlib import Path

from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QStackedWidget, QWidget

from pages.about_page import AboutPage
from pages.abc_page import ABCPage
from pages.dashboard import DashboardPage
from pages.eoq_page import EOQPage
from pages.import_page import ImportPage
from pages.report_page import ReportPage
from pages.safety_page import SafetyPage
from pages.xyz_page import XYZPage
from ui.navigation import Navigation
from utils.data_store import DataStore


class MainWindow(QMainWindow):
    def __init__(self, base_dir: Path | None = None):
        super().__init__()
        self.base_dir = base_dir or Path(__file__).resolve().parents[1]
        self.store = DataStore()
        self.pages = []
        self._init_window()
        self._init_ui()
        self._load_style()

    def _init_window(self) -> None:
        self.resize(1500, 900)
        self.setMinimumSize(1180, 720)
        self.setWindowTitle("LogiBox · Logistics Analytics Platform")
        self.statusBar().showMessage("LogiBox V3.2 已就绪")

    def _init_ui(self) -> None:
        root = QWidget()
        root.setObjectName("mainRoot")
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.nav = Navigation()
        self.stack = QStackedWidget()
        self.stack.setObjectName("pageStack")

        self.abc_page = ABCPage(self.store)
        self.xyz_page = XYZPage(self.store)
        self.eoq_page = EOQPage(self.store)
        self.safety_page = SafetyPage(self.store)

        self.pages = [
            DashboardPage(self.store, self.navigate_to),
            ImportPage(self.store),
            self.eoq_page,
            self.abc_page,
            self.xyz_page,
            self.safety_page,
            ReportPage(self.store),
            AboutPage(),
        ]

        for page in self.pages:
            self.stack.addWidget(page)

        self.nav.page_changed.connect(self.switch_page)
        layout.addWidget(self.nav)
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(root)
        self.stack.setCurrentIndex(0)

    def switch_page(self, index: int) -> None:
        if 0 <= index < self.stack.count():
            self.stack.setCurrentIndex(index)
            self.nav.set_active(index)
            self.statusBar().showMessage(f"当前模块：{self._page_title(index)}")

    def navigate_to(self, index: int) -> None:
        self.switch_page(index)

    @staticmethod
    def _page_title(index: int) -> str:
        titles = [
            "工作台",
            "数据中心",
            "EOQ 经济订货",
            "ABC 分类",
            "XYZ 分析",
            "安全库存",
            "报告中心",
            "关于 LogiBox",
        ]
        return titles[index] if 0 <= index < len(titles) else "工作台"

    def _load_style(self) -> None:
        style_path = self.base_dir / "styles" / "dark_v3.qss"
        try:
            self.setStyleSheet(style_path.read_text(encoding="utf-8"))
        except OSError as exc:
            self.statusBar().showMessage(f"主题加载失败：{exc}")
