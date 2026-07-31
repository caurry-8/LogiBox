from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from utils.data_store import DataStore
from widgets.metric_card import MetricCard


class FunctionCard(QFrame):
    clicked = Signal()

    def __init__(self, icon: str, title: str, description: str) -> None:
        super().__init__()
        self.setObjectName("functionCard")
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)

        icon_label = QLabel(icon)
        icon_label.setObjectName("cardIcon")
        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        desc_label = QLabel(description)
        desc_label.setObjectName("cardDescription")
        desc_label.setWordWrap(True)

        layout.addWidget(icon_label)
        layout.addWidget(title_label)
        layout.addWidget(desc_label)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class DashboardPage(QWidget):
    def __init__(self, store: DataStore, navigate) -> None:
        super().__init__()
        self.store = store
        self.navigate = navigate
        self._build_ui()
        self.store.data_changed.connect(self.refresh)
        self.store.analysis_changed.connect(self.refresh)
        self.store.status_changed.connect(self.refresh)
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(34, 28, 34, 28)
        layout.setSpacing(16)

        header = QHBoxLayout()
        left = QVBoxLayout()
        left.setSpacing(3)
        title = QLabel("LogiBox Analytics Dashboard")
        title.setObjectName("pageTitle")
        subtitle = QLabel("物流工程数据驾驶舱 · Logistics Analytics Platform V3.2")
        subtitle.setObjectName("pageDescription")
        left.addWidget(title)
        left.addWidget(subtitle)
        header.addLayout(left)
        header.addStretch()
        self.data_status = QLabel("● 未加载数据")
        self.data_status.setObjectName("statusBadge")
        header.addWidget(self.data_status)
        layout.addLayout(header)

        metrics = QGridLayout()
        metrics.setHorizontalSpacing(14)
        metrics.setVerticalSpacing(14)
        self.row_card = MetricCard("数据行数", "--", "#28C7FA", "当前加载数据规模")
        self.column_card = MetricCard("字段数量", "--", "#6C7BFF", "可用于分析的字段")
        self.missing_card = MetricCard("缺失单元格", "--", "#FFB86B", "数据质量快速检查")
        self.duplicate_card = MetricCard("重复行", "--", "#FF6B8A", "建议分析前先清洗")
        metrics.addWidget(self.row_card, 0, 0)
        metrics.addWidget(self.column_card, 0, 1)
        metrics.addWidget(self.missing_card, 0, 2)
        metrics.addWidget(self.duplicate_card, 0, 3)
        layout.addLayout(metrics)

        section = QLabel("快速进入")
        section.setObjectName("sectionTitle")
        layout.addWidget(section)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)
        cards = [
            ("◈", "数据中心", "导入、预览、质量检查与导出数据", 1),
            ("◎", "EOQ 经济订货", "计算经济订货批量、频率与相关成本", 2),
            ("◇", "ABC 分类", "识别高价值库存与结构贡献", 3),
            ("△", "XYZ 分析", "评估需求波动与库存稳定性", 4),
            ("◌", "安全库存", "估算安全库存与再订货点 ROP", 5),
            ("▣", "报告中心", "汇总分析结果并生成 Word 报告", 6),
        ]
        for i, (icon, name, desc, index) in enumerate(cards):
            card = FunctionCard(icon, name, desc)
            card.clicked.connect(lambda idx=index: self.navigate(idx))
            grid.addWidget(card, i // 3, i % 3)
        layout.addLayout(grid)

        footer = QFrame()
        footer.setObjectName("dashboardNote")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(14, 10, 14, 10)
        self.file_label = QLabel("当前数据：未加载")
        self.file_label.setObjectName("dashboardNoteText")
        footer_layout.addWidget(self.file_label)
        footer_layout.addStretch()
        self.analysis_label = QLabel("分析状态：尚未开始")
        self.analysis_label.setObjectName("dashboardNoteText")
        footer_layout.addWidget(self.analysis_label)
        layout.addWidget(footer)
        layout.addStretch()

    def refresh(self, *_args) -> None:
        if not self.store.has_data():
            self.row_card.set_value("--")
            self.column_card.set_value("--")
            self.missing_card.set_value("--")
            self.duplicate_card.set_value("--")
            self.data_status.setText("● 未加载数据")
            self.file_label.setText("当前数据：未加载")
            self.analysis_label.setText("分析状态：尚未开始")
            return

        self.row_card.set_value(str(self.store.rows()))
        self.column_card.set_value(str(self.store.cols()))
        self.missing_card.set_value(str(self.store.missing_cells()))
        self.duplicate_card.set_value(str(self.store.duplicate_rows()))
        self.data_status.setText("● 数据已就绪")
        self.file_label.setText(f"当前数据：{self.store.filename_only()}")

        completed = [
            name for name in ["abc", "xyz", "eoq", "safety"] if self.store.has_analysis(name)
        ]
        self.analysis_label.setText(
            "分析状态：已完成 " + " / ".join(completed) if completed else "分析状态：尚未开始"
        )
