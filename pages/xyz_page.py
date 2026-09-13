import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QGridLayout,
    QDoubleSpinBox,
)

from utils.data_store import DataStore
from utils.excel_utils import export_dataframe
from utils.quality_text import format_cell_value, xyz_status_label
from utils.xyz_utils import QUALITY_COLUMN, STATUS_INVALID, STATUS_MISSING, XYZAnalyzer
from widgets.metric_card import MetricCard


class XYZPage(QWidget):
    def __init__(self, store: DataStore) -> None:
        super().__init__()
        self.store = store
        self.result_df: pd.DataFrame | None = None
        self._build_ui()
        self.store.data_changed.connect(self.refresh_columns)
        self.refresh_columns()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(34, 28, 34, 22)
        root.setSpacing(14)

        header = QHBoxLayout()
        left = QVBoxLayout()
        left.setSpacing(2)
        title = QLabel("XYZ 需求稳定性分析")
        title.setObjectName("pageTitle")
        desc = QLabel("基于历史需求波动计算变异系数 CV，识别 X 稳定、Y 波动、Z 不稳定库存。")
        desc.setObjectName("pageDescription")
        left.addWidget(title)
        left.addWidget(desc)
        header.addLayout(left)
        header.addStretch()
        self.status = QLabel("待分析")
        self.status.setObjectName("statusBadge")
        header.addWidget(self.status)
        root.addLayout(header)

        basis_note = QLabel(
            "分类依据：变异系数 CV = 需求标准差 ÷ 平均需求。X 类需求稳定，Y 类存在一定波动，Z 类需求波动较大。"
        )
        basis_note.setObjectName("analysisNote")
        basis_note.setWordWrap(True)
        root.addWidget(basis_note)

        controls = QFrame()
        controls.setObjectName("controlBar")
        controls_layout = QGridLayout(controls)
        controls_layout.setContentsMargins(16, 12, 16, 12)
        controls_layout.setHorizontalSpacing(12)
        controls_layout.setVerticalSpacing(10)

        self.period_list = QListWidget()
        self.period_list.setSelectionMode(QListWidget.NoSelection)
        self.period_list.setMinimumHeight(110)
        self.x_spin = QDoubleSpinBox()
        self.x_spin.setRange(0.01, 0.99)
        self.x_spin.setSingleStep(0.01)
        self.x_spin.setValue(0.10)
        self.x_spin.setSuffix(" CV")
        self.y_spin = QDoubleSpinBox()
        self.y_spin.setRange(0.02, 1.99)
        self.y_spin.setSingleStep(0.01)
        self.y_spin.setValue(0.25)
        self.y_spin.setSuffix(" CV")

        analyze = QPushButton("开始分析")
        analyze.clicked.connect(self.run_analysis)
        export = QPushButton("导出结果")
        export.setObjectName("secondaryButton")
        export.clicked.connect(self.export_result)

        controls_layout.addWidget(QLabel("历史需求周期（可多选）"), 0, 0, 1, 2)
        controls_layout.addWidget(self.period_list, 1, 0, 3, 2)
        controls_layout.addWidget(QLabel("X 类阈值"), 0, 2)
        controls_layout.addWidget(self.x_spin, 0, 3)
        controls_layout.addWidget(QLabel("Y 类阈值"), 1, 2)
        controls_layout.addWidget(self.y_spin, 1, 3)
        controls_layout.addWidget(analyze, 2, 2)
        controls_layout.addWidget(export, 2, 3)
        root.addWidget(controls)

        metrics = QHBoxLayout()
        self.card_x = MetricCard("X 类", "--", "#28C7FA", "需求稳定")
        self.card_y = MetricCard("Y 类", "--", "#6C7BFF", "需求波动")
        self.card_z = MetricCard("Z 类", "--", "#A970FF", "需求不稳定")
        metrics.addWidget(self.card_x)
        metrics.addWidget(self.card_y)
        metrics.addWidget(self.card_z)
        root.addLayout(metrics)

        self.coverage_note = QLabel("完成分析后显示数据覆盖情况。")
        self.coverage_note.setObjectName("analysisNote")
        self.coverage_note.setWordWrap(True)
        root.addWidget(self.coverage_note)

        table_panel = QFrame()
        table_panel.setObjectName("tablePanel")
        table_layout = QVBoxLayout(table_panel)
        table_title = QLabel("XYZ 分类结果明细")
        table_title.setObjectName("sectionTitle")
        table_layout.addWidget(table_title)
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        table_layout.addWidget(self.table, 1)

        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(table_panel)
        splitter.setStretchFactor(0, 1)
        root.addWidget(splitter, 1)

    def refresh_columns(self) -> None:
        self.period_list.clear()
        for column in self.store.numeric_columns():
            item = QListWidgetItem(column)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.period_list.addItem(item)
        # 数据源变化后旧结果失效，覆盖说明一并复位
        self.coverage_note.setText("完成分析后显示数据覆盖情况。")

    def _selected_periods(self) -> list[str]:
        columns = []
        for i in range(self.period_list.count()):
            item = self.period_list.item(i)
            if item.checkState() == Qt.Checked:
                columns.append(item.text())
        return columns

    def run_analysis(self) -> None:
        df = self.store.dataframe()
        if df is None:
            QMessageBox.information(self, "提示", "请先在数据中心导入数据。")
            return
        periods = self._selected_periods()
        if len(periods) < 2:
            QMessageBox.warning(self, "参数错误", "请至少勾选 2 个历史需求周期字段。")
            return
        if self.x_spin.value() >= self.y_spin.value():
            QMessageBox.warning(self, "参数错误", "X 类阈值必须小于 Y 类阈值。")
            return

        try:
            result = XYZAnalyzer(
                df,
                periods,
                self.x_spin.value(),
                self.y_spin.value(),
            ).analyze()
            self.result_df = result.dataframe
            self.card_x.set_value(str(result.counts["X"]))
            self.card_y.set_value(str(result.counts["Y"]))
            self.card_z.set_value(str(result.counts["Z"]))
            # 占比基数是「已完成分类的 SKU」，必须在文案中明确，避免被误读为全部 SKU 的比例。
            classified = result.classified_count
            self.card_x.set_hint(self._share_hint("需求稳定", result.counts["X"], classified))
            self.card_y.set_hint(
                self._share_hint("需求存在一定波动", result.counts["Y"], classified)
            )
            self.card_z.set_hint(
                self._share_hint("需求波动较大", result.counts["Z"], classified)
            )
            self.coverage_note.setText(self._coverage_text(result))
            self.status.setText("分析完成")
            self._refresh_table()
            self.store.set_analysis(
                "xyz",
                {
                    "dataframe": self.result_df,
                    "counts": result.counts,
                    "mean_cv": result.mean_cv,
                    "status_counts": result.status_counts,
                    "total_count": result.total_count,
                    "period_columns": periods,
                    "x_rate": self.x_spin.value(),
                    "y_rate": self.y_spin.value(),
                },
            )
        except Exception as exc:
            self.status.setText("分析失败")
            QMessageBox.critical(self, "分析失败", str(exc))

    @staticmethod
    def _share_hint(label: str, count: int, classified: int) -> str:
        """分类占比提示，明确写出分母是「已分类 SKU」。"""
        if classified <= 0:
            return f"{label} · 暂无有效分类"
        return f"{label} · 占已分类 SKU 的 {count / classified:.1%}"

    @staticmethod
    def _coverage_text(result) -> str:
        """数据覆盖说明：总量、有效分类、未分类原因、平均 CV 口径。"""
        classified = result.classified_count
        total = result.total_count
        lines = [
            f"数据覆盖：有效分类 {classified} / 总 SKU {total}"
            f"（覆盖率 {result.coverage_rate:.1%}）"
        ]
        if result.unclassified_count:
            missing = result.status_counts.get(STATUS_MISSING, 0)
            invalid = result.status_counts.get(STATUS_INVALID, 0)
            lines.append(
                f"未参与分类 {result.unclassified_count}"
                f"（缺失数据 {missing} / 非法数据 {invalid}）"
            )
        if result.mean_cv is None:
            lines.append("平均 CV：暂无有效数据")
        else:
            lines.append(f"平均 CV：{result.mean_cv:.4f}（基于 {classified} 个有效 SKU）")
        lines.append("X / Y / Z 分布基于已完成有效分类的 SKU。")
        return "\n".join(lines)

    def _refresh_table(self) -> None:
        if self.result_df is None:
            return
        df = self.result_df
        self.table.setSortingEnabled(False)
        self.table.clear()
        self.table.setRowCount(len(df))
        self.table.setColumnCount(len(df.columns))
        self.table.setHorizontalHeaderLabels([str(c) for c in df.columns])
        for r in range(len(df)):
            for c in range(len(df.columns)):
                value = df.iat[r, c]
                column = df.columns[c]
                if column == QUALITY_COLUMN and isinstance(value, str):
                    # 内部状态语义（valid / missing / invalid）不直接暴露给用户
                    text = xyz_status_label(value)
                else:
                    # CV 列固定 4 位小数；缺失与非法值统一为占位符
                    digits = 4 if column == "变异系数CV" else None
                    text = format_cell_value(value, digits)
                self.table.setItem(r, c, QTableWidgetItem(text))
        self.table.resizeColumnsToContents()
        self.table.setSortingEnabled(True)

    def export_result(self) -> None:
        if self.result_df is None:
            QMessageBox.information(self, "提示", "请先完成 XYZ 分析。")
            return
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "保存 XYZ 分析结果",
            "XYZ分析结果.xlsx",
            "Excel 文件 (*.xlsx);;CSV 文件 (*.csv)",
        )
        if not filename:
            return
        try:
            export_dataframe(self.result_df, filename)
            QMessageBox.information(self, "导出成功", f"结果已保存：\n{filename}")
        except Exception as exc:
            QMessageBox.critical(self, "导出失败", str(exc))
