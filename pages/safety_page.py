import math

from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout, QWidget

from utils.data_store import DataStore
from widgets.metric_card import MetricCard


class SafetyPage(QWidget):
    def __init__(self, store: DataStore | None = None) -> None:
        super().__init__()
        self.store = store
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(34, 28, 34, 22)
        root.setSpacing(14)
        title = QLabel("安全库存 / 再订货点")
        title.setObjectName("pageTitle")
        desc = QLabel("根据需求波动、提前期与服务水平估算安全库存和 ROP。")
        desc.setObjectName("pageDescription")
        root.addWidget(title)
        root.addWidget(desc)

        body = QHBoxLayout()
        body.setSpacing(14)
        form_panel = QFrame()
        form_panel.setObjectName("contentPanel")
        form_layout = QVBoxLayout(form_panel)
        form_layout.setContentsMargins(18, 18, 18, 18)
        form_title = QLabel("参数输入")
        form_title.setObjectName("sectionTitle")
        form = QGridLayout()
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(12)
        self.mean = QLineEdit()
        self.std = QLineEdit()
        self.lead = QLineEdit()
        self.z = QLineEdit("1.65")
        fields = [
            ("日均需求量", self.mean, "例如 100"),
            ("日需求标准差", self.std, "例如 20"),
            ("提前期（天）", self.lead, "例如 5"),
            ("Z 值", self.z, "例如 1.65"),
        ]
        for r, (label, editor, placeholder) in enumerate(fields):
            editor.setPlaceholderText(placeholder)
            form.addWidget(QLabel(label), r, 0)
            form.addWidget(editor, r, 1)
        button = QPushButton("计算")
        button.clicked.connect(self.calculate)
        form_layout.addWidget(form_title)
        form_layout.addLayout(form)
        form_layout.addWidget(button)
        form_layout.addStretch()

        result_panel = QFrame()
        result_panel.setObjectName("contentPanel")
        result_layout = QVBoxLayout(result_panel)
        result_layout.setContentsMargins(18, 18, 18, 18)
        result_title = QLabel("分析结果")
        result_title.setObjectName("sectionTitle")
        result_layout.addWidget(result_title)
        row = QHBoxLayout()
        self.safety_card = MetricCard("安全库存", "--", "#28C7FA", "用于吸收需求波动")
        self.rop_card = MetricCard("再订货点 ROP", "--", "#A970FF", "触发补货的库存水平")
        row.addWidget(self.safety_card)
        row.addWidget(self.rop_card)
        result_layout.addLayout(row)
        result_layout.addStretch()
        body.addWidget(form_panel, 1)
        body.addWidget(result_panel, 2)
        root.addLayout(body, 1)

    def calculate(self) -> None:
        try:
            mean = float(self.mean.text())
            std = float(self.std.text())
            lead = float(self.lead.text())
            z = float(self.z.text())
            if min(mean, std, lead, z) < 0:
                raise ValueError("输入值不能为负数。")
            safety = z * std * math.sqrt(lead)
            rop = mean * lead + safety
            self.safety_card.set_value(f"{safety:.2f}")
            self.rop_card.set_value(f"{rop:.2f}")
            self.last_result = {
                "安全库存": round(safety, 2),
                "再订货点 ROP": round(rop, 2),
                "Z 值": z,
            }
            if self.store is not None:
                self.store.set_analysis("safety", self.last_result)
        except Exception as exc:
            QMessageBox.warning(self, "计算失败", str(exc))
