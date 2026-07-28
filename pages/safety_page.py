import math
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QVBoxLayout, QWidget
)

class SafetyPage(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(36, 30, 36, 30)
        root.setSpacing(20)

        title = QLabel("安全库存 / 再订货点")
        title.setObjectName("pageTitle")
        desc = QLabel("输入需求波动、提前期和服务水平参数。")
        desc.setObjectName("pageDescription")
        root.addWidget(title)
        root.addWidget(desc)

        body = QHBoxLayout()
        body.setSpacing(20)

        form_card = QFrame()
        form_card.setObjectName("panelCard")
        form = QGridLayout(form_card)
        form.setContentsMargins(24, 24, 24, 24)

        self.mean = QLineEdit()
        self.std = QLineEdit()
        self.lead = QLineEdit()
        self.z = QLineEdit("1.65")

        self.mean.setPlaceholderText("日均需求量")
        self.std.setPlaceholderText("日需求标准差")
        self.lead.setPlaceholderText("提前期（天）")
        self.z.setPlaceholderText("Z 值")

        for r, (label, editor) in enumerate([
            ("日均需求量", self.mean),
            ("日需求标准差", self.std),
            ("提前期（天）", self.lead),
            ("Z 值", self.z),
        ]):
            form.addWidget(QLabel(label), r, 0)
            form.addWidget(editor, r, 1)

        button = QPushButton("计算")
        button.clicked.connect(self.calculate)
        form.addWidget(button, 4, 0, 1, 2)

        result_card = QFrame()
        result_card.setObjectName("panelCard")
        result = QVBoxLayout(result_card)
        result.setContentsMargins(24, 24, 24, 24)

        self.safety_result = QLabel("安全库存：--")
        self.rop_result = QLabel("再订货点：--")
        self.safety_result.setObjectName("bigMetric")
        self.rop_result.setObjectName("bigMetric")

        result.addWidget(QLabel("计算结果"))
        result.addSpacing(10)
        result.addWidget(self.safety_result)
        result.addWidget(self.rop_result)
        result.addStretch()

        body.addWidget(form_card, 1)
        body.addWidget(result_card, 1)
        root.addLayout(body)
        root.addStretch()

    def calculate(self):
        try:
            mean = float(self.mean.text())
            std = float(self.std.text())
            lead = float(self.lead.text())
            z = float(self.z.text())
            if min(mean, std, lead, z) < 0:
                raise ValueError("输入值不能为负数。")
            safety = z * std * math.sqrt(lead)
            rop = mean * lead + safety
            self.safety_result.setText(f"安全库存：{safety:.2f}")
            self.rop_result.setText(f"再订货点：{rop:.2f}")
        except Exception as exc:
            QMessageBox.warning(self, "计算失败", str(exc))
