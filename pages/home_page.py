from typing import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget

from widgets.metric_card import MetricCard


class FunctionCard(QFrame):
    clicked = Signal()

    def __init__(self, icon: str, title: str, description: str) -> None:
        super().__init__()
        self.setObjectName('functionCard')
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(8)

        icon_label = QLabel(icon)
        icon_label.setObjectName('cardIcon')
        icon_label.setAlignment(Qt.AlignCenter)

        title_label = QLabel(title)
        title_label.setObjectName('cardTitle')
        title_label.setAlignment(Qt.AlignCenter)

        desc_label = QLabel(description)
        desc_label.setObjectName('cardDescription')
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setWordWrap(True)

        layout.addWidget(icon_label)
        layout.addWidget(title_label)
        layout.addWidget(desc_label)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class HomePage(QWidget):
    def __init__(self, navigate: Callable[[int], None], store) -> None:
        super().__init__()
        self.store = store
        self.navigate = navigate
        self._build_ui()

        self.store.data_changed.connect(self.refresh_data_summary)
        self.refresh_data_summary()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 30, 36, 30)
        layout.setSpacing(18)

        title = QLabel('工作台')
        title.setObjectName('pageTitle')
        subtitle = QLabel('LogiBox 物流工程效率工具箱 · 数据分析工作台')
        subtitle.setObjectName('pageDescription')

        layout.addWidget(title)
        layout.addWidget(subtitle)

        metrics = QGridLayout()
        metrics.setHorizontalSpacing(14)
        metrics.setVerticalSpacing(14)

        self.data_card = MetricCard('当前数据行数', '0', '尚未导入数据', '#62C2F4')
        self.field_card = MetricCard('数据字段数', '0', '等待数据导入', '#9C7CFF')
        self.file_card = MetricCard('当前数据文件', '--', '数据中心', '#4CAF50')
        self.status_card = MetricCard('分析入口', 'ABC', '导入数据后可直接进行库存分类', '#FFC107')

        metrics.addWidget(self.data_card, 0, 0)
        metrics.addWidget(self.field_card, 0, 1)
        metrics.addWidget(self.file_card, 0, 2)
        metrics.addWidget(self.status_card, 0, 3)
        layout.addLayout(metrics)

        self.hero = QFrame()
        self.hero.setObjectName('heroCard')
        hero_layout = QVBoxLayout(self.hero)
        hero_layout.setContentsMargins(24, 20, 24, 20)

        welcome = QLabel('欢迎使用 LogiBox V2.2')
        welcome.setObjectName('heroTitle')
        self.summary_label = QLabel()
        self.summary_label.setObjectName('heroText')
        self.summary_label.setWordWrap(True)

        hero_layout.addWidget(welcome)
        hero_layout.addWidget(self.summary_label)
        layout.addWidget(self.hero)

        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(18)

        cards = [
            ('📂', '数据中心', '导入 Excel / CSV，统一管理分析数据。', 1),
            ('📈', 'EOQ 计算', '计算经济订货批量与年度库存成本。', 2),
            ('📦', 'ABC 分类', '生成价值贡献分类、统计卡片与专业图表。', 3),
            ('📊', '安全库存 / ROP', '计算安全库存、服务水平与再订货点。', 4),
        ]

        for i, (icon, name, desc, index) in enumerate(cards):
            card = FunctionCard(icon, name, desc)
            card.clicked.connect(lambda idx=index: self.navigate(idx))
            grid.addWidget(card, i // 2, i % 2)

        layout.addLayout(grid)
        layout.addStretch()

    def refresh_data_summary(self) -> None:
        if self.store.has_data():
            self.data_card.set_value(self.store.rows())
            self.data_card.set_detail('当前已载入数据')
            self.field_card.set_value(self.store.cols())
            self.field_card.set_detail('数据字段数量')
            self.file_card.set_value(self.store.filename_only() or '--')
            self.file_card.set_detail('当前数据文件')
            self.summary_label.setText(
                f'当前数据：{self.store.filename_only()} · '
                f'{self.store.rows()} 行 × {self.store.cols()} 列。'
                ' 现在可以直接进入 ABC 分类进行分析。'
            )
        else:
            self.data_card.set_value('0')
            self.data_card.set_detail('尚未导入数据')
            self.field_card.set_value('0')
            self.field_card.set_detail('等待数据导入')
            self.file_card.set_value('--')
            self.file_card.set_detail('数据中心')
            self.summary_label.setText(
                '当前还没有导入数据。建议先进入“数据中心”，导入一个 Excel 或 CSV 文件。'
            )
