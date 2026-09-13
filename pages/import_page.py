from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from utils.data_store import DataStore
from utils.excel_utils import export_dataframe
from utils.quality_text import (
    SEVERITY_COLORS,
    describe,
    format_cell_value,
    impact_text,
    severity_label,
    status_label,
)
from utils.quality_utils import assess_data_quality


class ImportPage(QWidget):
    def __init__(self, store: DataStore) -> None:
        super().__init__()
        self.store = store
        self._build_ui()
        self.store.data_changed.connect(self.refresh_table)
        self.refresh_table()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(34, 28, 34, 22)
        layout.setSpacing(14)

        title = QLabel("数据中心")
        title.setObjectName("pageTitle")
        description = QLabel("统一管理数据源。支持 Excel / CSV 导入、预览、质量检查、示例数据与导出。")
        description.setObjectName("pageDescription")
        layout.addWidget(title)
        layout.addWidget(description)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        open_button = QPushButton("导入数据")
        open_button.clicked.connect(self.open_file)
        sample_button = QPushButton("加载示例数据")
        sample_button.setObjectName("secondaryButton")
        sample_button.clicked.connect(self.load_sample)
        export_button = QPushButton("导出当前数据")
        export_button.clicked.connect(self.export_current)
        clear_button = QPushButton("清空")
        clear_button.setObjectName("dangerButton")
        clear_button.clicked.connect(self.clear_data)
        self.file_label = QLabel("未加载文件")
        self.file_label.setObjectName("mutedLabel")
        self.stats_label = QLabel("0 行 × 0 列")
        self.stats_label.setObjectName("mutedLabel")
        toolbar.addWidget(open_button)
        toolbar.addWidget(sample_button)
        toolbar.addWidget(export_button)
        toolbar.addWidget(clear_button)
        toolbar.addSpacing(10)
        toolbar.addWidget(self.file_label)
        toolbar.addStretch()
        toolbar.addWidget(self.stats_label)
        layout.addLayout(toolbar)

        layout.addWidget(self._build_quality_panel())

        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.DoubleClicked)
        layout.addWidget(self.table, 1)

    def _build_quality_panel(self) -> QFrame:
        """轻量数据质量概览：状态 + 关键数字 + 问题列表（不做成完整 Dashboard）。"""
        panel = QFrame()
        panel.setObjectName("qualityPanel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(14, 12, 14, 12)
        panel_layout.setSpacing(6)

        header = QHBoxLayout()
        header.setSpacing(10)
        title = QLabel("数据质量")
        title.setObjectName("sectionTitle")
        self.quality_status = QLabel("未加载数据")
        self.quality_status.setObjectName("qualityStatus")
        header.addWidget(title)
        header.addWidget(self.quality_status)
        header.addStretch()
        panel_layout.addLayout(header)

        self.quality_metrics = QLabel("")
        self.quality_metrics.setObjectName("mutedLabel")
        self.quality_metrics.setWordWrap(True)
        panel_layout.addWidget(self.quality_metrics)

        self.quality_issues = QLabel("")
        self.quality_issues.setObjectName("qualityIssues")
        self.quality_issues.setWordWrap(True)
        self.quality_issues.setTextFormat(Qt.RichText)
        panel_layout.addWidget(self.quality_issues)

        return panel

    def open_file(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "选择数据文件",
            "",
            "Excel / CSV (*.xlsx *.xls *.csv)",
        )
        if not filename:
            return
        try:
            self.store.load(filename)
        except Exception as exc:
            QMessageBox.critical(self, "导入失败", str(exc))

    def load_sample(self) -> None:
        sample_path = Path(__file__).resolve().parents[1] / "data" / "sample_inventory.csv"
        try:
            self.store.load(str(sample_path))
            QMessageBox.information(self, "加载成功", "已加载 LogiBox 示例库存数据。")
        except Exception as exc:
            QMessageBox.critical(self, "加载失败", str(exc))

    def clear_data(self) -> None:
        self.store.clear()

    def export_current(self) -> None:
        if not self.store.has_data():
            QMessageBox.information(self, "提示", "当前没有可导出的数据。")
            return
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "导出当前数据",
            "LogiBox数据.xlsx",
            "Excel 文件 (*.xlsx);;CSV 文件 (*.csv)",
        )
        if not filename:
            return
        try:
            export_dataframe(self.store.dataframe(), filename)
            QMessageBox.information(self, "导出成功", f"已导出：\n{filename}")
        except Exception as exc:
            QMessageBox.critical(self, "导出失败", str(exc))

    def refresh_quality(self) -> None:
        """刷新数据质量概览。字段识别遵循「不猜测」：只有高置信命中主键列名才给出 SKU 级指标。"""
        df = self.store.dataframe()
        result = assess_data_quality(df)

        self.quality_status.setText(status_label(result.status))
        self.quality_status.setProperty("severity", result.status)
        self.quality_status.style().unpolish(self.quality_status)
        self.quality_status.style().polish(self.quality_status)

        if df is None:
            self.quality_metrics.setText("")
            self.quality_issues.setText("")
            return

        parts = [f"总记录 {result.total_rows}", f"字段 {result.total_columns}"]
        if result.has_key_metrics:
            parts.extend(
                [
                    f"主键 {result.key_column}",
                    f"有效 SKU {result.valid_key_count}",
                    f"空值 SKU {result.empty_key_count}",
                    f"重复 SKU {result.duplicate_key_count}",
                ]
            )
        parts.extend(
            [
                f"缺失单元格 {result.missing_cell_count}",
                f"阻断 {result.blocker_count} ｜ 警告 {result.warning_count}",
            ]
        )
        self.quality_metrics.setText(" ｜ ".join(parts))

        if not result.issues:
            self.quality_issues.setText("未发现数据质量问题。")
            return

        lines = []
        for issue in result.issues:
            title, description, action = describe(issue)
            color = SEVERITY_COLORS.get(issue.severity, "#8b949e")
            detail = description
            if issue.affected_count:
                detail += f"（受影响 {issue.affected_count} 项）"
            impact = impact_text(issue)
            if impact:
                detail += f"　{impact}"
            lines.append(
                f'<span style="color:{color};">{severity_label(issue.severity)}</span>'
                f"　<b>{title}</b>　{detail}"
                f'<br/><span style="color:#6e7681;">建议：{action}</span>'
            )
        self.quality_issues.setText("<br/>".join(lines))

    def refresh_table(self) -> None:
        df = self.store.dataframe()
        self.refresh_quality()
        self.table.setSortingEnabled(False)
        self.table.clear()

        if df is None:
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
            self.table.setSortingEnabled(True)
            self.file_label.setText("未加载文件")
            self.stats_label.setText("0 行 × 0 列")
            return

        self.table.setRowCount(len(df))
        self.table.setColumnCount(len(df.columns))
        self.table.setHorizontalHeaderLabels([str(c) for c in df.columns])

        for r in range(len(df)):
            for c in range(len(df.columns)):
                self.table.setItem(
                    r, c, QTableWidgetItem(format_cell_value(df.iat[r, c]))
                )

        self.table.resizeColumnsToContents()
        self.table.setSortingEnabled(True)
        self.file_label.setText(Path(self.store.filename).name if self.store.filename else "未加载文件")
        self.stats_label.setText(f"{self.store.rows()} 行 × {self.store.cols()} 列")
