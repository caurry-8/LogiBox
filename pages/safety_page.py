import math
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout, QWidget


class SafetyPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(36, 30, 36, 30)
        root.setSpacing(18)

        title = QLabel('安全库存 / 再订货点')
        title.setObjectName('pageTitle')
        desc = QLabel('基于需求波动、提前期和服务水平计算安全库存与 ROP。')
        desc.setObjectName('pageDescription')
        root.addWidget(title)
        root.addWidget(desc)

        body = QHBoxLayout()
        body.setSpacing(18)
        input_card = QFrame()
        input_card.setObjectName('panelCard')
        form = QGridLayout(input_card)
        form.setContentsMargins(24, 24, 24, 24)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(14)

        self.mean = QLineEdit()
        self.std = QLineEdit()
        self.lead = QLineEdit()
        self.z = QLineEdit('1.65')
        self.mean.setPlaceholderText('日均需求量')
        self.std.setPlaceholderText('日需求标准差')
        self.lead.setPlaceholderText('提前期（天）')
        self.z.setPlaceholderText('Z 值')

        rows = [
            ('日均需求量', self.mean),
            ('日需求标准差', self.std),
            ('提前期（天）', self.lead),
            ('Z 值', self.z),
        ]
        for row, (label, editor) in enumerate(rows):
            form.addWidget(QLabel(label), row, 0)
            form.addWidget(editor, row, 1)

        button = QPushButton('计算')
        button.clicked.connect(self.calculate)
        form.addWidget(button, 4, 0, 1, 2)

        result_card = QFrame()
        result_card.setObjectName('panelCard')
        result = QVBoxLayout(result_card)
        result.setContentsMargins(24, 24, 24, 24)
        result.addWidget(QLabel('计算结果'))

        self.safety_result = QLabel('安全库存：--')
        self.rop_result = QLabel('再订货点：--')
        self.safety_result.setObjectName('bigMetric')
        self.rop_result.setObjectName('bigMetric')

        result.addWidget(self.safety_result)
        result.addWidget(self.rop_result)
        result.addStretch()

        body.addWidget(input_card, 1)
        body.addWidget(result_card, 1)
        root.addLayout(body, 1)

    def calculate(self) -> None:
        try:
            mean = float(self.mean.text())
            std = float(self.std.text())
            lead = float(self.lead.text())
            z = float(self.z.text())
            if min(mean, std, lead, z) < 0:
                raise ValueError('输入值不能为负数。')
            safety_stock = z * std * math.sqrt(lead)
            rop = mean * lead + safety_stock
            self.safety_result.setText(f'安全库存：{safety_stock:.2f}')
            self.rop_result.setText(f'再订货点：{rop:.2f}')
        except Exception as exc:
            QMessageBox.warning(self, '计算失败', str(exc))
