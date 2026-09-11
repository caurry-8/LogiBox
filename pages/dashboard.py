from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from utils.data_store import DataStore
from widgets.metric_card import MetricCard


class ActionCard(QFrame):
    clicked = Signal()

    def __init__(self, title: str, description: str, action_text: str) -> None:
        super().__init__()
        self.setObjectName("functionCard")
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(7)

        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        description_label = QLabel(description)
        description_label.setObjectName("cardDescription")
        description_label.setWordWrap(True)
        action_label = QLabel(action_text)
        action_label.setObjectName("cardAction")

        layout.addWidget(title_label)
        layout.addWidget(description_label)
        layout.addStretch(1)
        layout.addWidget(action_label)

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
        layout.setSpacing(18)

        header = QHBoxLayout()
        header_left = QVBoxLayout()
        header_left.setSpacing(3)

        title = QLabel("库存分析总览")
        title.setObjectName("pageTitle")
        subtitle = QLabel("监控数据质量、运行库存分析模型，并导出分析结果。")
        subtitle.setObjectName("pageDescription")
        header_left.addWidget(title)
        header_left.addWidget(subtitle)

        header.addLayout(header_left)
        header.addStretch(1)

        import_button = QPushButton("导入数据")
        import_button.setObjectName("primaryButton")
        import_button.setCursor(Qt.PointingHandCursor)
        import_button.clicked.connect(lambda: self.navigate("data_center"))
        header.addWidget(import_button)

        self.data_status = QLabel("未加载数据")
        self.data_status.setObjectName("statusBadge")
        header.addWidget(self.data_status)
        layout.addLayout(header)

        divider = QFrame()
        divider.setObjectName("pageDivider")
        divider.setFixedHeight(1)
        layout.addWidget(divider)

        overview_header = QHBoxLayout()
        overview_title = QLabel("数据概览")
        overview_title.setObjectName("sectionTitle")
        overview_header.addWidget(overview_title)
        overview_header.addStretch(1)
        self.file_label = QLabel("当前没有活动的数据集")
        self.file_label.setObjectName("mutedLabel")
        overview_header.addWidget(self.file_label)
        layout.addLayout(overview_header)

        metrics = QGridLayout()
        metrics.setHorizontalSpacing(12)
        metrics.setVerticalSpacing(12)
        self.row_card = MetricCard("数据行数", "--", "#58a6ff", "可用于分析的记录数")
        self.column_card = MetricCard("字段数量", "--", "#a5d6ff", "数据集中识别到的字段")
        self.missing_card = MetricCard("缺失单元格", "--", "#d29922", "运行模型前建议先检查")
        self.duplicate_card = MetricCard("重复行", "--", "#f85149", "可能存在数据质量问题")
        metrics.addWidget(self.row_card, 0, 0)
        metrics.addWidget(self.column_card, 0, 1)
        metrics.addWidget(self.missing_card, 0, 2)
        metrics.addWidget(self.duplicate_card, 0, 3)
        layout.addLayout(metrics)

        content = QHBoxLayout()
        content.setSpacing(14)

        actions_panel = QFrame()
        actions_panel.setObjectName("contentPanel")
        actions_layout = QVBoxLayout(actions_panel)
        actions_layout.setContentsMargins(18, 16, 18, 18)
        actions_layout.setSpacing(10)

        actions_title = QLabel("快捷操作")
        actions_title.setObjectName("sectionTitle")
        actions_layout.addWidget(actions_title)

        action_grid = QGridLayout()
        action_grid.setHorizontalSpacing(10)
        action_grid.setVerticalSpacing(10)
        cards = [
            ("数据中心", "导入、预览、校验并导出表格数据。", "打开数据中心  →", "data_center"),
            ("ABC 库存分类", "按价值贡献对库存进行 ABC 分类。", "运行 ABC 分析  →", "abc"),
            ("XYZ 稳定性分析", "衡量多个周期的需求波动程度。", "运行 XYZ 分析  →", "xyz"),
            ("ABC × XYZ 矩阵", "结合价值与稳定性生成 3×3 策略矩阵。", "生成交叉矩阵  →", "matrix"),
            ("安全库存 / ROP", "按服务水平估算安全库存与再订货点。", "打开安全库存  →", "safety"),
            ("报告中心", "一键生成汇总的 Word 分析报告。", "打开报告中心  →", "report"),
        ]
        for i, (name, desc, action, key) in enumerate(cards):
            card = ActionCard(name, desc, action)
            card.clicked.connect(lambda _=False, target=key: self.navigate(target))
            action_grid.addWidget(card, i // 2, i % 2)
        actions_layout.addLayout(action_grid)
        content.addWidget(actions_panel, 2)

        activity_panel = QFrame()
        activity_panel.setObjectName("contentPanel")
        activity_layout = QVBoxLayout(activity_panel)
        activity_layout.setContentsMargins(18, 16, 18, 18)
        activity_layout.setSpacing(11)

        activity_title = QLabel("分析状态")
        activity_title.setObjectName("sectionTitle")
        activity_layout.addWidget(activity_title)

        self.analysis_rows: dict[str, QLabel] = {}
        for key, label_text in [
            ("abc", "ABC 库存分类"),
            ("xyz", "XYZ 稳定性分析"),
            ("matrix", "交叉矩阵"),
            ("eoq", "EOQ 经济订货"),
            ("safety", "安全库存"),
        ]:
            row = QFrame()
            row.setObjectName("activityRow")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(10, 8, 10, 8)
            name = QLabel(label_text)
            name.setObjectName("activityName")
            status = QLabel("未开始")
            status.setObjectName("activityStatus")
            row_layout.addWidget(name)
            row_layout.addStretch(1)
            row_layout.addWidget(status)
            activity_layout.addWidget(row)
            self.analysis_rows[key] = status

        structure_title = QLabel("库存结构")
        structure_title.setObjectName("sectionTitle")
        activity_layout.addWidget(structure_title)
        self.structure_summary = QLabel("完成 ABC 与 XYZ 分析后显示分类结构。")
        self.structure_summary.setObjectName("summaryText")
        self.structure_summary.setWordWrap(True)
        activity_layout.addWidget(self.structure_summary)

        matrix_title = QLabel("ABC × XYZ 分布")
        matrix_title.setObjectName("sectionTitle")
        activity_layout.addWidget(matrix_title)
        self.matrix_summary = QLabel("完成交叉矩阵分析后显示 9 个组合的 SKU 数量。")
        self.matrix_summary.setObjectName("summaryText")
        self.matrix_summary.setWordWrap(True)
        activity_layout.addWidget(self.matrix_summary)

        activity_layout.addStretch(1)
        content.addWidget(activity_panel, 1)
        layout.addLayout(content)
        layout.addStretch(1)

    def refresh(self, *_args) -> None:
        if not self.store.has_data():
            self.row_card.set_value("--")
            self.column_card.set_value("--")
            self.missing_card.set_value("--")
            self.duplicate_card.set_value("--")
            self.data_status.setText("未加载数据")
            self.data_status.setProperty("ready", False)
            self.file_label.setText("当前没有活动的数据集")
            for label in self.analysis_rows.values():
                label.setText("未开始")
                label.setProperty("complete", False)
                label.style().unpolish(label)
                label.style().polish(label)
            self.structure_summary.setText("完成 ABC 与 XYZ 分析后显示分类结构。")
            self.matrix_summary.setText("完成交叉矩阵分析后显示 9 个组合的 SKU 数量。")
            return

        self.row_card.set_value(str(self.store.rows()))
        self.column_card.set_value(str(self.store.cols()))
        self.missing_card.set_value(str(self.store.missing_cells()))
        self.duplicate_card.set_value(str(self.store.duplicate_rows()))
        self.data_status.setText("数据已就绪")
        self.data_status.setProperty("ready", True)
        self.data_status.style().unpolish(self.data_status)
        self.data_status.style().polish(self.data_status)
        self.file_label.setText(f"当前数据集：{self.store.filename_only()}")

        for key, label in self.analysis_rows.items():
            complete = self.store.has_analysis(key)
            label.setText("已完成" if complete else "未开始")
            label.setProperty("complete", complete)
            label.style().unpolish(label)
            label.style().polish(label)

        abc = self.store.get_analysis("abc") or {}
        xyz = self.store.get_analysis("xyz") or {}
        abc_counts = abc.get("counts", {})
        xyz_counts = xyz.get("counts", {})
        if abc_counts or xyz_counts:
            abc_text = "ABC：" + " · ".join(
                f"{key} 类 {abc_counts.get(key, 0)}" for key in ("A", "B", "C")
            )
            xyz_text = "XYZ：" + " · ".join(
                f"{key} 类 {xyz_counts.get(key, 0)}" for key in ("X", "Y", "Z")
            )
            self.structure_summary.setText(f"{abc_text}\n{xyz_text}")
        else:
            self.structure_summary.setText("完成 ABC 与 XYZ 分析后显示分类结构。")

        matrix = self.store.get_analysis("matrix") or {}
        matrix_counts = matrix.get("cell_counts", {})
        if matrix_counts:
            rows = [
                " · ".join(f"{cell} {matrix_counts.get(cell, 0)}" for cell in cells)
                for cells in (("AX", "AY", "AZ"), ("BX", "BY", "BZ"), ("CX", "CY", "CZ"))
            ]
            self.matrix_summary.setText("\n".join(rows))
        else:
            self.matrix_summary.setText("完成交叉矩阵分析后显示 9 个组合的 SKU 数量。")
