from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout, QWidget

from utils.eoq_utils import EOQCalculator
from utils.data_store import DataStore
from widgets.metric_card import MetricCard


class EOQPage(QWidget):
    def __init__(self, store: DataStore | None = None) -> None:
        super().__init__()
        self.store = store
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(34, 28, 34, 22)
        root.setSpacing(14)

        title = QLabel("EOQ 经济订货批量")
        title.setObjectName("pageTitle")
        desc = QLabel("快速计算经济订货批量、订货频率与年度相关库存成本。")
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

        self.demand = QLineEdit()
        self.order_cost = QLineEdit()
        self.hold_cost = QLineEdit()
        self.demand.setPlaceholderText("例如 10000")
        self.order_cost.setPlaceholderText("例如 200")
        self.hold_cost.setPlaceholderText("例如 5")

        form.addWidget(QLabel("年需求量 D"), 0, 0)
        form.addWidget(self.demand, 0, 1)
        form.addWidget(QLabel("订货成本 S"), 1, 0)
        form.addWidget(self.order_cost, 1, 1)
        form.addWidget(QLabel("持有成本 H"), 2, 0)
        form.addWidget(self.hold_cost, 2, 1)

        button = QPushButton("计算 EOQ")
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

        metrics = QGridLayout()
        metrics.setHorizontalSpacing(12)
        metrics.setVerticalSpacing(12)
        self.cards = {}
        defs = [
            ("EOQ", "经济订货批量", "#28C7FA"),
            ("平均库存", "平均库存", "#6C7BFF"),
            ("订货次数", "年订货次数", "#A970FF"),
            ("订货周期", "平均订货周期", "#FFB86B"),
            ("年订货成本", "年订货成本", "#64D8CB"),
            ("年库存持有成本", "年库存持有成本", "#FF6B8A"),
        ]
        for i, (key, text, color) in enumerate(defs):
            card = MetricCard(text, "--", color)
            self.cards[key] = card
            metrics.addWidget(card, i // 2, i % 2)
        result_layout.addLayout(metrics)
        total_card = MetricCard("年度相关总成本", "--", "#FFFFFF", "订货成本 + 库存持有成本")
        self.cards["总成本"] = total_card
        result_layout.addWidget(total_card)
        result_layout.addStretch()

        body.addWidget(form_panel, 1)
        body.addWidget(result_panel, 2)
        root.addLayout(body, 1)

    def calculate(self) -> None:
        try:
            result = EOQCalculator(
                float(self.demand.text()),
                float(self.order_cost.text()),
                float(self.hold_cost.text()),
            ).report()
            for key, card in self.cards.items():
                card.set_value(str(result[key]))
            # The page is intentionally decoupled from DataStore for compatibility.
            self.last_result = result
            if self.store is not None:
                self.store.set_analysis("eoq", result)
        except Exception as exc:
            QMessageBox.warning(self, "计算失败", str(exc))
