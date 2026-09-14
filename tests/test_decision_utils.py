"""库存决策摘要规则层的回归测试（V3.5.0-A-04.1）。

覆盖：
- v1 规则：AZ 高优先级、AY / BX 中优先级、其余一般关注
- 数据质量 BLOCKER 时不产生正常决策建议
- 未分类 SKU 不被强行归入决策
- 与现有 ABC×XYZ 矩阵结果保持一致
- 规则表覆盖全部 9 个单元、可替换
- 展示层措辞

本文件只验证决策规则，不涉及 ABC / XYZ / Matrix / EOQ / ROP 的算法。
"""

from __future__ import annotations

import pandas as pd
import pytest

from utils.abc_utils import ABCAnalyzer
from utils.decision_text import (
    describe_blocking,
    describe_focus,
    describe_item,
    describe_item_line,
    describe_next_actions,
    describe_risk_categories,
    describe_status,
    describe_unclassified,
    next_action_label,
    priority_label,
    severity_label,
    status_label,
)
from utils.decision_utils import (
    ACTION_MONITOR_BUFFER,
    ACTION_PRECISE_REPLENISH,
    ACTION_ROUTINE,
    ACTION_STANDARD_REPLENISH,
    ACTION_TIGHT_CONTROL_BUFFER,
    BLOCK_MISSING_MATRIX,
    BLOCK_MISSING_XYZ,
    BLOCK_QUALITY_BLOCKER,
    CATEGORY_RULE_OVERRIDES,
    DEFAULT_MAX_ITEMS,
    NEXT_IMPORT_DATA,
    NEXT_MONITOR_ROUTINE,
    NEXT_REVIEW_HIGH_PRIORITY,
    NEXT_REVIEW_UNCLASSIFIED,
    NEXT_RUN_INVENTORY_MODELS,
    NEXT_RUN_MISSING_ANALYSIS,
    PRIORITY_HIGH,
    PRIORITY_MEDIUM,
    PRIORITY_NORMAL,
    PRIORITY_ORDER,
    REASON_HIGH_VALUE_FLUCTUATING,
    REASON_HIGH_VALUE_STABLE,
    REASON_HIGH_VALUE_VOLATILE,
    REASON_MEDIUM_VALUE_STABLE,
    REASON_NORMAL_CATEGORY,
    SEVERITY_CRITICAL,
    SEVERITY_ELEVATED,
    SEVERITY_NORMAL,
    SUMMARY_BLOCKED_BY_QUALITY,
    SUMMARY_MISSING_ANALYSIS,
    SUMMARY_NO_DATA,
    SUMMARY_READY,
    all_category_rules,
    build_decision_summary,
    category_rule,
)
from utils.matrix_utils import CELL_ORDER, ABCXYZMatrixAnalyzer
from utils.xyz_utils import XYZAnalyzer

PERIODS = ["1月", "2月", "3月", "4月"]


def _dataset(missing_period_for: str | None = None) -> pd.DataFrame:
    """6 行数据，覆盖 AZ / AY / AX / BX / CY / CX 六种单元。

    年消耗金额合计 820 → ABC 为 A=3 / B=1 / C=2；
    周期波动（CV, ddof=0）依次为 Z / Y / X / X / Y / X。
    """
    rows = {
        "S1": (300.0, [10, 50, 20, 60]),   # A + Z = AZ
        "S2": (200.0, [100, 120, 80, 100]),  # A + Y = AY
        "S3": (150.0, [100, 100, 100, 100]),  # A + X = AX
        "S4": (100.0, [50, 50, 50, 50]),   # B + X = BX
        "S5": (50.0, [50, 60, 70, 60]),    # C + Y = CY
        "S6": (20.0, [20, 20, 20, 20]),    # C + X = CX
    }
    records = []
    for sku, (value, periods) in rows.items():
        periods = list(periods)
        if missing_period_for == sku:
            periods[1] = None
        records.append(
            {
                "SKU": sku,
                "年消耗金额": value,
                "1月": periods[0],
                "2月": periods[1],
                "3月": periods[2],
                "4月": periods[3],
            }
        )
    return pd.DataFrame(records)


def _analyses(dataframe: pd.DataFrame, key_column: str = "SKU") -> dict[str, dict]:
    """用真实分析器构建分析结果映射，不做 mock。"""
    abc = ABCAnalyzer(dataframe, "年消耗金额").analyze()
    xyz = XYZAnalyzer(dataframe, PERIODS).analyze()
    matrix = ABCXYZMatrixAnalyzer(
        abc.dataframe, xyz.dataframe, key_column=key_column, value_column="年消耗金额"
    ).analyze()
    return {
        "abc": {
            "dataframe": abc.dataframe,
            "counts": abc.counts,
            "contributions": abc.contributions,
            "value_column": "年消耗金额",
        },
        "xyz": {
            "dataframe": xyz.dataframe,
            "counts": xyz.counts,
            "mean_cv": xyz.mean_cv,
            "status_counts": xyz.status_counts,
            "total_count": xyz.total_count,
            "period_columns": PERIODS,
            "field_semantics": "ok",
        },
        "matrix": {
            "dataframe": matrix.dataframe,
            "cell_counts": matrix.cell_counts,
            "cell_values": matrix.cell_values,
            "cell_amounts": matrix.cell_amounts,
            "cell_sku_shares": matrix.cell_sku_shares,
            "key_column": matrix.key_column,
            "value_column": matrix.value_column,
            "total_value": matrix.total_value,
            "input_sku_count": matrix.input_sku_count,
            "excluded_sku_count": matrix.excluded_sku_count,
            "excluded_by_quality": matrix.excluded_by_quality,
        },
    }


@pytest.fixture
def dataset() -> pd.DataFrame:
    return _dataset()


@pytest.fixture
def analyses(dataset: pd.DataFrame) -> dict[str, dict]:
    return _analyses(dataset)


@pytest.fixture
def summary(dataset: pd.DataFrame, analyses: dict[str, dict]):
    return build_decision_summary(dataset, analyses)


# --------------------------------------------------------------------------- #
# 一、规则表
# --------------------------------------------------------------------------- #


def test_rule_table_covers_all_matrix_cells():
    rules = all_category_rules()

    assert set(rules) == set(CELL_ORDER)
    assert len(rules) == 9


def test_az_is_high_priority():
    rule = category_rule("AZ")

    assert rule.priority == PRIORITY_HIGH
    assert rule.severity == SEVERITY_CRITICAL
    assert rule.reason == REASON_HIGH_VALUE_VOLATILE
    assert rule.action == ACTION_TIGHT_CONTROL_BUFFER


def test_ax_is_high_priority():
    """AX 与 matrix_utils.CELL_STRATEGIES 的「高」保持一致。"""
    rule = category_rule("AX")

    assert rule.priority == PRIORITY_HIGH
    assert rule.severity == SEVERITY_ELEVATED
    assert rule.reason == REASON_HIGH_VALUE_STABLE
    assert rule.action == ACTION_PRECISE_REPLENISH


def test_az_severity_is_higher_than_ax():
    """AZ 与 AX 同为高优先级，但 AZ 的风险严重度更高（对应矩阵的「极高」）。"""
    assert category_rule("AZ").priority == category_rule("AX").priority == PRIORITY_HIGH
    assert category_rule("AZ").severity == SEVERITY_CRITICAL
    assert category_rule("AX").severity == SEVERITY_ELEVATED


def test_ay_and_bx_are_medium_priority():
    ay = category_rule("AY")
    bx = category_rule("BX")

    assert ay.priority == PRIORITY_MEDIUM
    assert ay.severity == SEVERITY_ELEVATED
    assert ay.reason == REASON_HIGH_VALUE_FLUCTUATING
    assert ay.action == ACTION_MONITOR_BUFFER

    assert bx.priority == PRIORITY_MEDIUM
    assert bx.severity == SEVERITY_ELEVATED
    assert bx.reason == REASON_MEDIUM_VALUE_STABLE
    assert bx.action == ACTION_STANDARD_REPLENISH


@pytest.mark.parametrize("category", ["BY", "BZ", "CX", "CY", "CZ"])
def test_other_combinations_are_normal(category):
    rule = category_rule(category)

    assert rule.priority == PRIORITY_NORMAL
    assert rule.severity == SEVERITY_NORMAL
    assert rule.reason == REASON_NORMAL_CATEGORY
    assert rule.action == ACTION_ROUTINE


def test_unknown_category_falls_back_to_default():
    assert category_rule("ZZ").priority == PRIORITY_NORMAL
    assert category_rule("").priority == PRIORITY_NORMAL


def test_overridden_categories():
    assert set(CATEGORY_RULE_OVERRIDES) == {"AX", "AY", "AZ", "BX"}


# --------------------------------------------------------------------------- #
# 二、摘要整体
# --------------------------------------------------------------------------- #


def test_summary_is_ready_for_complete_data(summary):
    assert summary.status == SUMMARY_READY
    assert summary.is_ready is True
    assert summary.decidable is True
    assert summary.blocking_reasons == []


def test_summary_counts_are_correct(summary):
    assert summary.total_sku_count == 6
    assert summary.analyzed_sku_count == 6
    assert summary.unclassified_sku_count == 0


def test_priority_distribution(summary):
    # S1 AZ / S3 AX → 高；S2 AY / S4 BX → 中；S5 CY / S6 CX → 一般
    assert summary.high_priority_count == 2
    assert summary.medium_priority_count == 2
    assert summary.normal_priority_count == 2
    assert summary.focus_count == 4
    assert summary.has_focus is True
    assert set(summary.priority_counts) == set(PRIORITY_ORDER)


def test_risk_categories_only_include_focus_cells(summary):
    assert summary.risk_category_counts == {"AZ": 1, "AX": 1, "AY": 1, "BX": 1}


def test_top_risk_items_are_high_priority_sorted_by_value(summary):
    assert [item.sku for item in summary.top_risk_items] == ["S1", "S3"]
    assert summary.top_risk_items[0].matrix_category == "AZ"
    assert summary.top_risk_items[0].priority == PRIORITY_HIGH
    assert summary.top_risk_items[1].matrix_category == "AX"
    assert summary.top_risk_items[1].priority == PRIORITY_HIGH


def test_priority_items_sorted_high_then_value_desc(summary):
    assert [item.sku for item in summary.priority_items] == ["S1", "S3", "S2", "S4"]
    assert [item.priority for item in summary.priority_items] == [
        PRIORITY_HIGH,
        PRIORITY_HIGH,
        PRIORITY_MEDIUM,
        PRIORITY_MEDIUM,
    ]


def test_decision_item_carries_expected_fields(summary):
    item = summary.top_risk_items[0]

    assert item.sku == "S1"
    assert item.abc_class == "A"
    assert item.xyz_class == "Z"
    assert item.matrix_category == "AZ"
    assert item.reason == REASON_HIGH_VALUE_VOLATILE
    assert item.suggested_action == ACTION_TIGHT_CONTROL_BUFFER
    assert item.value == pytest.approx(300.0)


def test_ax_item_uses_precise_replenish_action(summary):
    ax_item = next(item for item in summary.priority_items if item.matrix_category == "AX")

    assert ax_item.sku == "S3"
    assert ax_item.priority == PRIORITY_HIGH
    assert ax_item.reason == REASON_HIGH_VALUE_STABLE
    assert ax_item.suggested_action == ACTION_PRECISE_REPLENISH


def test_items_do_not_include_normal_skus(summary):
    skus = {item.sku for item in summary.priority_items}
    assert "S5" not in skus
    assert "S6" not in skus


def test_items_are_capped(dataset, analyses):
    capped = build_decision_summary(dataset, analyses, max_items=1)

    assert len(capped.priority_items) == 1
    assert capped.priority_items[0].sku == "S1"
    # 计数仍是全量，不受截断影响
    assert capped.focus_count == 4


def test_default_max_items_is_reasonable():
    assert DEFAULT_MAX_ITEMS >= 5


# --------------------------------------------------------------------------- #
# 三、不可决策的场景
# --------------------------------------------------------------------------- #


def test_no_data_is_not_decidable():
    summary = build_decision_summary(None, {})

    assert summary.status == SUMMARY_NO_DATA
    assert summary.decidable is False
    assert summary.priority_items == []
    assert summary.next_actions == [NEXT_IMPORT_DATA]


def test_empty_dataframe_is_not_decidable():
    summary = build_decision_summary(pd.DataFrame(), {})

    assert summary.status == SUMMARY_NO_DATA
    assert summary.decidable is False


def test_quality_blocker_blocks_decisions(analyses):
    """数据质量 BLOCKER 时不得生成正常决策建议。"""
    blocked = pd.DataFrame(
        {
            "SKU": [None, "B", "C", "D", "E", "F"],
            "年消耗金额": [300.0, 200.0, 150.0, 100.0, 50.0, 20.0],
            "1月": [10, 50, 20, 60, 30, 40],
            "2月": [20, 60, 30, 70, 40, 50],
            "3月": [30, 70, 40, 80, 50, 60],
            "4月": [40, 80, 50, 90, 60, 70],
        }
    )
    summary = build_decision_summary(blocked, analyses)

    assert summary.status == SUMMARY_BLOCKED_BY_QUALITY
    assert summary.decidable is False
    assert summary.blocking_reasons == [BLOCK_QUALITY_BLOCKER]
    assert summary.priority_items == []
    assert summary.top_risk_items == []
    assert summary.focus_count == 0
    assert summary.next_actions == ["fix_data_quality"]


def test_missing_analysis_blocks_decisions(dataset, analyses):
    partial = {"abc": analyses["abc"]}
    summary = build_decision_summary(dataset, partial)

    assert summary.status == SUMMARY_MISSING_ANALYSIS
    assert summary.decidable is False
    assert BLOCK_MISSING_XYZ in summary.blocking_reasons
    assert BLOCK_MISSING_MATRIX in summary.blocking_reasons
    assert summary.priority_items == []
    assert summary.next_actions == [NEXT_RUN_MISSING_ANALYSIS]


def test_matrix_without_expected_columns_is_treated_as_missing(dataset, analyses):
    broken = dict(analyses)
    broken["matrix"] = dict(analyses["matrix"])
    broken["matrix"]["dataframe"] = pd.DataFrame({"SKU": ["S1"], "其他": [1]})

    summary = build_decision_summary(dataset, broken)

    assert summary.status == SUMMARY_MISSING_ANALYSIS
    assert BLOCK_MISSING_MATRIX in summary.blocking_reasons


# --------------------------------------------------------------------------- #
# 四、未分类 SKU
# --------------------------------------------------------------------------- #


def test_unclassified_sku_is_excluded_from_decisions():
    dataframe = _dataset(missing_period_for="S6")
    summary = build_decision_summary(dataframe, _analyses(dataframe))

    assert summary.unclassified_sku_count == 1
    assert summary.analyzed_sku_count == 5
    assert summary.total_sku_count == 6
    assert "S6" not in {item.sku for item in summary.priority_items}


def test_no_item_uses_unclassified_category():
    dataframe = _dataset(missing_period_for="S6")
    summary = build_decision_summary(dataframe, _analyses(dataframe))

    for item in summary.priority_items:
        assert item.matrix_category in CELL_ORDER
        assert item.matrix_category != "未分类"
        assert item.priority != "undetermined"


def test_unclassified_count_adds_next_action():
    dataframe = _dataset(missing_period_for="S6")
    summary = build_decision_summary(dataframe, _analyses(dataframe))

    assert NEXT_REVIEW_UNCLASSIFIED in summary.next_actions


def test_no_unclassified_next_action_when_all_classified(summary):
    assert NEXT_REVIEW_UNCLASSIFIED not in summary.next_actions


# --------------------------------------------------------------------------- #
# 五、下一步建议
# --------------------------------------------------------------------------- #


def test_next_actions_include_high_priority_review(summary):
    assert NEXT_REVIEW_HIGH_PRIORITY in summary.next_actions


def test_next_actions_suggest_monitoring_when_no_focus():
    """全部为一般关注组合（BY / CX / CY）时，建议转为常规监控。"""
    plain = pd.DataFrame(
        {
            "SKU": ["S1", "S2", "S3"],
            "年消耗金额": [900.0, 60.0, 40.0],
            "1月": [100, 50, 50],
            "2月": [120, 50, 60],
            "3月": [80, 50, 70],
            "4月": [100, 50, 60],
        }
    )
    summary = build_decision_summary(plain, _analyses(plain))

    # 900 占 90% → B；其余为 C。S1 B+Y=BY、S2 C+X=CX、S3 C+Y=CY，均不触发高/中优先级
    assert summary.priority_counts[PRIORITY_HIGH] == 0
    assert summary.priority_counts[PRIORITY_MEDIUM] == 0
    assert summary.has_focus is False
    assert NEXT_MONITOR_ROUTINE in summary.next_actions
    assert NEXT_REVIEW_HIGH_PRIORITY not in summary.next_actions


def test_next_actions_suggest_inventory_models_when_missing(summary):
    assert summary.models_run == []
    assert NEXT_RUN_INVENTORY_MODELS in summary.next_actions


def test_next_actions_skip_inventory_models_when_present(dataset, analyses):
    with_models = dict(analyses)
    with_models["eoq"] = {"EOQ": 100.0}
    with_models["safety"] = {"安全库存": 10.0}

    summary = build_decision_summary(dataset, with_models)

    assert summary.models_run == ["eoq", "safety"]
    assert summary.missing_models == []
    assert NEXT_RUN_INVENTORY_MODELS not in summary.next_actions


def test_atypical_field_semantics_adds_next_action(dataset, analyses):
    adjusted = dict(analyses)
    adjusted["xyz"] = dict(analyses["xyz"])
    adjusted["xyz"]["field_semantics"] = "atypical_selection"

    summary = build_decision_summary(dataset, adjusted)

    assert "review_period_fields" in summary.next_actions


# --------------------------------------------------------------------------- #
# 六、与现有矩阵结果保持一致
# --------------------------------------------------------------------------- #


def test_sample_inventory_summary_matches_matrix(sample_dataframe, sample_period_columns):
    """正常样例：优先级分布必须能由矩阵单元数量直接推导出来。

    ABC 以「年需求量」为价值字段 → A=5 / B=3 / C=2；
    XYZ 为 X=4 / Y=6；交叉后 AX3 / AY2 / BY2 / BX1 / CY2。
    """
    abc = ABCAnalyzer(sample_dataframe, "年需求量").analyze()
    xyz = XYZAnalyzer(sample_dataframe, sample_period_columns).analyze()
    matrix = ABCXYZMatrixAnalyzer(
        abc.dataframe, xyz.dataframe, key_column="SKU", value_column="年需求量"
    ).analyze()

    assert matrix.cell_counts["AX"] == 3
    assert matrix.cell_counts["AY"] == 2
    assert matrix.cell_counts["BY"] == 2
    assert matrix.cell_counts["BX"] == 1
    assert matrix.cell_counts["CY"] == 2
    assert sum(matrix.cell_counts.values()) == len(sample_dataframe)

    summary = build_decision_summary(
        sample_dataframe,
        {
            "abc": {"dataframe": abc.dataframe, "counts": abc.counts},
            "xyz": {
                "dataframe": xyz.dataframe,
                "counts": xyz.counts,
                "total_count": xyz.total_count,
                "status_counts": xyz.status_counts,
                "field_semantics": "ok",
            },
            "matrix": {
                "dataframe": matrix.dataframe,
                "key_column": matrix.key_column,
                "value_column": matrix.value_column,
            },
        },
    )

    # AZ 0 + AX 3 → 高优先级 3；AY 2 + BX 1 → 中优先级 3；其余 4 个为一般关注
    assert summary.status == SUMMARY_READY
    assert summary.analyzed_sku_count == len(sample_dataframe)
    assert summary.high_priority_count == 3
    assert summary.medium_priority_count == 3
    assert summary.normal_priority_count == 4
    assert summary.risk_category_counts == {"AX": 3, "AY": 2, "BX": 1}
    assert summary.unclassified_sku_count == 0
    # 先高优先级，再按价值（年需求量）降序
    assert [item.sku for item in summary.priority_items] == [
        "A001", "A002", "A004", "A003", "A005", "A007",
    ]
    assert [item.matrix_category for item in summary.priority_items] == [
        "AX", "AX", "AX", "AY", "AY", "BX",
    ]
    assert len(summary.top_risk_items) == 3


def test_summary_does_not_copy_full_dataframe(summary):
    """决策条目只保存决策所需字段，不携带整行数据。"""
    item = summary.priority_items[0]

    assert not hasattr(item, "dataframe")
    assert set(item.__dataclass_fields__) == {
        "sku",
        "abc_class",
        "xyz_class",
        "matrix_category",
        "priority",
        "severity",
        "reason",
        "suggested_action",
        "value",
    }


# --------------------------------------------------------------------------- #
# 七、展示层措辞
# --------------------------------------------------------------------------- #


def test_label_helpers():
    assert status_label(SUMMARY_READY) == "可决策"
    assert status_label(SUMMARY_BLOCKED_BY_QUALITY) == "数据不可靠"
    assert priority_label(PRIORITY_HIGH) == "高优先级"
    assert priority_label(PRIORITY_MEDIUM) == "中优先级"
    assert priority_label(PRIORITY_NORMAL) == "一般关注"
    assert severity_label(SEVERITY_CRITICAL) == "严重"
    assert severity_label(SEVERITY_ELEVATED) == "较高"


def test_describe_item_returns_reason_and_action(summary):
    reason, action = describe_item(summary.top_risk_items[0])

    assert "高价值" in reason
    assert "安全库存" in action


def test_describe_item_line_contains_sku_and_category(summary):
    line = describe_item_line(summary.top_risk_items[0])

    assert "S1" in line
    assert "AZ" in line
    assert "高优先级" in line
    assert "建议：" in line


def test_describe_status_for_ready(summary):
    assert "可支撑决策" in describe_status(summary)


def test_describe_status_for_blocked(dataset, analyses):
    blocked = pd.DataFrame({"SKU": [None], "年消耗金额": [1.0], "1月": [1], "2月": [2]})
    summary = build_decision_summary(blocked, analyses)

    assert "阻断" in describe_status(summary)
    assert describe_blocking(summary) == ["数据质量存在阻断问题，无法给出可靠决策建议"]


def test_describe_focus_and_categories(summary):
    assert "4 个 SKU" in describe_focus(summary)
    assert "AZ 1 个" in describe_risk_categories(summary)


def test_describe_focus_when_not_ready():
    summary = build_decision_summary(None, {})

    assert describe_focus(summary) == "分析未就绪，暂无重点 SKU。"
    assert describe_unclassified(summary) == ""


def test_describe_unclassified_when_present():
    dataframe = _dataset(missing_period_for="S6")
    summary = build_decision_summary(dataframe, _analyses(dataframe))

    assert "1 个 SKU 未参与分类" in describe_unclassified(summary)


def test_describe_next_actions_are_human_readable(summary):
    labels = describe_next_actions(summary)

    assert labels
    assert all(isinstance(label, str) and label for label in labels)
    assert next_action_label(NEXT_IMPORT_DATA) == "在数据中心导入库存数据"


def test_high_priority_action_label_does_not_overclaim():
    """高优先级为 0、只有中优先级时，下一步文案不能只提「高优先级」。"""
    dataframe = pd.DataFrame(
        {
            "SKU": ["S1", "S2", "S3"],
            "年消耗金额": [300.0, 200.0, 100.0],
            "1月": [100, 50, 50],
            "2月": [120, 50, 50],
            "3月": [80, 50, 50],
            "4月": [100, 50, 50],
        }
    )
    summary = build_decision_summary(dataframe, _analyses(dataframe))

    # S1 A+Y=AY、S2 B+X=BX、S3 C+X=CX
    assert summary.high_priority_count == 0
    assert summary.medium_priority_count == 2
    assert NEXT_REVIEW_HIGH_PRIORITY in summary.next_actions

    label = next_action_label(NEXT_REVIEW_HIGH_PRIORITY)
    assert "重点关注的 SKU" in label
