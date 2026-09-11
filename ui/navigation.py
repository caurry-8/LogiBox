from collections.abc import Sequence

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout, QWidget

from core.config import APP_CONFIG


class Navigation(QWidget):
    """GitHub-inspired sidebar navigation with configurable page entries."""

    page_changed = Signal(int)

    def __init__(
        self,
        nav_items: Sequence[tuple[str, str, int]] | None = None,
    ) -> None:
        super().__init__()
        self.nav_items = list(nav_items or [])
        self.setObjectName("sidebar")
        self.setFixedWidth(252)
        self.buttons: list[QPushButton] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 18, 16, 16)
        layout.setSpacing(4)

        brand_row = QFrame()
        brand_row.setObjectName("brandBlock")
        brand_layout = QVBoxLayout(brand_row)
        brand_layout.setContentsMargins(12, 10, 12, 10)
        brand_layout.setSpacing(2)

        brand = QLabel("LOGIBOX")
        brand.setObjectName("logo")
        brand_layout.addWidget(brand)

        subtitle = QLabel("物流工程分析平台")
        subtitle.setObjectName("subtitle")
        brand_layout.addWidget(subtitle)

        version = QLabel(
            f"V{APP_CONFIG.version} · {APP_CONFIG.edition}"
        )
        version.setObjectName("versionLabel")
        brand_layout.addWidget(version)
        layout.addWidget(brand_row)
        layout.addSpacing(12)

        current_section: str | None = None
        for text, section, index in self.nav_items:
            if section != current_section:
                section_label = QLabel(section)
                section_label.setObjectName("navSection")
                layout.addSpacing(5)
                layout.addWidget(section_label)
                current_section = section

            button = QPushButton(text)
            button.setObjectName("navButton")
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(
                lambda checked=False, page_index=index: self.change_page(page_index)
            )
            layout.addWidget(button)
            self.buttons.append(button)

        layout.addStretch(1)

        footer = QFrame()
        footer.setObjectName("sidebarFooter")
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(12, 10, 12, 10)
        footer_layout.setSpacing(3)

        self.status = QLabel("系统状态：在线")
        self.status.setObjectName("status")
        footer_layout.addWidget(self.status)

        repository = QLabel("本地工作区")
        repository.setObjectName("sidebarMeta")
        footer_layout.addWidget(repository)
        layout.addWidget(footer)

    def set_active(self, index: int) -> None:
        for button_index, button in enumerate(self.buttons):
            button.setChecked(button_index == index)

    def change_page(self, index: int) -> None:
        self.set_active(index)
        self.page_changed.emit(index)
