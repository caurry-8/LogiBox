from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMainWindow, QStackedWidget, QStatusBar, QVBoxLayout, QWidget
)
from pages.home_page import HomePage
from pages.import_page import ImportPage
from pages.eoq_page import EOQPage
from pages.abc_page import ABCPage
from pages.safety_page import SafetyPage

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LogiBox 物流工程效率工具箱")
        self.resize(1500, 900)
        self.setMinimumSize(1100, 700)
        self._build_ui()

    def _build_ui(self):
        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        sidebar = self._build_sidebar()
        root_layout.addWidget(sidebar)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.addWidget(self._build_topbar())

        self.stack = QStackedWidget()
        self.stack.addWidget(HomePage(self.navigate_to))
        self.stack.addWidget(ImportPage())
        self.stack.addWidget(EOQPage())
        self.stack.addWidget(ABCPage())
        self.stack.addWidget(SafetyPage())
        self.stack.addWidget(self._placeholder("运输分析", "运输成本与车辆利用率分析模块"))
        self.stack.addWidget(self._placeholder("报告中心", "Excel / Word / PDF 报告导出模块"))
        self.stack.addWidget(self._placeholder("系统设置", "软件设置与数据目录管理模块"))

        content_layout.addWidget(self.stack, 1)
        root_layout.addWidget(content, 1)
        self.setCentralWidget(root)

        status = QStatusBar()
        status.showMessage("就绪 · LogiBox V1.0")
        self.setStatusBar(status)

        self.menu.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.menu.setCurrentRow(0)

    def _build_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(250)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(18, 20, 18, 20)
        layout.setSpacing(12)

        logo = QLabel("LogiBox")
        logo.setObjectName("logoTitle")
        subtitle = QLabel("物流工程效率工具箱")
        subtitle.setObjectName("logoSubtitle")
        layout.addWidget(logo)
        layout.addWidget(subtitle)
        layout.addSpacing(18)

        self.menu = QListWidget()
        self.menu.setObjectName("sidebarMenu")
        for text in [
            "工作台", "数据中心", "EOQ 经济订货批量", "ABC 库存分类",
            "安全库存 / ROP", "运输分析", "报告中心", "系统设置"
        ]:
            self.menu.addItem(QListWidgetItem(text))
        layout.addWidget(self.menu, 1)

        version = QLabel("Version 1.0.0")
        version.setObjectName("versionLabel")
        version.setAlignment(Qt.AlignCenter)
        layout.addWidget(version)
        return sidebar

    def _build_topbar(self):
        topbar = QFrame()
        topbar.setObjectName("topbar")
        topbar.setFixedHeight(64)
        layout = QHBoxLayout(topbar)
        layout.setContentsMargins(24, 0, 24, 0)

        title = QLabel("物流工程效率工具箱")
        title.setObjectName("topbarTitle")
        hint = QLabel("数据分析 · 库存管理 · 物流计算")
        hint.setObjectName("topbarHint")

        layout.addWidget(title)
        layout.addSpacing(16)
        layout.addWidget(hint)
        layout.addStretch()
        return topbar

    def _placeholder(self, title, description):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(50, 50, 50, 50)
        label = QLabel(title)
        label.setObjectName("pageTitle")
        desc = QLabel(description)
        desc.setObjectName("pageDescription")
        layout.addWidget(label)
        layout.addWidget(desc)
        layout.addStretch()
        return page

    def navigate_to(self, index):
        if 0 <= index < self.stack.count():
            self.menu.setCurrentRow(index)
