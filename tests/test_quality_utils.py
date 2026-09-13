"""数据质量判定与措辞的回归测试（V3.5.0-A-03）。

分两部分：
- 判定层：utils/quality_utils.py —— 严重级别、计数、状态聚合
- 展示层：utils/quality_text.py —— 面向用户的措辞与覆盖率文案

判定与措辞分离是设计约束：quality_utils 不含界面文案，quality_text 不含判定逻辑。
"""

from __future__ import annotations

import pandas as pd
import pytest

from utils import quality_text
from utils.quality_text import (
    coverage_text,
    describe,
    excluded_reason_text,
    format_cell_value,
    format_issue_line,
    impact_text,
    severity_label,
    status_label,
    xyz_status_label,
)
from utils.quality_utils import (
    ANALYSIS_ABC,
    ANALYSIS_MATRIX,
    ANALYSIS_XYZ,
    CODE_ALL_ZERO_PERIOD,
    CODE_DUPLICATE_KEY_VALUE,
    CODE_EMPTY_DATASET,
    CODE_EMPTY_KEY_VALUE,
    CODE_KEY_COLUMN_UNIDENTIFIED,
    CODE_MISSING_CELLS,
    CODE_NEGATIVE_VALUE,
    CODE_PERIOD_COLUMN_MISSING,
    CODE_PERIOD_COLUMN_NOT_NUMERIC,
    CODE_PERIOD_MISSING_VALUE,
    SEVERITY_BLOCKER,
    SEVERITY_INFO,
    SEVERITY_ORDER,
    SEVERITY_WARNING,
    STATUS_BLOCKER,
    STATUS_OK,
    STATUS_WARNING,
    assess_data_quality,
    detect_key_column,
)


def _codes(result) -> set[str]:
    return {issue.code for issue in result.issues}


def _issue(result, code: str):
    return next(issue for issue in result.issues if issue.code == code)


# --------------------------------------------------------------------------- #
# 一、干净数据
# --------------------------------------------------------------------------- #


def test_clean_data_has_no_issues():
    dataframe = pd.DataFrame({"SKU": ["A", "B"], "年需求量": [10, 20]})
    result = assess_data_quality(dataframe)

    assert result.status == STATUS_OK
    assert result.issues == []
    assert result.is_analyzable is True
    assert result.blocker_count == 0
    assert result.warning_count == 0
    assert result.info_count == 0


def test_clean_data_reports_counts():
    dataframe = pd.DataFrame({"SKU": ["A", "B", "C"], "年需求量": [10, 20, 30]})
    result = assess_data_quality(dataframe)

    assert result.total_rows == 3
    assert result.total_columns == 2
    assert result.valid_key_count == 3
    assert result.empty_key_count == 0
    assert result.duplicate_key_count == 0
    assert result.missing_cell_count == 0


def test_sample_inventory_is_clean(sample_dataframe):
    result = assess_data_quality(sample_dataframe)

    assert result.status == STATUS_OK
    assert result.issues == []
    assert result.key_column == "SKU"
    assert result.key_column_confident is True
    assert result.valid_key_count == 10
    assert result.duplicate_key_count == 0
    assert result.empty_key_count == 0


def test_sample_inventory_with_period_columns_is_clean(
    sample_dataframe, sample_period_columns
):
    result = assess_data_quality(
        sample_dataframe, period_columns=sample_period_columns
    )

    assert result.status == STATUS_OK
    assert result.issues == []


# --------------------------------------------------------------------------- #
# 二、BLOCKER 级判定
# --------------------------------------------------------------------------- #


def test_none_dataframe_is_blocker():
    result = assess_data_quality(None)

    assert result.status == STATUS_BLOCKER
    assert result.total_rows == 0
    assert _codes(result) == {CODE_EMPTY_DATASET}
    assert result.is_analyzable is False


def test_empty_dataframe_is_blocker():
    result = assess_data_quality(pd.DataFrame())

    assert result.status == STATUS_BLOCKER
    assert _codes(result) == {CODE_EMPTY_DATASET}


def test_empty_dataset_affects_all_inventory_analyses():
    issue = _issue(assess_data_quality(pd.DataFrame()), CODE_EMPTY_DATASET)

    assert issue.severity == SEVERITY_BLOCKER
    assert ANALYSIS_ABC in issue.affected_analyses
    assert ANALYSIS_XYZ in issue.affected_analyses
    assert ANALYSIS_MATRIX in issue.affected_analyses


def test_empty_key_value_is_blocker():
    dataframe = pd.DataFrame({"SKU": ["A", None, "C"], "金额": [1, 2, 3]})
    result = assess_data_quality(dataframe)

    assert result.status == STATUS_BLOCKER
    assert result.empty_key_count == 1
    assert result.valid_key_count == 2
    assert _issue(result, CODE_EMPTY_KEY_VALUE).severity == SEVERITY_BLOCKER


def test_blank_string_key_value_counts_as_empty():
    dataframe = pd.DataFrame({"SKU": ["A", "   ", "C"], "金额": [1, 2, 3]})
    result = assess_data_quality(dataframe)

    assert result.empty_key_count == 1
    assert result.valid_key_count == 2


def test_missing_period_column_is_blocker():
    dataframe = pd.DataFrame({"SKU": ["A"], "1月": [10]})
    result = assess_data_quality(dataframe, period_columns=["1月", "9月"])

    assert result.status == STATUS_BLOCKER
    issue = _issue(result, CODE_PERIOD_COLUMN_MISSING)
    assert issue.severity == SEVERITY_BLOCKER
    assert issue.details["columns"] == ["9月"]
    assert ANALYSIS_XYZ in issue.affected_analyses


def test_non_numeric_period_column_is_blocker():
    dataframe = pd.DataFrame({"SKU": ["A", "B"], "1月": ["甲", "乙"], "2月": ["丙", "丁"]})
    result = assess_data_quality(dataframe, period_columns=["1月", "2月"])

    assert result.status == STATUS_BLOCKER
    assert _issue(result, CODE_PERIOD_COLUMN_NOT_NUMERIC).severity == SEVERITY_BLOCKER


# --------------------------------------------------------------------------- #
# 三、WARNING 级判定
# --------------------------------------------------------------------------- #


def test_duplicate_key_is_warning_and_affects_matrix():
    dataframe = pd.DataFrame({"SKU": ["A", "A", "B"], "金额": [1, 2, 3]})
    result = assess_data_quality(dataframe)

    assert result.duplicate_key_count == 1
    assert result.status == STATUS_WARNING
    issue = _issue(result, CODE_DUPLICATE_KEY_VALUE)
    assert issue.severity == SEVERITY_WARNING
    assert issue.affected_analyses == (ANALYSIS_MATRIX,)


def test_duplicate_key_ignores_blank_values():
    dataframe = pd.DataFrame({"SKU": ["A", None, None], "金额": [1, 2, 3]})
    result = assess_data_quality(dataframe)

    # 两个空值只算「空值」，不算「重复」
    assert result.empty_key_count == 2
    assert result.duplicate_key_count == 0


def test_missing_cells_is_warning():
    dataframe = pd.DataFrame({"SKU": ["A", "B"], "金额": [1, None]})
    result = assess_data_quality(dataframe)

    assert result.missing_cell_count == 1
    issue = _issue(result, CODE_MISSING_CELLS)
    assert issue.severity == SEVERITY_WARNING
    assert issue.affected_count == 1


def test_negative_value_is_warning():
    dataframe = pd.DataFrame({"SKU": ["A", "B"], "金额": [10, -5]})
    result = assess_data_quality(dataframe)

    issue = _issue(result, CODE_NEGATIVE_VALUE)
    assert issue.severity == SEVERITY_WARNING
    assert issue.affected_count == 1
    assert issue.details["columns"] == ["金额"]


def test_period_missing_value_is_warning_and_affects_xyz():
    dataframe = pd.DataFrame({"SKU": ["A", "B"], "1月": [10, None], "2月": [20, 30]})
    result = assess_data_quality(dataframe, period_columns=["1月", "2月"])

    issue = _issue(result, CODE_PERIOD_MISSING_VALUE)
    assert issue.severity == SEVERITY_WARNING
    assert issue.affected_count == 1
    assert issue.affected_analyses == (ANALYSIS_XYZ,)


def test_all_zero_period_is_warning():
    dataframe = pd.DataFrame({"SKU": ["A", "B"], "1月": [0, 10], "2月": [0, 20]})
    result = assess_data_quality(dataframe, period_columns=["1月", "2月"])

    issue = _issue(result, CODE_ALL_ZERO_PERIOD)
    assert issue.severity == SEVERITY_WARNING
    assert issue.affected_count == 1


def test_all_missing_row_is_not_counted_as_all_zero():
    """整行缺失与整行全零是两件事，不能重复计数。"""
    dataframe = pd.DataFrame({"SKU": ["ZERO", "MISSING"], "1月": [0, None], "2月": [0, None]})
    result = assess_data_quality(dataframe, period_columns=["1月", "2月"])

    assert _issue(result, CODE_PERIOD_MISSING_VALUE).affected_count == 1
    assert _issue(result, CODE_ALL_ZERO_PERIOD).affected_count == 1


# --------------------------------------------------------------------------- #
# 四、主键识别（不猜测原则）
# --------------------------------------------------------------------------- #


def test_detect_key_column_accepts_known_names():
    assert detect_key_column(["仓库", "SKU", "金额"]) == "SKU"
    assert detect_key_column(["物料编码", "名称"]) == "物料编码"


def test_detect_key_column_does_not_guess():
    assert detect_key_column(["产品", "数量"]) is None
    assert detect_key_column(["第一列", "第二列"]) is None
    assert detect_key_column([]) is None


def test_unidentified_key_reports_info_and_no_sku_metrics():
    dataframe = pd.DataFrame({"产品": ["甲", "乙"], "数量": [1, 2]})
    result = assess_data_quality(dataframe)

    assert result.key_column is None
    assert result.key_column_confident is False
    assert result.has_key_metrics is False
    issue = _issue(result, CODE_KEY_COLUMN_UNIDENTIFIED)
    assert issue.severity == SEVERITY_INFO
    # 只有 INFO 不应让整体状态升级
    assert result.status == STATUS_OK


def test_explicit_key_column_is_respected():
    dataframe = pd.DataFrame({"自定义主键": ["A", "B"], "金额": [1, 2]})
    result = assess_data_quality(dataframe, key_column="自定义主键")

    assert result.key_column == "自定义主键"
    assert result.key_column_confident is True
    assert result.has_key_metrics is True
    assert result.valid_key_count == 2


def test_unknown_explicit_key_column_is_not_used():
    dataframe = pd.DataFrame({"SKU": ["A"], "金额": [1]})
    result = assess_data_quality(dataframe, key_column="不存在的列")

    assert result.key_column is None
    assert result.has_key_metrics is False


# --------------------------------------------------------------------------- #
# 五、状态聚合
# --------------------------------------------------------------------------- #


def test_blocker_dominates_status():
    dataframe = pd.DataFrame({"SKU": [None, "B"], "金额": [1, None]})
    result = assess_data_quality(dataframe)

    assert result.blocker_count >= 1
    assert result.status == STATUS_BLOCKER


def test_severity_counts_cover_all_levels():
    dataframe = pd.DataFrame({"产品": ["甲"], "金额": [-1]})
    result = assess_data_quality(dataframe)

    assert set(result.severity_counts) == set(SEVERITY_ORDER)
    assert result.severity_counts[SEVERITY_INFO] == 1  # 主键未识别
    assert result.severity_counts[SEVERITY_WARNING] == 1  # 负值


def test_issues_by_severity_filters_correctly():
    dataframe = pd.DataFrame({"SKU": [None, "B"], "金额": [1, None]})
    result = assess_data_quality(dataframe)

    assert all(i.severity == SEVERITY_BLOCKER for i in result.issues_by_severity(SEVERITY_BLOCKER))
    assert all(i.severity == SEVERITY_WARNING for i in result.issues_by_severity(SEVERITY_WARNING))


def test_period_rules_only_apply_when_columns_given():
    """周期相关规则必须由调用方显式给出列，不由底层猜测。"""
    dataframe = pd.DataFrame({"SKU": ["A", "B"], "1月": [10, None], "2月": [20, None]})
    without = assess_data_quality(dataframe)
    with_periods = assess_data_quality(dataframe, period_columns=["1月", "2月"])

    assert CODE_PERIOD_MISSING_VALUE not in _codes(without)
    assert CODE_ALL_ZERO_PERIOD not in _codes(without)
    assert CODE_PERIOD_MISSING_VALUE in _codes(with_periods)
    assert _issue(with_periods, CODE_PERIOD_MISSING_VALUE).affected_count == 1


def test_fully_empty_period_column_is_blocker_not_warning():
    """整列没有任何数值属于阻断问题（无法分析），不是普通的缺失警告。"""
    dataframe = pd.DataFrame({"SKU": ["A", "B"], "1月": [None, None], "2月": [10, 20]})
    result = assess_data_quality(dataframe, period_columns=["1月", "2月"])

    assert result.status == STATUS_BLOCKER
    assert CODE_PERIOD_COLUMN_NOT_NUMERIC in _codes(result)
    assert CODE_PERIOD_MISSING_VALUE not in _codes(result)


# --------------------------------------------------------------------------- #
# 六、展示层措辞（utils/quality_text.py）
# --------------------------------------------------------------------------- #


def test_describe_returns_registered_text():
    issue = _issue(
        assess_data_quality(pd.DataFrame({"SKU": ["A"], "金额": [None]})),
        CODE_MISSING_CELLS,
    )
    title, description, action = describe(issue)

    assert title == "存在缺失单元格"
    assert "1" in description
    assert action


def test_describe_falls_back_for_unknown_code():
    from utils.quality_utils import QualityIssue

    title, description, action = describe(QualityIssue(code="unknown_code", severity=SEVERITY_INFO))

    assert title == "unknown_code"
    assert description
    assert action


def test_describe_formats_column_details():
    issue = _issue(
        assess_data_quality(pd.DataFrame({"SKU": ["A"]}), period_columns=["9月"]),
        CODE_PERIOD_COLUMN_MISSING,
    )
    _title, description, _action = describe(issue)

    assert "9月" in description


def test_format_issue_line_contains_severity_and_action():
    issue = _issue(
        assess_data_quality(pd.DataFrame({"SKU": ["A"], "金额": [None]})),
        CODE_MISSING_CELLS,
    )
    line = format_issue_line(issue)

    assert "警告" in line
    assert "建议：" in line
    assert "存在缺失单元格" in line


def test_impact_text_lists_analyses():
    issue = _issue(
        assess_data_quality(pd.DataFrame({"SKU": ["A"], "金额": [None]})),
        CODE_MISSING_CELLS,
    )
    assert impact_text(issue) == "影响：ABC 分类、XYZ 分析"


def test_impact_text_empty_without_analyses():
    from utils.quality_utils import QualityIssue

    assert impact_text(QualityIssue(code="x", severity=SEVERITY_INFO)) == ""


def test_label_helpers():
    assert severity_label(SEVERITY_BLOCKER) == "阻断"
    assert status_label(STATUS_OK) == "可分析"
    assert status_label(STATUS_WARNING) == "存在风险"
    assert status_label(STATUS_BLOCKER) == "无法分析"
    assert xyz_status_label("missing") == "缺失数据"
    assert xyz_status_label("invalid") == "非法数据"


def test_coverage_text_formats_ratio():
    assert coverage_text(2, 4) == "2 / 4（50.0%）"
    assert coverage_text(10, 10) == "10 / 10（100.0%）"
    assert coverage_text(0, 0) == "0 / 0"


def test_excluded_reason_text_translates_statuses():
    text = excluded_reason_text({"missing": 1, "invalid": 2})

    assert "缺失数据 1" in text
    assert "非法数据 2" in text
    assert excluded_reason_text({}) == ""


def test_quality_text_has_no_judgement_logic():
    """展示层不应反向定义判定规则：问题编码必须来自 quality_utils。"""
    from utils.quality_utils import (
        CODE_ALL_ZERO_PERIOD as source_all_zero,
        CODE_MISSING_CELLS as source_missing,
    )

    assert set(quality_text.ISSUE_TEXT) >= {source_missing, source_all_zero}


# --------------------------------------------------------------------------- #
# 七、单元格展示占位符统一
# --------------------------------------------------------------------------- #


def test_format_cell_value_uses_placeholders():
    assert format_cell_value(None) == "—"
    assert format_cell_value(float("nan")) == "—"
    assert format_cell_value(float("inf")) == "非法值"
    assert format_cell_value(float("-inf")) == "非法值"


def test_format_cell_value_keeps_ordinary_values():
    assert format_cell_value(0) == "0"
    assert format_cell_value(0.0) == "0.0"
    assert format_cell_value("西安仓") == "西安仓"


def test_format_cell_value_with_digits():
    assert format_cell_value(1 / 3, digits=4) == "0.3333"
    assert format_cell_value(float("nan"), digits=4) == "—"
    assert format_cell_value(float("inf"), digits=4) == "非法值"
