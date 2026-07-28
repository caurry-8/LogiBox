from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QVBoxLayout, QWidget
)
from utils.eoq_utils import EOQCalculator

class EOQPage(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(36, 30, 36, 30)
        root.setSpacing(20)

        title = QLabel("EOQ 经济订货批量")
        title.setObjectName("pageTitle")
        desc = QLabel("输入参数，计算经济订货批量和年度库存成本。")
        desc.setObjectName("pageDescription")
        root.addWidget(title)
        root.addWidget(desc)

        body = QHBoxLayout()
        body.setSpacing(20)

        input_card = QFrame()
        input_card.setObjectName("panelCard")
        input_layout = QVBoxLayout(input_card)
        input_layout.setContentsMargins(24, 24, 24, 24)

        panel_title = QLabel("参数输入")
        panel_title.setObjectName("panelTitle")

        form = QGridLayout()
        self.demand = QLineEdit()
        self.order_cost = QLineEdit()
        self.hold_cost = QLineEdit()
        self.demand.setPlaceholderText("例如：10000")
        self.order_cost.setPlaceholderText("例如：200")
        self.hold_cost.setPlaceholderText("例如：5")

        form.addWidget(QLabel("年需求量 D"), 0, 0)
        form.addWidget(self.demand, 0, 1)
        form.addWidget(QLabel("每次订货成本 S"), 1, 0)
        form.addWidget(self.order_cost, 1, 1)
        form.addWidget(QLabel("单位持有成本 H"), 2, 0)
        form.addWidget(self.hold_cost, 2, 1)

        button = QPushButton("开始计算")
        button.clicked.connect(self.calculate)

        input_layout.addWidget(panel_title)
        input_layout.addLayout(form)
        input_layout.addWidget(button)
        input_layout.addStretch()

        result_card = QFrame()
        result_card.setObjectName("panelCard")
        result_layout = QVBoxLayout(result_card)
        result_layout.setContentsMargins(24, 24, 24, 24)

        result_title = QLabel("计算结果")
        result_title.setObjectName("panelTitle")
        result_layout.addWidget(result_title)

        self.result_labels = {}
        metrics = [
            ("EOQ", "经济订货批量"),
            ("平均库存", "平均库存"),
            ("订货次数", "年订货次数"),
            ("订货周期", "平均订货周期"),
            ("年订货成本", "年订货成本"),
            ("年库存持有成本", "年库存持有成本"),
            ("总成本", "年度相关总成本"),
        ]
        for key, label_text in metrics:
            row = QHBoxLayout()
            row.addWidget(QLabel(label_text))
            value = QLabel("--")
            value.setObjectName("metricValue")
            row.addStretch()
            row.addWidget(value)
            result_layout.addLayout(row)
            self.result_labels[key] = value
        result_layout.addStretch()

        body.addWidget(input_card, 1)
        body.addWidget(result_card, 1)
        root.addLayout(body, 1)

    def calculate(self):
        try:
            result = EOQCalculator(
                float(self.demand.text()),
                float(self.order_cost.text()),
                float(self.hold_cost.text())
            ).report()
            for key, label in self.result_labels.items():
                label.setText(str(result[key]))
        except Exception as exc:
            QMessageBox.warning(self, "计算失败", str(exc))
