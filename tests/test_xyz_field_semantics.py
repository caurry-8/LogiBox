"""XYZ 历史需求周期字段语义的回归测试（V3.5.0-A-03.1）。

覆盖：
- 周期字段识别（哪些像历史周期、哪些明确不是、识别不到时不猜测）
- 选择评估（手动选择非典型字段时给出 WARNING，但不阻断计算）
- 页面默认选中行为（自动选中真正的历史周期字段，年需求量 / 单价不被推荐）
- 展示层文案

注意：本文件只验证字段语义，不涉及 XYZ 的 CV 计算、阈值与数据质量语义。
"""

from __future__ import annotations

import pandas as pd
import pytest
from PySide6.QtCore import Qt

from pages.xyz_page import XYZPage
from utils.data_store import DataStore
from utils.field_utils import (
    CLASS_NON_PERIOD,
    CLASS_OTHER,
    CLASS_PERIOD,
    CLASS_POSSIBLE,
    FIELD_ATYPICAL_SELECTION,
    FIELD_FEW_PERIOD_FIELDS,
    FIELD_NO_PERIOD_FIELDS,
    FIELD_OK,
    PeriodFieldDetection,
    assess_period_selection,
    detect_period_fields,
)
from utils.quality_text import describe_field_detection, field_notice_line

NON_PERIOD_SAMPLE_COLUMNS = ("年需求量", "单价")


def _checked_columns(page: XYZPage) -> list[str]:
    return [
        page.period_list.item(index).text()
        for index in range(page.period_list.count())
        if page.period_list.item(index).checkState() == Qt.Checked
    ]


def _listed_columns(page: XYZPage) -> list[str]:
    return [page.period_list.item(index).text() for index in range(page.period_list.count())]


# --------------------------------------------------------------------------- #
# 一、周期字段识别
# --------------------------------------------------------------------------- #


def test_sample_inventory_detects_real_period_columns(sample_store, sample_period_columns):
    detection = detect_period_fields(sample_store.numeric_columns())

    assert detection.period_columns == list(sample_period_columns)
    assert detection.has_confident_periods is True
    assert detection.has_usable_sequence is True


def test_annual_demand_is_not_a_period_column(sample_store):
    detection = detect_period_fields(sample_store.numeric_columns())

    assert "年需求量" not in detection.period_columns
    assert "年需求量" in detection.non_period_columns


def test_unit_price_is_not_a_period_column(sample_store):
    detection = detect_period_fields(sample_store.numeric_columns())

    assert "单价" not in detection.period_columns
    assert "单价" in detection.non_period_columns


def test_non_period_columns_are_kept_selectable(sample_store):
    """明确非周期的字段只是不推荐，不能被从候选列表中删除。"""
    detection = detect_period_fields(sample_store.numeric_columns())

    assert set(NON_PERIOD_SAMPLE_COLUMNS).issubset(set(detection.non_period_columns))
    assert set(detection.ordered_columns()) == set(sample_store.numeric_columns())


def test_ordered_columns_put_periods_first_and_non_periods_last(sample_store):
    detection = detect_period_fields(sample_store.numeric_columns())
    ordered = detection.ordered_columns()

    assert ordered[:6] == ["1月需求", "2月需求", "3月需求", "4月需求", "5月需求", "6月需求"]
    assert ordered[-2:] == ["年需求量", "单价"]


def test_detects_common_period_naming_variants():
    columns = ["2026-01需求", "2026-02需求", "Jan Demand", "Feb Demand",
               "Month 1 Demand", "Demand_01", "Demand_02"]
    detection = detect_period_fields(columns)

    for column in columns:
        assert column in detection.period_columns, column


def test_no_period_columns_is_not_guessed():
    detection = detect_period_fields(["库存数量", "周转天数", "平均需求"])

    assert detection.period_columns == []
    assert detection.has_confident_periods is False


def test_only_one_period_column_is_not_a_usable_sequence():
    detection = detect_period_fields(["1月需求", "库存数量"])

    assert detection.period_columns == ["1月需求"]
    assert detection.has_usable_sequence is False


def test_empty_input_returns_empty_detection():
    detection = detect_period_fields([])

    assert detection.ordered_columns() == []
    assert detection.has_confident_periods is False


def test_duplicate_columns_are_deduplicated():
    detection = detect_period_fields(["1月需求", "1月需求", "单价", "单价"])

    assert detection.period_columns == ["1月需求"]
    assert detection.non_period_columns == ["单价"]


@pytest.mark.parametrize(
    "column",
    ["单价", "价格", "unit_price", "Price", "年需求量", "年销量", "年销售额", "金额", "amount", "SKU", "编码", "名称", "类别"],
)
def test_explicit_non_period_names_are_classified_as_non_period(column):
    detection = detect_period_fields([column])

    assert detection.non_period_columns == [column]
    assert detection.period_columns == []


# --------------------------------------------------------------------------- #
# 二、选择评估
# --------------------------------------------------------------------------- #


def test_selecting_real_period_columns_is_ok(sample_store, sample_period_columns):
    detection = detect_period_fields(sample_store.numeric_columns())
    assessment = assess_period_selection(sample_period_columns, detection)

    assert assessment.code == FIELD_OK
    assert assessment.is_ok is True
    assert assessment.atypical_selected == []


def test_selecting_annual_demand_and_price_produces_warning(sample_store):
    detection = detect_period_fields(sample_store.numeric_columns())
    assessment = assess_period_selection(["年需求量", "单价"], detection)

    assert assessment.code == FIELD_ATYPICAL_SELECTION
    assert assessment.is_ok is False
    assert assessment.atypical_selected == ["年需求量", "单价"]


def test_mixing_one_atypical_column_still_warns(sample_store, sample_period_columns):
    detection = detect_period_fields(sample_store.numeric_columns())
    assessment = assess_period_selection(["1月需求", "年需求量"], detection)

    assert assessment.code == FIELD_ATYPICAL_SELECTION
    assert assessment.atypical_selected == ["年需求量"]


def test_no_period_fields_in_data_produces_notice():
    detection = detect_period_fields(["库存数量", "周转天数"])
    assessment = assess_period_selection(["库存数量", "周转天数"], detection)

    assert assessment.code == FIELD_NO_PERIOD_FIELDS


def test_single_period_field_produces_few_periods_notice():
    detection = detect_period_fields(["1月需求", "库存数量"])
    assessment = assess_period_selection(["1月需求", "库存数量"], detection)

    assert assessment.code == FIELD_FEW_PERIOD_FIELDS
    assert assessment.period_count == 1


def test_atypical_selection_takes_priority_over_other_codes():
    detection = PeriodFieldDetection(period_columns=["1月需求"], non_period_columns=["单价"])
    assessment = assess_period_selection(["1月需求", "单价"], detection)

    assert assessment.code == FIELD_ATYPICAL_SELECTION


# --------------------------------------------------------------------------- #
# 三、展示层文案
# --------------------------------------------------------------------------- #


def test_field_notice_line_is_empty_when_ok():
    assert field_notice_line(FIELD_OK) == ""


def test_field_notice_line_mentions_offending_columns():
    line = field_notice_line(FIELD_ATYPICAL_SELECTION, columns="年需求量、单价", count=6)

    assert "注意" in line
    assert "年需求量、单价" in line
    assert "建议" in line


def test_field_notice_line_for_few_periods_includes_count():
    line = field_notice_line(FIELD_FEW_PERIOD_FIELDS, columns="", count=1)

    assert "1" in line
    assert "注意" in line


def test_describe_field_detection_reports_detected_columns(sample_store):
    detection = detect_period_fields(sample_store.numeric_columns())
    text = describe_field_detection(detection)

    assert "6" in text
    assert "1月需求" in text


def test_describe_field_detection_asks_for_manual_selection_when_unknown():
    detection = detect_period_fields(["库存数量", "周转天数"])

    assert "未自动识别" in describe_field_detection(detection)


# --------------------------------------------------------------------------- #
# 四、页面默认选中行为
# --------------------------------------------------------------------------- #


def test_page_default_selects_real_period_columns(sample_store, sample_period_columns):
    page = XYZPage(sample_store)

    assert _checked_columns(page) == list(sample_period_columns)


def test_page_does_not_default_select_annual_demand_or_price(sample_store):
    page = XYZPage(sample_store)
    checked = _checked_columns(page)

    assert "年需求量" not in checked
    assert "单价" not in checked


def test_page_lists_non_period_columns_last(sample_store):
    page = XYZPage(sample_store)

    assert _listed_columns(page)[-2:] == ["年需求量", "单价"]


def test_page_field_note_explains_auto_selection(sample_store):
    page = XYZPage(sample_store)
    text = page.field_note.text()

    assert "已自动识别" in text
    assert "6" in text


def test_page_does_not_guess_when_data_has_no_period_columns():
    store = DataStore()
    store.df = pd.DataFrame({"SKU": ["A", "B"], "库存数量": [10, 20], "周转天数": [3, 4]})
    page = XYZPage(store)

    assert _checked_columns(page) == []
    assert "未自动识别" in page.field_note.text()


def test_page_shows_warning_note_when_atypical_columns_selected(sample_store):
    page = XYZPage(sample_store)
    for index in range(page.period_list.count()):
        item = page.period_list.item(index)
        item.setCheckState(
            Qt.Checked if item.text() in NON_PERIOD_SAMPLE_COLUMNS else Qt.Unchecked
        )

    page.run_analysis()

    note = page.coverage_note.text()
    assert "注意" in note
    assert "年需求量" in note
    assert page.coverage_note.property("warn") == "true"


def test_page_analysis_still_completes_with_atypical_columns(sample_store):
    """语义可疑只是 WARNING，不能阻断计算。"""
    page = XYZPage(sample_store)
    for index in range(page.period_list.count()):
        item = page.period_list.item(index)
        item.setCheckState(
            Qt.Checked if item.text() in NON_PERIOD_SAMPLE_COLUMNS else Qt.Unchecked
        )

    page.run_analysis()

    assert page.status.text() == "分析完成"
    stored = sample_store.get_analysis("xyz")
    assert stored is not None
    assert stored["field_semantics"] == FIELD_ATYPICAL_SELECTION
    assert stored["period_columns"] == list(NON_PERIOD_SAMPLE_COLUMNS)


def test_page_publishes_ok_semantics_for_real_period_columns(
    sample_store, sample_period_columns
):
    page = XYZPage(sample_store)
    page.run_analysis()

    stored = sample_store.get_analysis("xyz")
    assert stored["field_semantics"] == FIELD_OK
    assert stored["period_columns"] == list(sample_period_columns)
    assert stored["detected_period_count"] == 6
    assert "注意" not in page.coverage_note.text()
    assert page.coverage_note.property("warn") == "false"


def test_page_resets_field_note_when_data_changes(sample_store):
    page = XYZPage(sample_store)
    store = DataStore()
    store.df = pd.DataFrame({"SKU": ["A", "B"], "库存数量": [10, 20], "周转天数": [3, 4]})

    page.store = store
    page.refresh_columns()

    assert "未自动识别" in page.field_note.text()
    assert page.coverage_note.property("warn") == "false"
