"""决策工作台页面。

本页面只做展示：全部判断都来自 utils/decision_utils.py 的 DecisionSummary，
文案来自 utils/decision_text.py。**页面内不重复任何决策规则**。

数据来源：DataStore 的原始数据 + analysis_results（abc / xyz / matrix / eoq / safety）。
未参与分类的 SKU 不会出现在决策条目中，也不会被强行归类。
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from utils.data_store import DataStore
from utils.decision_text import (
    describe_blocking,
    describe_focus,
    describe_model_readiness,
    describe_next_actions,
    describe_risk_categories_detail,
    describe_status,
    describe_unclassified,
    describe_item,
    priority_label,
    status_label,
)
from utils.decision_utils import (
    SUMMARY_BLOCKED_BY_QUALITY,
    SUMMARY_READY,
    build_decision_summary,
)
from widgets.metric_card import MetricCard

PLACEHOLDER = "—"

ITEM_COLUMNS = ["SKU", "ABC × XYZ", "优先级", "原因", "建议动作", "价值"]


def _format_value(value) -> str:
    if value is None:
        return PLACEHOLDER
    try:
        return f"{float(value):,.2f}"
    except (TypeError, ValueError):
        return PLACEHOLDER


class DecisionPage(QWidget):
    def __init__(self, store: DataStore) -> None:
        super().__init__()
        self.store = store
        self.summary = None
        self._build_ui()
        self.store.data_changed.connect(self.refresh)
        self.store.analysis_changed.connect(self.refresh)
        self.store.status_changed.connect(self.refresh)
        self.refresh()

    # ------------------------------------------------------------------ 构建

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(34, 28, 34, 22)
        layout.setSpacing(14)

        header = QHBoxLayout()
        header_left = QVBoxLayout()
        header_left.setSpacing(3)

        title = QLabel("决策工作台")
        title.setObjectName("pageTitle")
        description = QLabel(
            "汇总 ABC / XYZ / 交叉矩阵与数据质量，给出需要重点关注的 SKU 与下一步行动。"
        )
        description.setObjectName("pageDescription")
        header_left.addWidget(title)
        header_left.addWidget(description)
        header.addLayout(header_left)
        header.addStretch(1)

        self.status_badge = QLabel("未加载数据")
        self.status_badge.setObjectName("statusBadge")
        header.addWidget(self.status_badge)
        layout.addLayout(header)

        divider = QFrame()
        divider.setObjectName("pageDivider")
        divider.setFixedHeight(1)
        layout.addWidget(divider)

        self.status_note = QLabel("")
        self.status_note.setObjectName("analysisNote")
        self.status_note.setWordWrap(True)
        layout.addWidget(self.status_note)

        overview_header = QHBoxLayout()
        overview_title = QLabel("决策总览")
        overview_title.setObjectName("sectionTitle")
        overview_header.addWidget(overview_title)
        overview_header.addStretch(1)
        self.overview_note = QLabel("")
        self.overview_note.setObjectName("mutedLabel")
        overview_header.addWidget(self.overview_note)
        layout.addLayout(overview_header)

        metrics = QGridLayout()
        metrics.setHorizontalSpacing(12)
        metrics.setVerticalSpacing(12)
        self.card_high = MetricCard("高优先级", PLACEHOLDER, "#f85149", "需要优先安排处理")
        self.card_medium = MetricCard("中优先级", PLACEHOLDER, "#d29922", "需要持续监控")
        self.card_normal = MetricCard("一般关注", PLACEHOLDER, "#3fb950", "按常规节奏管理")
        self.card_risk = MetricCard("数据风险", PLACEHOLDER, "#8b949e", "未参与分类的 SKU")
        metrics.addWidget(self.card_high, 0, 0)
        metrics.addWidget(self.card_medium, 0, 1)
        metrics.addWidget(self.card_normal, 0, 2)
        metrics.addWidget(self.card_risk, 0, 3)
        layout.addLayout(metrics)

        layout.addWidget(self._build_items_panel(), 3)

        bottom = QHBoxLayout()
        bottom.setSpacing(14)
        bottom.addWidget(self._build_risk_panel(), 1)
        bottom.addWidget(self._build_actions_panel(), 1)
        layout.addLayout(bottom, 2)

    def _build_items_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("tablePanel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(16, 14, 16, 16)
        panel_layout.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("重点关注列表")
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch(1)
        self.items_note = QLabel("")
        self.items_note.setObjectName("mutedLabel")
        header.addWidget(self.items_note)
        panel_layout.addLayout(header)

        self.items_table = QTableWidget()
        self.items_table.setColumnCount(len(ITEM_COLUMNS))
        self.items_table.setHorizontalHeaderLabels(ITEM_COLUMNS)
        self.items_table.setAlternatingRowColors(True)
        self.items_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.items_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.items_table.verticalHeader().setVisible(False)
        self.items_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeToContents
        )
        for column in range(1, len(ITEM_COLUMNS) - 1):
            self.items_table.horizontalHeader().setSectionResizeMode(
                column, QHeaderView.Stretch
            )
        self.items_table.horizontalHeader().setSectionResizeMode(
            len(ITEM_COLUMNS) - 1, QHeaderView.ResizeToContents
        )
        panel_layout.addWidget(self.items_table, 1)
        return panel

    def _build_risk_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("contentPanel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(18, 16, 18, 18)
        panel_layout.setSpacing(8)

        title = QLabel("风险集中")
        title.setObjectName("sectionTitle")
        panel_layout.addWidget(title)

        self.risk_note = QLabel("")
        self.risk_note.setObjectName("analysisNote")
        self.risk_note.setWordWrap(True)
        panel_layout.addWidget(self.risk_note)
        panel_layout.addStretch(1)
        return panel

    def _build_actions_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("contentPanel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(18, 16, 18, 18)
        panel_layout.setSpacing(8)

        title = QLabel("下一步行动")
        title.setObjectName("sectionTitle")
        panel_layout.addWidget(title)

        self.actions_note = QLabel("")
        self.actions_note.setObjectName("analysisNote")
        self.actions_note.setWordWrap(True)
        panel_layout.addWidget(self.actions_note)

        self.model_note = QLabel("")
        self.model_note.setObjectName("mutedLabel")
        self.model_note.setWordWrap(True)
        panel_layout.addWidget(self.model_note)
        panel_layout.addStretch(1)
        return panel

    # ------------------------------------------------------------------ 刷新

    def refresh(self) -> None:
        summary = build_decision_summary(
            self.store.dataframe(), self.store.analysis_results
        )
        self.summary = summary
        self._apply_status(summary)
        self._apply_overview(summary)
        self._apply_items(summary)
        self._apply_risk(summary)
        self._apply_actions(summary)

    def _apply_status(self, summary) -> None:
        self.status_badge.setText(status_label(summary.status))
        ready = summary.status == SUMMARY_READY
        self.status_badge.setProperty("ready", "true" if ready else "false")
        self.status_badge.setProperty(
            "state",
            "blocker" if summary.status == SUMMARY_BLOCKED_BY_QUALITY else "normal",
        )
        self._repolish(self.status_badge)

        lines = [describe_status(summary)]
        blocking = describe_blocking(summary)
        if blocking:
            lines.append("原因：" + "；".join(blocking))
        unclassified = describe_unclassified(summary)
        if unclassified:
            lines.append(unclassified)
        self.status_note.setText("\n".join(lines))
        self.status_note.setProperty("warn", "false" if ready else "true")
        self._repolish(self.status_note)

    def _apply_overview(self, summary) -> None:
        ready = summary.status == SUMMARY_READY
        counts = (
            (
                summary.high_priority_count,
                summary.medium_priority_count,
                summary.normal_priority_count,
                summary.unclassified_sku_count,
            )
            if ready
            else (None, None, None, None)
        )
        high, medium, normal, risk = counts
        self.card_high.set_value(PLACEHOLDER if high is None else str(high))
        self.card_medium.set_value(PLACEHOLDER if medium is None else str(medium))
        self.card_normal.set_value(PLACEHOLDER if normal is None else str(normal))
        self.card_risk.set_value(PLACEHOLDER if risk is None else str(risk))
        self.overview_note.setText(describe_focus(summary) if ready else "")

    def _apply_items(self, summary) -> None:
        items = summary.priority_items if summary.status == SUMMARY_READY else []
        self.items_table.setRowCount(len(items))
        for row, item in enumerate(items):
            reason, action = describe_item(item)
            values = [
                item.sku,
                item.matrix_category,
                priority_label(item.priority),
                reason,
                action,
                _format_value(item.value),
            ]
            for column, text in enumerate(values):
                cell = QTableWidgetItem(str(text))
                if column == len(ITEM_COLUMNS) - 1:
                    cell.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.items_table.setItem(row, column, cell)

        if summary.status != SUMMARY_READY:
            self.items_note.setText("分析未就绪，暂无决策条目")
        elif not items:
            self.items_note.setText("当前没有需要重点关注的 SKU")
        else:
            self.items_note.setText(f"共 {summary.focus_count} 个需要关注")

    def _apply_risk(self, summary) -> None:
        if summary.status != SUMMARY_READY:
            self.risk_note.setText("分析未就绪，暂无法判断风险集中情况。")
            return
        lines = describe_risk_categories_detail(summary)
        self.risk_note.setText("\n".join(lines) if lines else "暂无集中的风险单元。")

    def _apply_actions(self, summary) -> None:
        actions = describe_next_actions(summary)
        self.actions_note.setText(
            "\n".join(f"· {text}" for text in actions) if actions else "暂无建议。"
        )
        self.model_note.setText(describe_model_readiness(summary))

    @staticmethod
    def _repolish(widget) -> None:
        widget.style().unpolish(widget)
        widget.style().polish(widget)
