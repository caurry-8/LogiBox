import pandas as pd

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QComboBox,
    QDoubleSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QCheckBox,
)

from utils.abc_utils import ABCAnalyzer
from utils.data_store import DataStore
from utils.excel_utils import export_dataframe
from utils.chart_utils import ChartCanvas
from widgets.metric_card import MetricCard


class ABCPage(QWidget):
    def __init__(self, store: DataStore) -> None:
        super().__init__()
        self.store = store
        self.result_df: pd.DataFrame | None = None
        self.last_result = None
        self._build_ui()
        self.store.data_changed.connect(self.refresh_columns)
        self.refresh_columns()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 24, 30, 24)
        root.setSpacing(14)

        title = QLabel('ABC 库存分类 · 专业分析')
        title.setObjectName('pageTitle')
        desc = QLabel(
            '支持直接分析数值字段，或根据“年需求量 × 单价”自动生成年消耗金额。'
        )
        desc.setObjectName('pageDescription')
        root.addWidget(title)
        root.addWidget(desc)

        control = QFrame()
        control.setObjectName('panelCard')
        grid = QGridLayout(control)
        grid.setContentsMargins(18, 16, 18, 16)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            '直接使用现有数值字段',
            '年需求量 × 单价 = 年消耗金额',
        ])
        self.mode_combo.currentIndexChanged.connect(self.refresh_controls)

        self.value_combo = QComboBox()
        self.demand_combo = QComboBox()
        self.price_combo = QComboBox()

        self.a_spin = QDoubleSpinBox()
        self.a_spin.setRange(1.0, 99.0)
        self.a_spin.setValue(80.0)
        self.a_spin.setSuffix(' %')

        self.b_spin = QDoubleSpinBox()
        self.b_spin.setRange(1.0, 99.0)
        self.b_spin.setValue(95.0)
        self.b_spin.setSuffix(' %')

        self.auto_checkbox = QCheckBox('将“年消耗金额”写入共享数据')
        self.auto_checkbox.setChecked(True)

        analyze_button = QPushButton('开始 ABC 分类')
        analyze_button.clicked.connect(self.run_analysis)
        export_button = QPushButton('导出分类结果')
        export_button.clicked.connect(self.export_result)

        grid.addWidget(QLabel('分析模式'), 0, 0)
        grid.addWidget(self.mode_combo, 0, 1, 1, 3)
        grid.addWidget(QLabel('直接分析字段'), 1, 0)
        grid.addWidget(self.value_combo, 1, 1, 1, 3)
        grid.addWidget(QLabel('年需求量'), 2, 0)
        grid.addWidget(self.demand_combo, 2, 1)
        grid.addWidget(QLabel('单价'), 2, 2)
        grid.addWidget(self.price_combo, 2, 3)
        grid.addWidget(QLabel('A 类阈值'), 3, 0)
        grid.addWidget(self.a_spin, 3, 1)
        grid.addWidget(QLabel('B 类阈值'), 3, 2)
        grid.addWidget(self.b_spin, 3, 3)
        grid.addWidget(self.auto_checkbox, 4, 0, 1, 2)

        button_row = QHBoxLayout()
        button_row.addWidget(analyze_button)
        button_row.addWidget(export_button)
        button_row.addStretch()
        grid.addLayout(button_row, 4, 2, 1, 2)

        root.addWidget(control)

        metrics = QGridLayout()
        metrics.setHorizontalSpacing(12)
        self.cardA = MetricCard('A 类', '--', '商品数量 · 金额贡献 --', '#4CAF50')
        self.cardB = MetricCard('B 类', '--', '商品数量 · 金额贡献 --', '#2196F3')
        self.cardC = MetricCard('C 类', '--', '商品数量 · 金额贡献 --', '#FFC107')
        metrics.addWidget(self.cardA, 0, 0)
        metrics.addWidget(self.cardB, 0, 1)
        metrics.addWidget(self.cardC, 0, 2)
        root.addLayout(metrics)

        charts_splitter = QSplitter(Qt.Horizontal)
        charts_splitter.setChildrenCollapsible(False)

        self.pie_card = self._chart_card('ABC 分类占比（金额贡献）')
        self.pie_chart = ChartCanvas()
        self.pie_card.layout().addWidget(self.pie_chart)

        self.bar_card = self._chart_card('ABC 数量统计（SKU 数量）')
        self.bar_chart = ChartCanvas()
        self.bar_card.layout().addWidget(self.bar_chart)

        charts_splitter.addWidget(self.pie_card)
        charts_splitter.addWidget(self.bar_card)
        charts_splitter.setStretchFactor(0, 1)
        charts_splitter.setStretchFactor(1, 1)

        table_card = QFrame()
        table_card.setObjectName('panelCard')
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(14, 12, 14, 12)

        table_title = QLabel('分类结果明细')
        table_title.setObjectName('panelTitle')

        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setDefaultSectionSize(30)
        self.table.horizontalHeader().setStretchLastSection(True)

        table_layout.addWidget(table_title)
        table_layout.addWidget(self.table, 1)

        main_splitter = QSplitter(Qt.Vertical)
        main_splitter.setChildrenCollapsible(False)
        main_splitter.addWidget(charts_splitter)
        main_splitter.addWidget(table_card)
        main_splitter.setStretchFactor(0, 3)
        main_splitter.setStretchFactor(1, 5)
        main_splitter.setSizes([360, 540])

        root.addWidget(main_splitter, 1)

        self._clear_charts()

    def _chart_card(self, title: str) -> QFrame:
        card = QFrame()
        card.setObjectName('chartCard')
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 8)
        title_label = QLabel(title)
        title_label.setObjectName('chartTitle')
        layout.addWidget(title_label)
        return card

    def _clear_charts(self) -> None:
        self.pie_chart.plot_pie(['A 类', 'B 类', 'C 类'], [0, 0, 0], 'ABC 分类占比（金额贡献）')
        self.bar_chart.plot_bar(['A 类', 'B 类', 'C 类'], [0, 0, 0], 'ABC 数量统计（SKU 数量）')

    def refresh_columns(self) -> None:
        self.value_combo.clear()
        self.demand_combo.clear()
        self.price_combo.clear()

        df = self.store.dataframe()
        if df is None:
            self.refresh_controls()
            return

        numeric_columns = []
        for column in df.columns:
            numeric = pd.to_numeric(df[column], errors='coerce')
            if numeric.notna().any():
                numeric_columns.append(str(column))

        self.value_combo.addItems(numeric_columns)
        self.demand_combo.addItems(numeric_columns)
        self.price_combo.addItems(numeric_columns)

        for name in ['年消耗金额', '库存金额', '金额', '销售额', '年需求量']:
            index = self.value_combo.findText(name)
            if index >= 0:
                self.value_combo.setCurrentIndex(index)
                break

        for candidates, combo in [
            (['年需求量', '需求量'], self.demand_combo),
            (['单价', '价格'], self.price_combo),
        ]:
            for name in candidates:
                index = combo.findText(name)
                if index >= 0:
                    combo.setCurrentIndex(index)
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
            QMessageBox.information(self, '提示', '请先在数据中心导入数据。')
            return

        if self.a_spin.value() >= self.b_spin.value():
            QMessageBox.warning(self, '参数错误', 'A 类阈值必须小于 B 类阈值。')
            return

        work_df = df.copy()

        try:
            if self.mode_combo.currentIndex() == 1:
                demand = self.demand_combo.currentText()
                price = self.price_combo.currentText()
                if not demand or not price:
                    raise ValueError('请选择年需求量和单价字段。')

                work_df = ABCAnalyzer.build_consumption_value(work_df, demand, price)
                value_column = '年消耗金额'

                if self.auto_checkbox.isChecked():
                    self.store.replace_dataframe(work_df, '已生成“年消耗金额”，共享数据已更新')
            else:
                value_column = self.value_combo.currentText()
                if not value_column:
                    raise ValueError('请选择分析字段。')

            analyzer = ABCAnalyzer(
                dataframe=work_df,
                value_column=value_column,
                a_rate=self.a_spin.value() / 100,
                b_rate=self.b_spin.value() / 100,
            )

            result = analyzer.analyze()
            self.last_result = result
            self.result_df = result.dataframe

            a_count = result.counts['A']
            b_count = result.counts['B']
            c_count = result.counts['C']
            a_con = result.contributions['A']
            b_con = result.contributions['B']
            c_con = result.contributions['C']

            self.cardA.set_value(a_count)
            self.cardB.set_value(b_count)
            self.cardC.set_value(c_count)
            self.cardA.set_detail(f'数量占比 {a_count / len(self.result_df):.1%} · 金额贡献 {a_con:.1%}')
            self.cardB.set_detail(f'数量占比 {b_count / len(self.result_df):.1%} · 金额贡献 {b_con:.1%}')
            self.cardC.set_detail(f'数量占比 {c_count / len(self.result_df):.1%} · 金额贡献 {c_con:.1%}')

            labels = ['A 类', 'B 类', 'C 类']
            self.pie_chart.plot_pie(
                labels,
                [a_con, b_con, c_con],
                'ABC 分类占比（金额贡献）',
            )
            self.bar_chart.plot_bar(
                labels,
                [a_count, b_count, c_count],
                'ABC 数量统计（SKU 数量）',
            )

            self._refresh_table()

        except Exception as exc:
            QMessageBox.critical(self, '分析失败', str(exc))

    def _refresh_table(self) -> None:
        if self.result_df is None:
            return

        df = self.result_df
        self.table.setSortingEnabled(False)
        self.table.clear()
        self.table.setRowCount(len(df))
        self.table.setColumnCount(len(df.columns))
        self.table.setHorizontalHeaderLabels([str(column) for column in df.columns])

        for row in range(len(df)):
            for col in range(len(df.columns)):
                column = df.columns[col]
                value = df.iat[row, col]

                if column in {'金额占比', '累计占比'}:
                    text = f'{float(value):.2%}'
                elif isinstance(value, float):
                    text = f'{value:,.2f}'
                else:
                    text = str(value)

                item = QTableWidgetItem(text)
                if column == 'ABC分类':
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, item)

        self.table.resizeColumnsToContents()
        self.table.setSortingEnabled(True)

    def export_result(self) -> None:
        if self.result_df is None:
            QMessageBox.information(self, '提示', '请先完成 ABC 分类分析。')
            return

        filename, _ = QFileDialog.getSaveFileName(
            self,
            '保存 ABC 分类结果',
            'ABC分类结果.xlsx',
            'Excel 文件 (*.xlsx);;CSV 文件 (*.csv)',
        )
        if not filename:
            return

        try:
            export_dataframe(self.result_df, filename)
            QMessageBox.information(self, '导出成功', f'结果已保存：\n{filename}')
        except Exception as exc:
            QMessageBox.critical(self, '导出失败', str(exc))
