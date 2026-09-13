import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from utils.chart_utils import ChartCanvas
from utils.data_store import DataStore
from utils.excel_utils import export_dataframe
from utils.matrix_utils import (
    ABC_ORDER,
    ABCXYZMatrixAnalyzer,
    CELL_ORDER,
    MatrixResult,
    XYZ_ORDER,
)
from utils.quality_text import excluded_reason_text
from widgets.metric_card import MetricCard

CELL_BAR_COLORS = [
    "#28C7FA",
    "#4FB8E8",
    "#6C7BFF",
    "#7C8CFF",
    "#A970FF",
    "#B98CFF",
    "#FFB86B",
    "#FF9A76",
    "#FF6B8A",
]


class MatrixPage(QWidget):
    """ABC x XYZ cross matrix for differentiated inventory strategy."""

    def __init__(self, store: DataStore) -> None:
        super().__init__()
        self.store = store
        self.result: MatrixResult | None = None
        self.selected_cell: str | None = None
        self._build_ui()
        self.store.data_changed.connect(self.refresh_columns)
        self.store.analysis_changed.connect(self.refresh_status)
        self.refresh_columns()
        self.refresh_status()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(34, 28, 34, 22)
        root.setSpacing(14)

        header = QHBoxLayout()
        left = QVBoxLayout()
        left.setSpacing(2)
        title = QLabel("ABC × XYZ 交叉矩阵")
        title.setObjectName("pageTitle")
        desc = QLabel("把价值贡献与需求稳定性组合成 3×3 矩阵，为每一类库存匹配差异化的补货与监控策略。")
        desc.setObjectName("pageDescription")
        left.addWidget(title)
        left.addWidget(desc)
        header.addLayout(left)
        header.addStretch()
        self.status = QLabel("待分析")
        self.status.setObjectName("statusBadge")
        header.addWidget(self.status)
        root.addLayout(header)

        self.hint = QLabel("")
        self.hint.setObjectName("matrixHint")
        self.hint.setWordWrap(True)
        root.addWidget(self.hint)

        self.selection_label = QLabel("点击矩阵单元格可查看对应 SKU 明细。")
        self.selection_label.setObjectName("mutedLabel")
        root.addWidget(self.selection_label)

        controls = QFrame()
        controls.setObjectName("controlBar")
        grid = QGridLayout(controls)
        grid.setContentsMargins(16, 12, 16, 12)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)

        self.key_combo = QComboBox()
        self.value_combo = QComboBox()
        analyze_button = QPushButton("生成交叉矩阵")
        analyze_button.clicked.connect(self.run_analysis)
        export_button = QPushButton("导出结果")
        export_button.setObjectName("secondaryButton")
        export_button.clicked.connect(self.export_result)

        grid.addWidget(QLabel("关键字段"), 0, 0)
        grid.addWidget(self.key_combo, 0, 1)
        grid.addWidget(QLabel("价值字段"), 0, 2)
        grid.addWidget(self.value_combo, 0, 3)
        buttons = QHBoxLayout()
        buttons.addWidget(analyze_button)
        buttons.addWidget(export_button)
        buttons.addStretch()
        grid.addLayout(buttons, 0, 4)
        root.addWidget(controls)

        metrics = QHBoxLayout()
        metrics.setSpacing(12)
        self.card_matched = MetricCard("匹配 SKU", "--", "#28C7FA", "ABC 与 XYZ 成功对应")
        self.card_high = MetricCard("A 类 SKU", "--", "#6C7BFF", "高价值重点物料")
        self.card_risk = MetricCard("AZ 高风险", "--", "#FF6B8A", "高价值且需求不稳定")
        self.card_coverage = MetricCard("矩阵覆盖", "--", "#64D8CB", "有库存分布的单元数")
        for card in (self.card_matched, self.card_high, self.card_risk, self.card_coverage):
            metrics.addWidget(card)
        root.addLayout(metrics)

        self.coverage_label = QLabel("生成矩阵后显示分析覆盖情况。")
        self.coverage_label.setObjectName("analysisNote")
        self.coverage_label.setWordWrap(True)
        root.addWidget(self.coverage_label)

        charts = QFrame()
        charts.setObjectName("chartPanel")
        chart_layout = QHBoxLayout(charts)
        chart_layout.setContentsMargins(8, 8, 8, 8)
        chart_layout.setSpacing(8)
        self.heatmap = ChartCanvas()
        self.heatmap.setCursor(Qt.PointingHandCursor)
        self.heatmap.mpl_connect("button_press_event", self._on_heatmap_click)
        self.value_chart = ChartCanvas()
        chart_layout.addWidget(self.heatmap, 3)
        chart_layout.addWidget(self.value_chart, 2)

        strategy_panel = QFrame()
        strategy_panel.setObjectName("tablePanel")
        strategy_layout = QVBoxLayout(strategy_panel)
        strategy_layout.setContentsMargins(10, 10, 10, 10)
        self.strategy_table = QTableWidget()
        self.strategy_table.setAlternatingRowColors(True)
        self.strategy_table.setWordWrap(True)
        self.strategy_table.setColumnCount(8)
        self.strategy_table.setHorizontalHeaderLabels(
            ["单元", "SKU 数量", "SKU 占比", "分析金额", "金额占比", "优先级", "定位", "管理策略"]
        )
        self.strategy_table.verticalHeader().setVisible(False)
        strategy_layout.addWidget(self.strategy_table, 1)

        detail_panel = QFrame()
        detail_panel.setObjectName("tablePanel")
        detail_layout = QVBoxLayout(detail_panel)
        detail_layout.setContentsMargins(10, 10, 10, 10)
        self.detail_table = QTableWidget()
        self.detail_table.setAlternatingRowColors(True)
        self.detail_table.setSortingEnabled(True)
        detail_layout.addWidget(self.detail_table, 1)

        # 两张表内容都较长，用选项卡各占整宽整高，避免被压成只能看到一两行
        self.table_tabs = QTabWidget()
        self.table_tabs.setObjectName("matrixTabs")
        self.table_tabs.addTab(strategy_panel, "单元策略建议")
        self.table_tabs.addTab(detail_panel, "SKU 明细")

        content_split = QSplitter(Qt.Vertical)
        content_split.addWidget(charts)
        content_split.addWidget(self.table_tabs)
        content_split.setStretchFactor(0, 3)
        content_split.setStretchFactor(1, 4)
        # 图表和策略表都需要可见空间，给定初始分配避免策略表只露出一两行
        content_split.setSizes([250, 340])
        root.addWidget(content_split, 1)

        self._render_placeholder()

    # ------------------------------------------------------------------ state

    def refresh_status(self, *_args) -> None:
        abc = self.store.get_analysis("abc")
        xyz = self.store.get_analysis("xyz")
        if abc and xyz:
            self.hint.setText("ABC 与 XYZ 分析均已就绪，可生成交叉矩阵。")
            self.hint.setProperty("ready", True)
        else:
            missing = []
            if not abc:
                missing.append("ABC 分类")
            if not xyz:
                missing.append("XYZ 分析")
            self.hint.setText(
                "请先完成 " + " 与 ".join(missing) + " 分析，再生成交叉矩阵。"
            )
            self.hint.setProperty("ready", False)
        self.hint.style().unpolish(self.hint)
        self.hint.style().polish(self.hint)
        self.refresh_columns()

    def refresh_columns(self) -> None:
        abc = self.store.get_analysis("abc")
        xyz = self.store.get_analysis("xyz")

        self.key_combo.clear()
        self.value_combo.clear()

        if not abc or not xyz:
            return

        abc_df = abc.get("dataframe")
        xyz_df = xyz.get("dataframe")
        if abc_df is None or xyz_df is None:
            return

        shared = [str(c) for c in abc_df.columns if c in set(xyz_df.columns)]
        if shared:
            self.key_combo.addItems(shared)
            recommended = ABCXYZMatrixAnalyzer.recommend_key_column(shared)
            index = self.key_combo.findText(recommended)
            if index >= 0:
                self.key_combo.setCurrentIndex(index)

        value_column = str(abc.get("value_column", "") or "")
        numeric = self.store.numeric_columns()
        candidates: list[str] = []
        if value_column:
            candidates.append(value_column)
        for name in numeric:
            if name not in candidates:
                candidates.append(name)
        if candidates:
            self.value_combo.addItems(candidates)

    def _render_placeholder(self) -> None:
        self.heatmap.show_empty("等待生成交叉矩阵")
        self.value_chart.show_empty("等待生成交叉矩阵")
        self.strategy_table.setRowCount(0)
        self.detail_table.setRowCount(0)
        self.detail_table.setColumnCount(0)
        self.coverage_label.setText("生成矩阵后显示分析覆盖情况。")

    # ---------------------------------------------------------------- analysis

    def run_analysis(self) -> None:
        abc = self.store.get_analysis("abc")
        xyz = self.store.get_analysis("xyz")
        if not abc or not xyz:
            QMessageBox.information(self, "提示", "请先完成 ABC 与 XYZ 分析。")
            return

        abc_df = abc.get("dataframe")
        xyz_df = xyz.get("dataframe")
        if abc_df is None or xyz_df is None:
            QMessageBox.warning(self, "无法分析", "分析结果缺少明细数据，请重新运行 ABC 与 XYZ 分析。")
            return

        key_column = self.key_combo.currentText().strip()
        if not key_column:
            QMessageBox.warning(self, "参数错误", "请选择用于匹配的关键字段。")
            return

        value_column = self.value_combo.currentText().strip()

        try:
            result = ABCXYZMatrixAnalyzer(
                abc_df,
                xyz_df,
                key_column=key_column,
                value_column=value_column,
            ).analyze()
        except Exception as exc:
            self.status.setText("分析失败")
            QMessageBox.critical(self, "分析失败", str(exc))
            return

        self.result = result
        self.selected_cell = None
        self._update_metrics(result)
        self._draw_charts(result)
        self._fill_strategy_table(result)
        self._fill_detail_table(result)
        self.coverage_label.setText(self._coverage_text(result))
        self.selection_label.setText(
            "矩阵已生成：点击热力图中的 AX、AY、AZ 等单元格，可筛选并查看对应 SKU 明细。"
        )
        self.status.setText("分析完成")
        self.store.set_analysis(
            "matrix",
            {
                "dataframe": result.dataframe,
                "cell_counts": result.cell_counts,
                "cell_values": result.cell_values,
                "cell_amounts": result.cell_amounts,
                "cell_sku_shares": result.cell_sku_shares,
                "key_column": result.key_column,
                "value_column": result.value_column,
                "total_value": result.total_value,
                "input_sku_count": result.input_sku_count,
                "excluded_sku_count": result.excluded_sku_count,
                "excluded_by_quality": result.excluded_by_quality,
            },
        )

    def _update_metrics(self, result: MatrixResult) -> None:
        matched = int(len(result.dataframe))
        high = sum(result.cell_counts.get(f"A{x}", 0) for x in XYZ_ORDER)
        risk = result.cell_counts.get("AZ", 0)
        coverage = sum(1 for cell in CELL_ORDER if result.cell_counts.get(cell, 0) > 0)
        self.card_matched.set_value(str(matched))
        self.card_high.set_value(str(high))
        self.card_risk.set_value(str(risk))
        self.card_coverage.set_value(f"{coverage} / 9")

    @staticmethod
    def _coverage_text(result: MatrixResult) -> str:
        """矩阵覆盖说明：参与数量、未参与数量与原因、占比口径。"""
        analyzed = result.analyzed_sku_count
        total = result.input_sku_count
        lines = [
            f"矩阵分析覆盖：有效 SKU {analyzed} / 总 SKU {total}"
            f"（覆盖率 {result.coverage_rate:.1%}）"
        ]
        if result.has_exclusions:
            reason = excluded_reason_text(result.excluded_by_quality)
            detail = f"未参与矩阵分析 {result.excluded_sku_count} 个 SKU"
            detail += f"（{reason}）" if reason else "（原因：数据质量问题）"
            lines.append(detail)
        else:
            lines.append("全部 SKU 均已参与矩阵分析。")
        lines.append("矩阵占比基于已参与分析的 SKU。")
        return "\n".join(lines)

    def _draw_charts(self, result: MatrixResult) -> None:
        matrix = [
            [result.cell_counts.get(f"{a}{x}", 0) for x in XYZ_ORDER]
            for a in ABC_ORDER
        ]
        value_labels = [
            [
                f"{result.cell_counts.get(f'{a}{x}', 0)} SKU\n{result.cell_sku_shares.get(f'{a}{x}', 0):.1%}"
                for x in XYZ_ORDER
            ]
            for a in ABC_ORDER
        ]
        selected_position: tuple[int, int] | None = None
        if self.selected_cell and len(self.selected_cell) == 2:
            selected_position = (
                ABC_ORDER.index(self.selected_cell[0]),
                XYZ_ORDER.index(self.selected_cell[1]),
            )
        self.heatmap.draw_matrix_heatmap(
            row_labels=["A 类", "B 类", "C 类"],
            column_labels=["X 稳定", "Y 波动", "Z 不稳定"],
            matrix=matrix,
            title="ABC × XYZ 单元 SKU 数量 / 占比（点击查看明细）",
            value_labels=value_labels,
            selected_cell=selected_position,
        )

        labels = list(CELL_ORDER)
        values = [result.cell_values.get(cell, 0.0) for cell in labels]
        if result.has_amount:
            title = f"各单元 {result.value_label}占比"
            ylabel = f"{result.value_label}占比"
        else:
            title = "各单元 SKU 占比"
            ylabel = "SKU 占比"
            values = [result.cell_sku_shares.get(cell, 0.0) for cell in labels]
        self.value_chart.draw_bar_chart(
            labels,
            values,
            title=title,
            ylabel=ylabel,
            colors=CELL_BAR_COLORS,
            percent=True,
        )

    def _fill_strategy_table(self, result: MatrixResult) -> None:
        table = self.strategy_table
        table.setSortingEnabled(False)
        table.clearContents()
        headers = ["单元", "SKU 数量", "SKU 占比"]
        if result.has_amount:
            headers.extend([result.value_label, f"{result.value_label}占比"])
        headers.extend(["优先级", "定位", "库存管理建议"])
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setRowCount(len(CELL_ORDER))

        for row, cell in enumerate(CELL_ORDER):
            strategy = result.strategies[cell]
            items = [
                cell,
                str(result.cell_counts.get(cell, 0)),
                f"{result.cell_sku_shares.get(cell, 0.0):.1%}",
            ]
            if result.has_amount:
                items.extend(
                    [
                        f"{result.cell_amounts.get(cell, 0.0):,.2f}",
                        f"{result.cell_values.get(cell, 0.0):.1%}",
                    ]
                )
            items.extend([strategy["priority"], strategy["title"], strategy["action"]])
            for column, text in enumerate(items):
                table.setItem(row, column, QTableWidgetItem(text))

        header = table.horizontalHeader()
        for column in range(len(headers) - 1):
            header.setSectionResizeMode(column, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(len(headers) - 1, QHeaderView.Stretch)
        table.resizeRowsToContents()
        table.setSortingEnabled(False)

    def _detail_columns(self, dataframe: pd.DataFrame, result: MatrixResult) -> list[str]:
        """仅显示实际存在的专业字段；没有的字段绝不伪造。"""
        candidates = [
            result.key_column,
            "商品名称",
            "商品名",
            "物料名称",
            "品名",
            "名称",
            "年需求量",
            "需求量",
            "库存数量",
            "库存量",
            "现存量",
            "库存金额",
            "库存价值",
            "库存成本",
            result.value_column,
            "ABC分类",
            "XYZ分类",
            "矩阵单元",
            "变异系数CV",
            "SKU占比",
            "金额占比",
        ]
        columns: list[str] = []
        for column in candidates:
            if column and column in dataframe.columns and column not in columns:
                columns.append(column)
        return columns or [str(column) for column in dataframe.columns]

    def _fill_detail_table(self, result: MatrixResult, cell: str | None = None) -> None:
        df = result.dataframe
        if cell:
            df = df[df["矩阵单元"] == cell].copy()

        columns = self._detail_columns(df, result)
        table = self.detail_table
        table.setSortingEnabled(False)
        table.clear()
        table.setRowCount(len(df))
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)
        percent_columns = {"SKU占比", "金额占比"}
        for r in range(len(df)):
            for c, column in enumerate(columns):
                value = df.iloc[r][column]
                if column in percent_columns:
                    text = f"{float(value):.2%}"
                elif pd.isna(value):
                    text = ""
                else:
                    text = str(value)
                table.setItem(r, c, QTableWidgetItem(text))
        table.resizeColumnsToContents()
        table.setSortingEnabled(True)

    def _on_heatmap_click(self, event) -> None:
        """点击热力图单元格后，筛选当前单元的 SKU 明细并切换到明细标签页。"""
        if self.result is None or event.inaxes is not self.heatmap.axes:
            return
        if event.xdata is None or event.ydata is None:
            return
        column = int(round(event.xdata))
        row = int(round(event.ydata))
        if not (0 <= row < len(ABC_ORDER) and 0 <= column < len(XYZ_ORDER)):
            return

        self.selected_cell = f"{ABC_ORDER[row]}{XYZ_ORDER[column]}"
        count = self.result.cell_counts.get(self.selected_cell, 0)
        sku_share = self.result.cell_sku_shares.get(self.selected_cell, 0.0)
        strategy = self.result.strategies[self.selected_cell]
        detail = f"已选择 {self.selected_cell}：{count} 个 SKU，占全部 SKU 的 {sku_share:.1%}。"
        if self.result.has_amount:
            detail += (
                f" {self.result.value_label} {self.result.cell_amounts.get(self.selected_cell, 0.0):,.2f}，"
                f"占比 {self.result.cell_values.get(self.selected_cell, 0.0):.1%}。"
            )
        self.selection_label.setText(f"{detail} 建议：{strategy['action']}")
        self._draw_charts(self.result)
        self._fill_detail_table(self.result, self.selected_cell)
        self.table_tabs.setCurrentIndex(1)

    # ------------------------------------------------------------------ export

    def export_result(self) -> None:
        if self.result is None:
            QMessageBox.information(self, "提示", "请先生成交叉矩阵。")
            return
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "保存 ABC × XYZ 交叉矩阵结果",
            "ABC_XYZ交叉矩阵.xlsx",
            "Excel 文件 (*.xlsx);;CSV 文件 (*.csv)",
        )
        if not filename:
            return

        try:
            detail = self.result.dataframe
            summary = pd.DataFrame(
                [
                    {
                        "矩阵单元": cell,
                        "SKU 数量": self.result.cell_counts.get(cell, 0),
                        "金额占比": round(self.result.cell_values.get(cell, 0.0), 6),
                        "优先级": self.result.strategies[cell]["priority"],
                        "定位": self.result.strategies[cell]["title"],
                        "管理策略": self.result.strategies[cell]["action"],
                        "关注指标": self.result.strategies[cell]["target"],
                    }
                    for cell in CELL_ORDER
                ]
            )

            if filename.lower().endswith(".csv"):
                export_dataframe(detail, filename)
                summary.to_csv(
                    filename.replace(".csv", "_策略汇总.csv"),
                    index=False,
                    encoding="utf-8-sig",
                )
            else:
                with pd.ExcelWriter(filename, engine="openpyxl") as writer:
                    detail.to_excel(writer, sheet_name="SKU明细", index=False)
                    summary.to_excel(writer, sheet_name="单元策略", index=False)

            QMessageBox.information(self, "导出成功", f"结果已保存：\n{filename}")
        except Exception as exc:
            QMessageBox.critical(self, "导出失败", str(exc))
