"""ABC 库存价值分类回归基线。

覆盖：示例数据 A/B/C 数量、金额占比与累计占比、分类边界语义、
年消耗金额生成，以及非法输入。
本文件只验证当前行为，不修改算法。
"""

from __future__ import annotations

import pandas as pd
import pytest

from utils.abc_utils import ABCAnalyzer

# 示例数据（年需求量列）合计 46600，降序后累计占比依次为
# 0.2575 / 0.4399 / 0.5794 / 0.6910 / 0.7790 / 0.8476 / 0.9077 / 0.9485 / 0.9807 / 1.0
SAMPLE_TOTAL_VALUE = 46600.0
SAMPLE_COUNTS = {"A": 5, "B": 3, "C": 2}
SAMPLE_CONTRIBUTIONS = {"A": 36300 / 46600, "B": 7900 / 46600, "C": 2400 / 46600}


def test_sample_data_classifies_into_a5_b3_c2(sample_dataframe):
    result = ABCAnalyzer(sample_dataframe, "年需求量").analyze()
    assert result.counts == SAMPLE_COUNTS


def test_sample_classification_covers_every_row(sample_dataframe):
    result = ABCAnalyzer(sample_dataframe, "年需求量").analyze()
    assert sum(result.counts.values()) == len(sample_dataframe)
    assert len(result.dataframe) == len(sample_dataframe)


def test_sample_value_contributions_match_manual_calculation(sample_dataframe):
    result = ABCAnalyzer(sample_dataframe, "年需求量").analyze()
    for category, expected in SAMPLE_CONTRIBUTIONS.items():
        assert result.contributions[category] == pytest.approx(expected, rel=1e-9)


def test_contributions_sum_to_one(sample_dataframe):
    result = ABCAnalyzer(sample_dataframe, "年需求量").analyze()
    assert sum(result.contributions.values()) == pytest.approx(1.0, rel=1e-9)


def test_value_shares_sum_to_one(sample_dataframe):
    result = ABCAnalyzer(sample_dataframe, "年需求量").analyze()
    assert result.dataframe["金额占比"].sum() == pytest.approx(1.0, rel=1e-9)


def test_cumulative_share_is_monotonic_and_reaches_one(sample_dataframe):
    result = ABCAnalyzer(sample_dataframe, "年需求量").analyze()
    cumulative = result.dataframe["累计占比"]
    assert cumulative.is_monotonic_increasing
    assert cumulative.iloc[-1] == pytest.approx(1.0, rel=1e-9)


def test_rows_are_sorted_by_value_descending(sample_dataframe):
    result = ABCAnalyzer(sample_dataframe, "年需求量").analyze()
    values = result.dataframe["年需求量"].tolist()
    assert values == sorted(values, reverse=True)
    assert values[0] == 12000
    assert values[-1] == 900


def test_specific_sku_boundary_assignments(sample_dataframe):
    """核对处在阈值附近的 SKU 归属：A005 累计 0.7790 属 A 类，A008 累计 0.9485 属 B 类。"""
    result = ABCAnalyzer(sample_dataframe, "年需求量").analyze()
    assignment = dict(
        zip(result.dataframe["SKU"], result.dataframe["ABC分类"], strict=True)
    )
    assert assignment["A001"] == "A"
    assert assignment["A005"] == "A"
    assert assignment["A006"] == "B"
    assert assignment["A008"] == "B"
    assert assignment["A009"] == "C"
    assert assignment["A010"] == "C"


def test_threshold_boundaries_are_inclusive():
    """分类使用 `累计占比 <= 阈值` 判定，因此正好等于阈值时归入较低类别。

    4 行等值数据配合 A=50% / B=75%，累计占比恰好是 0.25 / 0.50 / 0.75 / 1.00，
    这些数值在二进制浮点下可精确表示，适合作为边界回归。
    """
    dataframe = pd.DataFrame({"SKU": ["B1", "B2", "B3", "B4"], "金额": [1, 1, 1, 1]})
    result = ABCAnalyzer(dataframe, "金额", a_rate=0.50, b_rate=0.75).analyze()

    assert result.dataframe["累计占比"].tolist() == [0.25, 0.50, 0.75, 1.00]
    assert result.dataframe["ABC分类"].tolist() == ["A", "A", "B", "C"]
    assert result.counts == {"A": 2, "B": 1, "C": 1}


def test_custom_thresholds_change_classification():
    """收紧阈值会把原本属于 A 类的 SKU 挤到 B 类。"""
    dataframe = pd.DataFrame({"SKU": ["T1", "T2", "T3", "T4"], "金额": [50, 30, 15, 5]})
    strict = ABCAnalyzer(dataframe, "金额", a_rate=0.60, b_rate=0.96).analyze()
    loose = ABCAnalyzer(dataframe, "金额", a_rate=0.90, b_rate=0.99).analyze()

    assert strict.counts == {"A": 1, "B": 2, "C": 1}
    assert loose.counts == {"A": 2, "B": 1, "C": 1}


def test_missing_value_column_is_rejected(sample_dataframe):
    with pytest.raises(ValueError, match="找不到分析字段"):
        ABCAnalyzer(sample_dataframe, "不存在的字段").analyze()


@pytest.mark.parametrize(
    ("a_rate", "b_rate"),
    [(0.95, 0.80), (0.80, 0.80), (0.0, 0.95), (0.80, 1.0), (-0.1, 0.95)],
)
def test_invalid_thresholds_are_rejected(sample_dataframe, a_rate, b_rate):
    with pytest.raises(ValueError, match="阈值必须满足"):
        ABCAnalyzer(sample_dataframe, "年需求量", a_rate, b_rate).analyze()


def test_non_numeric_value_column_is_rejected():
    dataframe = pd.DataFrame({"SKU": ["N1", "N2"], "金额": ["甲", "乙"]})
    with pytest.raises(ValueError, match="不是有效的数值列"):
        ABCAnalyzer(dataframe, "金额").analyze()


def test_negative_values_are_rejected():
    dataframe = pd.DataFrame({"SKU": ["G1", "G2"], "金额": [10, -5]})
    with pytest.raises(ValueError, match="不能包含负数"):
        ABCAnalyzer(dataframe, "金额").analyze()


def test_zero_total_is_rejected():
    dataframe = pd.DataFrame({"SKU": ["Z1", "Z2"], "金额": [0, 0]})
    with pytest.raises(ValueError, match="总值必须大于 0"):
        ABCAnalyzer(dataframe, "金额").analyze()


def test_current_behaviour_missing_value_is_treated_as_zero():
    """记录当前行为：金额列中的缺失值会被 fillna(0) 当作 0。

    这是 V3.5 数据可信层要评估的对象，此处只做行为基线，不做修改。
    """
    dataframe = pd.DataFrame({"SKU": ["M1", "M2", "M3"], "金额": [60.0, None, 40.0]})
    result = ABCAnalyzer(dataframe, "金额").analyze()

    # 缺失被当作 0 → 降序 60 / 40 / 0，合计 100，累计 0.6 / 1.0 / 1.0
    assert result.dataframe["金额"].tolist() == [60.0, 40.0, 0.0]
    assert result.counts == {"A": 1, "B": 0, "C": 2}


def test_build_consumption_value_multiplies_demand_and_price(small_pricing_dataframe):
    result = ABCAnalyzer.build_consumption_value(small_pricing_dataframe, "年需求量", "单价")
    assert result["年消耗金额"].tolist() == [80.0, 30.0, 15.0, 5.0]
    assert result["年消耗金额"].sum() == pytest.approx(130.0)


def test_build_consumption_value_does_not_mutate_input(small_pricing_dataframe):
    original_columns = list(small_pricing_dataframe.columns)
    ABCAnalyzer.build_consumption_value(small_pricing_dataframe, "年需求量", "单价")
    assert list(small_pricing_dataframe.columns) == original_columns


def test_build_consumption_value_rejects_missing_demand_column(small_pricing_dataframe):
    with pytest.raises(ValueError, match="找不到需求量字段"):
        ABCAnalyzer.build_consumption_value(small_pricing_dataframe, "缺字段", "单价")


def test_build_consumption_value_rejects_missing_price_column(small_pricing_dataframe):
    with pytest.raises(ValueError, match="找不到单价字段"):
        ABCAnalyzer.build_consumption_value(small_pricing_dataframe, "年需求量", "缺字段")


def test_build_consumption_value_rejects_non_numeric_columns():
    dataframe = pd.DataFrame({"SKU": ["P1"], "年需求量": ["甲"], "单价": ["乙"]})
    with pytest.raises(ValueError, match="无法转换为有效数值"):
        ABCAnalyzer.build_consumption_value(dataframe, "年需求量", "单价")


def test_generated_value_column_can_drive_classification(small_pricing_dataframe):
    """端到端：生成年消耗金额后再做 ABC 分类。"""
    work = ABCAnalyzer.build_consumption_value(small_pricing_dataframe, "年需求量", "单价")
    result = ABCAnalyzer(work, "年消耗金额", a_rate=0.50, b_rate=0.90).analyze()

    # 降序 80 / 30 / 15 / 5，合计 130 → 累计 0.615 / 0.846 / 0.962 / 1.0
    assert result.counts == {"A": 0, "B": 2, "C": 2}
    assert result.dataframe["SKU"].tolist() == ["S1", "S2", "S3", "S4"]
