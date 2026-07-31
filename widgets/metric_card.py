from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class MetricCard(QFrame):
    """Reusable metric card; keeps the V2.x four-argument API compatible."""

    def __init__(
        self,
        title: str,
        value: str = "--",
        accent: str = "#28C7FA",
        hint: str = "",
    ) -> None:
        super().__init__()
        self.setObjectName("metricCard")
        self.accent = accent

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("metricTitle")

        self.value_label = QLabel(value)
        self.value_label.setObjectName("metricValue")
        self.value_label.setStyleSheet(f"color: {accent};")

        self.hint_label = QLabel(hint)
        self.hint_label.setObjectName("metricHint")
        self.hint_label.setWordWrap(True)

        self.title_label.setAlignment(Qt.AlignLeft)
        self.value_label.setAlignment(Qt.AlignLeft)

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.hint_label)

    def set_value(self, value: str) -> None:
        self.value_label.setText(str(value))

    def set_hint(self, text: str) -> None:
        self.hint_label.setText(text)

    def set_title(self, text: str) -> None:
        self.title_label.setText(text)

    def set_accent(self, color: str) -> None:
        self.accent = color
        self.value_label.setStyleSheet(f"color: {color};")
