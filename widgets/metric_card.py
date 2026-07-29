from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class MetricCard(QFrame):
    """可复用统计卡片，避免通过 parentWidget() 反查父对象导致 Qt 生命周期问题。"""

    def __init__(
        self,
        title: str,
        value: str = '--',
        detail: str = '',
        accent: str = '#62C2F4',
    ) -> None:
        super().__init__()
        self.setObjectName('MetricCard')

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(6)

        self.title_label = QLabel(title)
        self.title_label.setObjectName('MetricCardTitle')
        self.title_label.setAlignment(Qt.AlignLeft)

        self.value_label = QLabel(value)
        self.value_label.setObjectName('MetricCardValue')
        self.value_label.setStyleSheet(
            f'color: {accent}; font-size: 28px; font-weight: 800;'
        )
        self.value_label.setAlignment(Qt.AlignLeft)

        self.detail_label = QLabel(detail)
        self.detail_label.setObjectName('MetricCardDetail')
        self.detail_label.setWordWrap(True)

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.detail_label)

    def set_value(self, value: str | int | float) -> None:
        self.value_label.setText(str(value))

    def set_detail(self, detail: str) -> None:
        self.detail_label.setText(detail)
