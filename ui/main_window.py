from pathlib import Path

from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QStackedWidget, QWidget

from core.config import APP_CONFIG
from core.logging_config import configure_logging
from core.page_registry import PageDefinition
from core.theme import load_stylesheet
from pages.about_page import AboutPage
from pages.abc_page import ABCPage
from pages.dashboard import DashboardPage
from pages.eoq_page import EOQPage
from pages.import_page import ImportPage
from pages.matrix_page import MatrixPage
from pages.report_page import ReportPage
from pages.safety_page import SafetyPage
from pages.xyz_page import XYZPage
from ui.navigation import Navigation
from utils.data_store import DataStore


class MainWindow(QMainWindow):
    def __init__(self, base_dir: Path | None = None) -> None:
        super().__init__()
        self.base_dir = base_dir or Path(__file__).resolve().parents[1]
        self.logger = configure_logging(self.base_dir)
        self.store = DataStore()
        self.page_definitions: list[PageDefinition] = []
        self.pages: list[QWidget] = []

        self._init_window()
        self._init_ui()
        self._load_style()
        self._connect_store_status()

    def _init_window(self) -> None:
        self.resize(APP_CONFIG.default_width, APP_CONFIG.default_height)
        self.setMinimumSize(APP_CONFIG.minimum_width, APP_CONFIG.minimum_height)
        self.setWindowTitle(APP_CONFIG.display_name)
        self.statusBar().showMessage(
            f"LogiBox V{APP_CONFIG.version} {APP_CONFIG.edition} 已就绪"
        )

    def _build_page_definitions(self) -> list[PageDefinition]:
        return [
            PageDefinition(
                "dashboard",
                "工作台",
                "工作台",
                "通用",
                lambda: DashboardPage(self.store, self.navigate_to_key),
            ),
            PageDefinition(
                "data_center",
                "数据中心",
                "数据中心",
                "通用",
                lambda: ImportPage(self.store),
            ),
            PageDefinition(
                "eoq",
                "EOQ 经济订货",
                "EOQ 经济订货",
                "库存分析",
                lambda: EOQPage(self.store),
            ),
            PageDefinition(
                "abc",
                "ABC 分类",
                "ABC 库存分类",
                "库存分析",
                lambda: ABCPage(self.store),
            ),
            PageDefinition(
                "xyz",
                "XYZ 分析",
                "XYZ 稳定性分析",
                "库存分析",
                lambda: XYZPage(self.store),
            ),
            PageDefinition(
                "matrix",
                "ABC × XYZ 矩阵",
                "ABC × XYZ 交叉矩阵",
                "库存分析",
                lambda: MatrixPage(self.store),
            ),
            PageDefinition(
                "safety",
                "安全库存",
                "安全库存 / ROP",
                "库存分析",
                lambda: SafetyPage(self.store),
            ),
            PageDefinition(
                "report",
                "报告中心",
                "报告中心",
                "输出",
                lambda: ReportPage(self.store),
            ),
            PageDefinition(
                "about",
                "关于 LogiBox",
                "关于 LogiBox",
                "系统",
                AboutPage,
            ),
        ]

    def _init_ui(self) -> None:
        root = QWidget()
        root.setObjectName("mainRoot")
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.page_definitions = self._build_page_definitions()
        nav_items = [
            (page.nav_label, page.section, index)
            for index, page in enumerate(self.page_definitions)
        ]
        self.nav = Navigation(nav_items=nav_items)
        self.stack = QStackedWidget()
        self.stack.setObjectName("pageStack")

        for definition in self.page_definitions:
            page = definition.factory()
            self.pages.append(page)
            self.stack.addWidget(page)

        self.nav.page_changed.connect(self.switch_page)
        layout.addWidget(self.nav)
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(root)
        self.switch_page(0)

    def _connect_store_status(self) -> None:
        self.store.status_changed.connect(self.statusBar().showMessage)

    def switch_page(self, index: int) -> None:
        if not 0 <= index < self.stack.count():
            self.logger.warning("Ignored invalid page index: %s", index)
            return

        self.stack.setCurrentIndex(index)
        self.nav.set_active(index)
        title = self.page_definitions[index].title
        self.statusBar().showMessage(f"当前模块：{title}")
        self.logger.info("Switched page to %s", self.page_definitions[index].key)

    def navigate_to(self, index: int) -> None:
        self.switch_page(index)

    def page_index(self, key: str) -> int:
        """Resolve a page key to its stack index; -1 when unknown."""
        for index, definition in enumerate(self.page_definitions):
            if definition.key == key:
                return index
        return -1

    def navigate_to_key(self, key: str) -> None:
        """Navigate by stable page key so menu order can change safely."""
        index = self.page_index(key)
        if index < 0:
            self.logger.warning("Unknown page key requested: %s", key)
            return
        self.switch_page(index)

    def _load_style(self) -> None:
        try:
            self.setStyleSheet(load_stylesheet(self.base_dir))
        except OSError as exc:
            self.logger.exception("Theme load failed")
            self.statusBar().showMessage(f"主题加载失败：{exc}")
