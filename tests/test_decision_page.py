"""决策工作台页面的回归测试（V3.5.0-A-04.2）。

覆盖五种核心状态：未导入 / 分析不足 / 质量 BLOCKER / 正常数据 / 模型未就绪，
以及页面是否正确消费 DecisionSummary（而不是在 UI 层重算规则）。

页面只做展示，因此这里的断言集中在「显示内容是否来自 decision_utils / decision_text」。
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from PySide6.QtWidgets import QTableWidgetItem

from pages.decision_page import ITEM_COLUMNS, PLACEHOLDER, DecisionPage
from utils.abc_utils import ABCAnalyzer
from utils.data_store import DataStore
from utils.decision_text import (
    describe_focus,
    describe_next_actions,
    describe_risk_categories_detail,
    priority_label,
)
from utils.decision_utils import SUMMARY_READY, build_decision_summary
from utils.matrix_utils import ABCXYZMatrixAnalyzer
from utils.xyz_utils import XYZAnalyzer

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PERIODS = ["1月", "2月", "3月", "4月"]


def _dataset(missing_period_for: str | None = None, blank_key_for: str | None = None) -> pd.DataFrame:
    rows = {
        "S1": (300.0, [10, 50, 20, 60]),     # A + Z = AZ
        "S2": (200.0, [100, 120, 80, 100]),  # A + Y = AY
        "S3": (150.0, [100, 100, 100, 100]),  # A + X = AX
        "S4": (100.0, [50, 50, 50, 50]),     # B + X = BX
        "S5": (50.0, [50, 60, 70, 60]),      # C + Y = CY
        "S6": (20.0, [20, 20, 20, 20]),      # C + X = CX
    }
    records = []
    for sku, (value, periods) in rows.items():
        periods = list(periods)
        if missing_period_for == sku:
            periods[1] = None
        records.append(
            {
                "SKU": None if blank_key_for == sku else sku,
                "年消耗金额": value,
                "1月": periods[0],
                "2月": periods[1],
                "3月": periods[2],
                "4月": periods[3],
            }
        )
    return pd.DataFrame(records)


def _fill_analyses(store: DataStore, dataframe: pd.DataFrame, with_models: bool = False) -> None:
    abc = ABCAnalyzer(dataframe, "年消耗金额").analyze()
    xyz = XYZAnalyzer(dataframe, PERIODS).analyze()
    matrix = ABCXYZMatrixAnalyzer(
        abc.dataframe, xyz.dataframe, key_column="SKU", value_column="年消耗金额"
    ).analyze()
    store.set_analysis(
        "abc",
        {
            "dataframe": abc.dataframe,
            "counts": abc.counts,
            "contributions": abc.contributions,
            "value_column": "年消耗金额",
        },
    )
    store.set_analysis(
        "xyz",
        {
            "dataframe": xyz.dataframe,
            "counts": xyz.counts,
            "mean_cv": xyz.mean_cv,
            "status_counts": xyz.status_counts,
            "total_count": xyz.total_count,
            "period_columns": PERIODS,
            "field_semantics": "ok",
        },
    )
    store.set_analysis(
        "matrix",
        {
            "dataframe": matrix.dataframe,
            "cell_counts": matrix.cell_counts,
            "key_column": matrix.key_column,
            "value_column": matrix.value_column,
        },
    )
    if with_models:
        store.set_analysis("eoq", {"EOQ": 894.43, "总成本": 4472.14})
        store.set_analysis("safety", {"安全库存": 73.79, "再订货点 ROP": 573.79})


def _store(dataframe: pd.DataFrame | None, with_analyses: bool = True, with_models: bool = False) -> DataStore:
    store = DataStore()
    if dataframe is not None:
        store.df = dataframe
        store.filename = "decision_test.csv"
    if with_analyses and dataframe is not None:
        _fill_analyses(store, dataframe, with_models=with_models)
    return store


def _cell(table, row: int, column: int) -> str:
    item = table.item(row, column)
    return "" if item is None else item.text()


def _lines(label) -> list[str]:
    text = label.text()
    return [line for line in text.split("\n") if line] if text else []


# --------------------------------------------------------------------------- #
# 一、页面注册
# --------------------------------------------------------------------------- #


def test_decision_page_is_registered():
    from ui.main_window import MainWindow

    window = MainWindow(base_dir=PROJECT_ROOT)
    try:
        index = window.page_index("decision")
        assert index >= 0
        assert isinstance(window.pages[index], DecisionPage)
        assert window.page_definitions[index].nav_label == "决策工作台"
        assert window.page_definitions[index].section == "决策"
    finally:
        window.close()


def test_existing_pages_still_registered():
    from ui.main_window import MainWindow

    window = MainWindow(base_dir=PROJECT_ROOT)
    try:
        for key in ("dashboard", "data_center", "abc", "xyz", "matrix", "safety", "eoq", "report", "about"):
            assert window.page_index(key) >= 0, key
        assert window.stack.count() == len(window.page_definitions)
    finally:
        window.close()


# --------------------------------------------------------------------------- #
# 二、状态 1：未导入数据
# --------------------------------------------------------------------------- #


def test_no_data_state():
    page = DecisionPage(_store(None))

    assert page.status_badge.text() == "无数据"
    assert "尚未导入数据" in page.status_note.text()
    for card in (page.card_high, page.card_medium, page.card_normal, page.card_risk):
        assert card.value_label.text() == PLACEHOLDER
    assert page.items_table.rowCount() == 0
    assert page.items_note.text() == "分析未就绪，暂无决策条目"
    assert "导入库存数据" in page.actions_note.text()


# --------------------------------------------------------------------------- #
# 三、状态 2：分析不足
# --------------------------------------------------------------------------- #


def test_missing_analysis_state():
    page = DecisionPage(_store(_dataset(), with_analyses=False))

    assert page.status_badge.text() == "分析未就绪"
    assert "尚未完成 ABC 分类" in page.status_note.text()
    assert "尚未生成 ABC × XYZ 交叉矩阵" in page.status_note.text()
    assert page.items_table.rowCount() == 0
    assert "补齐缺失的分析" in page.actions_note.text()
    assert page.model_note.text() == ""


def test_partial_analysis_state():
    store = _store(_dataset(), with_analyses=False)
    dataframe = store.dataframe()
    abc = ABCAnalyzer(dataframe, "年消耗金额").analyze()
    store.set_analysis("abc", {"dataframe": abc.dataframe, "counts": abc.counts})

    page = DecisionPage(store)

    assert page.status_badge.text() == "分析未就绪"
    assert "尚未完成 XYZ 稳定性分析" in page.status_note.text()
    assert "尚未生成 ABC × XYZ 交叉矩阵" in page.status_note.text()


# --------------------------------------------------------------------------- #
# 四、状态 3：数据质量 BLOCKER
# --------------------------------------------------------------------------- #


def test_quality_blocker_state():
    dataframe = _dataset(blank_key_for="S1")
    page = DecisionPage(_store(dataframe))

    assert page.status_badge.text() == "数据不可靠"
    assert "数据质量存在阻断问题" in page.status_note.text()
    assert page.status_badge.property("state") == "blocker"


def test_quality_blocker_generates_no_items():
    dataframe = _dataset(blank_key_for="S1")
    page = DecisionPage(_store(dataframe))

    assert page.items_table.rowCount() == 0
    assert page.items_note.text() == "分析未就绪，暂无决策条目"
    for card in (page.card_high, page.card_medium, page.card_normal, page.card_risk):
        assert card.value_label.text() == PLACEHOLDER


# --------------------------------------------------------------------------- #
# 五、状态 4：正常数据
# --------------------------------------------------------------------------- #


def test_ready_state_badge_and_overview():
    store = _store(_dataset(), with_models=True)
    page = DecisionPage(store)
    summary = build_decision_summary(store.dataframe(), store.analysis_results)

    assert page.status_badge.text() == "可决策"
    assert page.status_badge.property("ready") == "true"
    assert page.card_high.value_label.text() == str(summary.high_priority_count)
    assert page.card_medium.value_label.text() == str(summary.medium_priority_count)
    assert page.card_normal.value_label.text() == str(summary.normal_priority_count)
    assert page.card_risk.value_label.text() == str(summary.unclassified_sku_count)
    assert page.overview_note.text() == describe_focus(summary)


def test_items_table_columns():
    page = DecisionPage(_store(_dataset()))

    assert page.items_table.columnCount() == len(ITEM_COLUMNS)
    labels = [
        page.items_table.horizontalHeaderItem(i).text()
        for i in range(page.items_table.columnCount())
    ]
    assert labels == ITEM_COLUMNS
    assert labels == ["SKU", "ABC × XYZ", "优先级", "原因", "建议动作", "价值"]


def test_items_table_matches_decision_summary():
    store = _store(_dataset())
    page = DecisionPage(store)
    summary = build_decision_summary(store.dataframe(), store.analysis_results)

    assert page.items_table.rowCount() == len(summary.priority_items)
    for row, item in enumerate(summary.priority_items):
        assert _cell(page.items_table, row, 0) == item.sku
        assert _cell(page.items_table, row, 1) == item.matrix_category
        assert _cell(page.items_table, row, 2) == priority_label(item.priority)


def test_first_row_content():
    page = DecisionPage(_store(_dataset()))

    assert page.items_table.rowCount() == 4
    assert _cell(page.items_table, 0, 0) == "S1"
    assert _cell(page.items_table, 0, 1) == "AZ"
    assert _cell(page.items_table, 0, 2) == "高优先级"
    assert "高价值" in _cell(page.items_table, 0, 3)
    assert "安全库存" in _cell(page.items_table, 0, 4)
    assert _cell(page.items_table, 0, 5) == "300.00"


def test_value_column_uses_thousands_separator():
    """等比例放大金额（保持 ABC 比例不变），验证千分位格式。"""
    dataframe = _dataset()
    dataframe["年消耗金额"] = dataframe["年消耗金额"] * 1000
    page = DecisionPage(_store(dataframe))

    values = [
        _cell(page.items_table, row, 5) for row in range(page.items_table.rowCount())
    ]
    assert page.items_table.rowCount() == 4
    assert "300,000.00" in values
    assert _cell(page.items_table, 0, 5) == "300,000.00"


def test_items_note_reports_focus_count():
    store = _store(_dataset())
    page = DecisionPage(store)
    summary = build_decision_summary(store.dataframe(), store.analysis_results)

    assert page.items_note.text() == f"共 {summary.focus_count} 个需要关注"


def test_risk_panel_lists_matrix_cells():
    store = _store(_dataset())
    page = DecisionPage(store)
    summary = build_decision_summary(store.dataframe(), store.analysis_results)

    assert _lines(page.risk_note) == describe_risk_categories_detail(summary)
    assert "AZ · 高优先级 · 1 个 SKU" in page.risk_note.text()
    assert "BX · 中优先级 · 1 个 SKU" in page.risk_note.text()


def test_actions_panel_lists_next_actions():
    store = _store(_dataset())
    page = DecisionPage(store)
    summary = build_decision_summary(store.dataframe(), store.analysis_results)

    expected = [f"· {text}" for text in describe_next_actions(summary)]
    assert _lines(page.actions_note) == expected
    assert "查看需要重点关注的 SKU 清单并安排处理" in page.actions_note.text()


def test_unclassified_skus_are_reported_not_decided():
    dataframe = _dataset(missing_period_for="S6")
    store = _store(dataframe)
    page = DecisionPage(store)
    summary = build_decision_summary(store.dataframe(), store.analysis_results)

    assert summary.unclassified_sku_count == 1
    assert page.card_risk.value_label.text() == "1"
    assert "1 个 SKU 未参与分类" in page.status_note.text()
    assert "S6" not in {
        _cell(page.items_table, row, 0) for row in range(page.items_table.rowCount())
    }


# --------------------------------------------------------------------------- #
# 六、状态 5：模型未就绪
# --------------------------------------------------------------------------- #


def test_model_not_ready_note():
    page = DecisionPage(_store(_dataset(), with_models=False))

    assert page.status_badge.text() == "可决策"
    assert "尚未计算" in page.model_note.text()
    assert "EOQ 经济订货" in page.model_note.text()
    assert "安全库存 / ROP" in page.model_note.text()
    assert "补充 EOQ / 安全库存计算以完善补货参数" in page.actions_note.text()


def test_model_ready_note():
    page = DecisionPage(_store(_dataset(), with_models=True))

    assert page.model_note.text() == "EOQ 与安全库存均已计算，补货参数完整。"
    assert "补充 EOQ / 安全库存计算" not in page.actions_note.text()


# --------------------------------------------------------------------------- #
# 七、刷新与数据来源
# --------------------------------------------------------------------------- #


def test_refresh_follows_analysis_changes():
    store = _store(_dataset(), with_analyses=False)
    page = DecisionPage(store)
    assert page.status_badge.text() == "分析未就绪"

    _fill_analyses(store, store.dataframe(), with_models=True)
    store.analysis_changed.emit()

    assert page.status_badge.text() == "可决策"
    assert page.items_table.rowCount() == 4


def test_refresh_follows_data_changes():
    store = _store(None)
    page = DecisionPage(store)
    assert page.status_badge.text() == "无数据"

    store.load(str(PROJECT_ROOT / "data" / "sample_inventory.csv"))

    assert page.status_badge.text() == "分析未就绪"
    assert page.card_high.value_label.text() == PLACEHOLDER


def test_page_reads_rules_from_decision_layer():
    """页面不得自己维护优先级映射：显示值必须等于规则层的输出。"""
    store = _store(_dataset())
    page = DecisionPage(store)
    summary = build_decision_summary(store.dataframe(), store.analysis_results)

    displayed = {
        _cell(page.items_table, row, 0): _cell(page.items_table, row, 2)
        for row in range(page.items_table.rowCount())
    }
    for item in summary.priority_items:
        assert displayed[item.sku] == priority_label(item.priority)


def test_summary_snapshot_matches_page():
    store = _store(_dataset())
    page = DecisionPage(store)

    assert page.summary is not None
    assert page.summary.status == SUMMARY_READY
    assert page.summary == build_decision_summary(
        store.dataframe(), store.analysis_results
    )


def test_placeholder_is_used_for_missing_value():
    store = _store(_dataset(), with_analyses=False)
    dataframe = store.dataframe()
    abc = ABCAnalyzer(dataframe, "年消耗金额").analyze()
    xyz = XYZAnalyzer(dataframe, PERIODS).analyze()
    matrix = ABCXYZMatrixAnalyzer(
        abc.dataframe, xyz.dataframe, key_column="SKU", value_column=None
    ).analyze()
    store.set_analysis("abc", {"dataframe": abc.dataframe, "counts": abc.counts})
    store.set_analysis(
        "xyz",
        {
            "dataframe": xyz.dataframe,
            "counts": xyz.counts,
            "total_count": xyz.total_count,
            "status_counts": xyz.status_counts,
            "field_semantics": "ok",
        },
    )
    store.set_analysis(
        "matrix",
        {
            "dataframe": matrix.dataframe,
            "key_column": matrix.key_column,
            "value_column": matrix.value_column,
        },
    )

    page = DecisionPage(store)

    values = [
        _cell(page.items_table, row, 5) for row in range(page.items_table.rowCount())
    ]
    assert values
    assert set(values) == {PLACEHOLDER}


def test_table_is_read_only():
    page = DecisionPage(_store(_dataset()))

    from PySide6.QtWidgets import QTableWidget

    assert page.items_table.editTriggers() == QTableWidget.NoEditTriggers
    assert page.items_table.columnCount() > 0
    assert isinstance(page.items_table.item(0, 0), QTableWidgetItem)
