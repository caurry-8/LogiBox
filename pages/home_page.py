from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget

class FunctionCard(QFrame):
    clicked = Signal()
    def __init__(self, icon, title, description):
        super().__init__()
        self.setObjectName("functionCard")
        self.setCursor(Qt.PointingHandCursor)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(8)

        icon_label = QLabel(icon)
        icon_label.setObjectName("cardIcon")
        icon_label.setAlignment(Qt.AlignCenter)
        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        title_label.setAlignment(Qt.AlignCenter)
        desc_label = QLabel(description)
        desc_label.setObjectName("cardDescription")
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setWordWrap(True)

        layout.addWidget(icon_label)
        layout.addWidget(title_label)
        layout.addWidget(desc_label)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

class HomePage(QWidget):
    def __init__(self, navigate):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 30, 36, 30)
        layout.setSpacing(20)

        title = QLabel("工作台")
        title.setObjectName("pageTitle")
        subtitle = QLabel("快速进入常用物流工程分析工具")
        subtitle.setObjectName("pageDescription")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        hero = QFrame()
        hero.setObjectName("heroCard")
        hero_layout = QVBoxLayout(hero)
        welcome = QLabel("欢迎使用 LogiBox")
        welcome.setObjectName("heroTitle")
        message = QLabel("从数据导入开始，完成库存分析、EOQ、安全库存与再订货点计算。")
        message.setObjectName("heroText")
        message.setWordWrap(True)
        hero_layout.addWidget(welcome)
        hero_layout.addWidget(message)
        layout.addWidget(hero)

        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(18)

        cards = [
            ("📂", "数据导入", "导入 Excel / CSV 数据", 1),
            ("📈", "EOQ 计算", "经济订货批量与库存成本", 2),
            ("📦", "ABC 分类", "按金额贡献分析库存结构", 3),
            ("📊", "安全库存 / ROP", "安全库存与再订货点", 4),
        ]

        for i, (icon, title_text, desc, index) in enumerate(cards):
            card = FunctionCard(icon, title_text, desc)
            card.clicked.connect(lambda idx=index: navigate(idx))
            grid.addWidget(card, i // 2, i % 2)

        layout.addLayout(grid)
        layout.addStretch()
