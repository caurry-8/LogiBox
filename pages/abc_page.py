from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

class ABCPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 30, 36, 30)
        layout.setSpacing(20)

        title = QLabel("ABC 库存分类")
        title.setObjectName("pageTitle")
        desc = QLabel("按库存价值贡献进行 A / B / C 分类。")
        desc.setObjectName("pageDescription")
        layout.addWidget(title)
        layout.addWidget(desc)

        cards = QHBoxLayout()
        for name in ["A 类", "B 类", "C 类"]:
            card = QFrame()
            card.setObjectName("metricCard")
            card_layout = QVBoxLayout(card)
            n = QLabel(name)
            n.setObjectName("metricLabel")
            v = QLabel("--")
            v.setObjectName("bigMetric")
            card_layout.addWidget(n)
            card_layout.addWidget(v)
            cards.addWidget(card)
        layout.addLayout(cards)

        panel = QFrame()
        panel.setObjectName("panelCard")
        panel_layout = QVBoxLayout(panel)
        panel_layout.addWidget(QLabel("V1.0 模块说明"))
        panel_layout.addWidget(QLabel(
            "当前先完成界面框架。后续将接入数据中心的导入数据，支持："
            "字段选择、自定义阈值、分类结果、帕累托图和结果导出。"
        ))
        layout.addWidget(panel)
        layout.addStretch()
