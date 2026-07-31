from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


class Navigation(QWidget):
    """LogiBox V3.2 professional sidebar navigation."""

    page_changed = Signal(int)

    NAV_ITEMS = [
        ("工作台", "Overview", 0),
        ("数据中心", "Data Center", 1),
        ("EOQ 经济订货", "Inventory", 2),
        ("ABC 分类", "Inventory", 3),
        ("XYZ 分析", "Inventory", 4),
        ("安全库存", "Inventory", 5),
        ("报告中心", "Output", 6),
        ("关于 LogiBox", "System", 7),
    ]

    SECTION_NAMES = {
        "Overview": "工作台",
        "Data Center": "数据管理",
        "Inventory": "库存分析",
        "Output": "输出中心",
        "System": "系统",
    }

    def __init__(self):
        super().__init__()
        self.setObjectName("sidebar")
        self.setFixedWidth(248)
        self.buttons: list[QPushButton] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 22, 18, 18)
        layout.setSpacing(5)

        brand = QLabel("LOGIBOX")
        brand.setObjectName("logo")
        layout.addWidget(brand)

        subtitle = QLabel("LOGISTICS ANALYTICS PLATFORM")
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        version = QLabel("V3.2  ·  INTELLIGENT WORKSPACE")
        version.setObjectName("versionLabel")
        layout.addSpacing(14)
        layout.addWidget(version)
        layout.addSpacing(12)

        current_section = None
        for text, section, index in self.NAV_ITEMS:
            if section != current_section:
                section_label = QLabel(self.SECTION_NAMES[section])
                section_label.setObjectName("navSection")
                layout.addWidget(section_label)
                current_section = section

            button = QPushButton(text)
            button.setObjectName("navButton")
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda checked=False, i=index: self.change_page(i))
            layout.addWidget(button)
            self.buttons.append(button)

        layout.addStretch(1)

        line = QLabel("")
        line.setObjectName("sidebarLine")
        line.setFixedHeight(1)
        layout.addWidget(line)

        self.status = QLabel("● SYSTEM ONLINE")
        self.status.setObjectName("status")
        layout.addWidget(self.status)

        self.set_active(0)

    def set_active(self, index: int) -> None:
        for i, button in enumerate(self.buttons):
            button.setChecked(i == index)

    def change_page(self, index: int) -> None:
        self.set_active(index)
        self.page_changed.emit(index)
