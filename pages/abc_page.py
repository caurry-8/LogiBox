import pandas as pd
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from utils.abc_utils import ABCAnalyzer
from utils.chart_utils import ChartCanvas
from utils.data_store import DataStore
from utils.excel_utils import export_dataframe
from widgets.metric_card import MetricCard


class ABCPage(QWidget):
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
        title = QLabel("ABC 库存分类")
        title.setObjectName("pageTitle")
        desc = QLabel("按价值贡献识别重点库存，支持“年需求量 × 单价”自动生成年度消耗金额。")
        desc.setObjectName("pageDescription")
        left.addWidget(title)
        left.addWidget(desc)
        header.addLayout(left)
        header.addStretch()
        self.analysis_status = QLabel("待分析")
        self.analysis_status.setObjectName("statusBadge")
        header.addWidget(self.analysis_status)
        root.addLayout(header)

        controls = QFrame()
        controls.setObjectName("controlBar")
        grid = QGridLayout(controls)
        grid.setContentsMargins(16, 12, 16, 12)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["直接使用现有数值字段", "年需求量 × 单价 = 年消耗金额"])
        self.mode_combo.currentIndexChanged.connect(self.refresh_controls)
        self.value_combo = QComboBox()
        self.demand_combo = QComboBox()
        self.price_combo = QComboBox()
        self.a_spin = QDoubleSpinBox()
        self.a_spin.setRange(1, 98)
        self.a_spin.setValue(80)
        self.a_spin.setSuffix(" %")
        self.b_spin = QDoubleSpinBox()
        self.b_spin.setRange(2, 99)
        self.b_spin.setValue(95)
        self.b_spin.setSuffix(" %")
        self.auto_checkbox = QCheckBox("将年消耗金额写入共享数据")
        self.auto_checkbox.setChecked(True)
        analyze_button = QPushButton("开始分析")
        analyze_button.clicked.connect(self.run_analysis)
        export_button = QPushButton("导出结果")
        export_button.setObjectName("secondaryButton")
        export_button.clicked.connect(self.export_result)
        grid.addWidget(QLabel("模式"), 0, 0)
        grid.addWidget(self.mode_combo, 0, 1)
        grid.addWidget(QLabel("直接字段"), 0, 2)
        grid.addWidget(self.value_combo, 0, 3)
        grid.addWidget(QLabel("年需求量"), 1, 0)
        grid.addWidget(self.demand_combo, 1, 1)
        grid.addWidget(QLabel("单价"), 1, 2)
        grid.addWidget(self.price_combo, 1, 3)
        grid.addWidget(QLabel("A 类阈值"), 2, 0)
        grid.addWidget(self.a_spin, 2, 1)
        grid.addWidget(QLabel("B 类阈值"), 2, 2)
        grid.addWidget(self.b_spin, 2, 3)
        grid.addWidget(self.auto_checkbox, 3, 0, 1, 2)
        buttons = QHBoxLayout()
        buttons.addWidget(analyze_button)
        buttons.addWidget(export_button)
        buttons.addStretch()
        grid.addLayout(buttons, 3, 2, 1, 2)
        root.addWidget(controls)

        metrics = QHBoxLayout()
        metrics.setSpacing(12)
        self.card_a = MetricCard("A 类", "--", "#28C7FA", "SKU 数量")
        self.card_b = MetricCard("B 类", "--", "#6C7BFF", "SKU 数量")
        self.card_c = MetricCard("C 类", "--", "#A970FF", "SKU 数量")
        metrics.addWidget(self.card_a)
        metrics.addWidget(self.card_b)
        metrics.addWidget(self.card_c)
        root.addLayout(metrics)

        chart_container = QFrame()
        chart_container.setObjectName("chartPanel")
        chart_layout = QHBoxLayout(chart_container)
        chart_layout.setContentsMargins(8, 8, 8, 8)
        chart_layout.setSpacing(8)
        self.pie_chart = ChartCanvas()
        self.bar_chart = ChartCanvas()
        chart_layout.addWidget(self.pie_chart, 1)
        chart_layout.addWidget(self.bar_chart, 1)

        table_panel = QFrame()
        table_panel.setObjectName("tablePanel")
        table_layout = QVBoxLayout(table_panel)
        table_layout.setContentsMargins(8, 8, 8, 8)
        table_title = QLabel("分类结果明细")
        table_title.setObjectName("sectionTitle")
        table_layout.addWidget(table_title)
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        table_layout.addWidget(self.table, 1)

        splitter = QSplitter()
        splitter.addWidget(chart_container)
        splitter.addWidget(table_panel)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 6)
        root.addWidget(splitter, 1)

    def refresh_columns(self) -> None:
        self.value_combo.clear()
        self.demand_combo.clear()
        self.price_combo.clear()
        df = self.store.dataframe()
        if df is None:
            self.refresh_controls()
            return
        nums = self.store.numeric_columns()
        self.value_combo.addItems(nums)
        self.demand_combo.addItems(nums)
        self.price_combo.addItems(nums)
        for name in ["年消耗金额", "库存金额", "金额", "销售额", "年需求量"]:
            i = self.value_combo.findText(name)
            if i >= 0:
                self.value_combo.setCurrentIndex(i)
                break
        for candidates, combo in [(["年需求量", "需求量"], self.demand_combo), (["单价", "价格"], self.price_combo)]:
            for name in candidates:
                i = combo.findText(name)
                if i >= 0:
                    combo.setCurrentIndex(i)
                    break
        self.refresh_controls()

    def refresh_controls(self) -> None:
        generated = self.mode_combo.currentIndex() == 1
        self.value_combo.setEnabled(not generated)
        self.demand_combo.setEnabled(generated)
        self.price_combo.setEnabled(generated)

    def run_analysis(self) -> None:
        df = self.store.dataframe()
        if df is None:
            QMessageBox.information(self, "提示", "请先在数据中心导入数据。")
            return
        if self.a_spin.value() >= self.b_spin.value():
            QMessageBox.warning(self, "参数错误", "A 类阈值必须小于 B 类阈值。")
            return
        work_df = df.copy()
        try:
            generated = self.mode_combo.currentIndex() == 1
            if generated:
                demand = self.demand_combo.currentText()
                price = self.price_combo.currentText()
                if not demand or not price:
                    raise ValueError("请选择年需求量和单价字段。")
                work_df = ABCAnalyzer.build_consumption_value(work_df, demand, price)
                value_column = "年消耗金额"
                if self.auto_checkbox.isChecked():
                    self.store.df = work_df
                    self.store.data_changed.emit()
            else:
                value_column = self.value_combo.currentText()
                if not value_column:
                    raise ValueError("请选择分析字段。")

            analyzer = ABCAnalyzer(
                work_df,
                value_column,
                self.a_spin.value() / 100,
                self.b_spin.value() / 100,
            )
            result = analyzer.analyze()
            self.result_df = result.dataframe
            self.card_a.set_value(str(result.counts["A"]))
            self.card_b.set_value(str(result.counts["B"]))
            self.card_c.set_value(str(result.counts["C"]))
            self.card_a.set_hint(f"金额贡献 {result.contributions['A']:.2%}")
            self.card_b.set_hint(f"金额贡献 {result.contributions['B']:.2%}")
            self.card_c.set_hint(f"金额贡献 {result.contributions['C']:.2%}")
            labels = ["A 类", "B 类", "C 类"]
            values = [result.counts["A"], result.counts["B"], result.counts["C"]]
            self.pie_chart.draw_abc_pie(labels, values)
            self.bar_chart.draw_abc_bar(labels, values)
            self._refresh_table()
            self.analysis_status.setText("分析完成")
            self.store.set_analysis(
                "abc",
                {
                    "dataframe": self.result_df,
                    "counts": result.counts,
                    "contributions": result.contributions,
                    "value_column": value_column,
                    "a_rate": self.a_spin.value() / 100,
                    "b_rate": self.b_spin.value() / 100,
                },
            )
        except Exception as exc:
            self.analysis_status.setText("分析失败")
            QMessageBox.critical(self, "分析失败", str(exc))

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
                text = f"{float(value):.2%}" if df.columns[c] in {"金额占比", "累计占比"} else str(value)
                self.table.setItem(r, c, QTableWidgetItem(text))
        self.table.resizeColumnsToContents()
        self.table.setSortingEnabled(True)

    def export_result(self) -> None:
        if self.result_df is None:
            QMessageBox.information(self, "提示", "请先完成 ABC 分类分析。")
            return
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "保存 ABC 分类结果",
            "ABC分类结果.xlsx",
            "Excel 文件 (*.xlsx);;CSV 文件 (*.csv)",
        )
        if not filename:
            return
        try:
            export_dataframe(self.result_df, filename)
            QMessageBox.information(self, "导出成功", f"结果已保存：\n{filename}")
        except Exception as exc:
            QMessageBox.critical(self, "导出失败", str(exc))
