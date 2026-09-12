"""XYZ 需求稳定性分析回归基线。

覆盖：示例数据 X/Y/Z 数量、CV 计算口径（ddof=0）、分类阈值语义、
以及 V3.5.0-A-02 引入的数据可信语义。

数据可信规则（V3.5.0-A-02）：
- 真实 0 需求是合法数据，正常参与 XYZ 分析；
- 缺失值 NaN 不再被 fillna(0)，该 SKU 不参与正常 XYZ 分类，状态标记为 missing；
- Inf / -Inf 属于非法数值，状态标记为 invalid；
- 周期字段不存在时抛出明确的中文 ValueError；
- 只有 valid 的 SKU 会得到 X / Y / Z 分类，其余为「未分类」。

关键断言：真实 0 ≠ 缺失。两者必须产生不同的数据质量状态。
"""

from __future__ import annotations

import math

import pandas as pd
import pytest

from utils.xyz_utils import (
    QUALITY_COLUMN,
    STATUS_INVALID,
    STATUS_MISSING,
    STATUS_VALID,
    UNCLASSIFIED,
    XYZAnalyzer,
)

# 示例数据按 CV 分类结果：X=4（A001 / A002 / A004 / A007），Y=6，Z=0
SAMPLE_COUNTS = {"X": 4, "Y": 6, "Z": 0}
SAMPLE_MEAN_CV = 0.121856
# A001 月度需求 [1950, 1980, 2020, 1970, 2040, 2040]：均值 2000，总体标准差 35.1190，CV 0.01756
A001_CV = 0.01756
# A010 月度需求 [160, 120, 180, 110, 170, 160]：均值 150，总体标准差 25.8199，CV 0.17213
A010_CV = 0.17213

ALL_VALID_STATUS = {STATUS_VALID: 0, STATUS_MISSING: 0, STATUS_INVALID: 0}


def _status_counts(valid: int = 0, missing: int = 0, invalid: int = 0) -> dict[str, int]:
    return {STATUS_VALID: valid, STATUS_MISSING: missing, STATUS_INVALID: invalid}


# --------------------------------------------------------------------------- #
# 一、原有正常数据行为保持不变
# --------------------------------------------------------------------------- #


def test_sample_data_classifies_into_x4_y6_z0(sample_dataframe, sample_period_columns):
    result = XYZAnalyzer(sample_dataframe, sample_period_columns).analyze()
    assert result.counts == SAMPLE_COUNTS


def test_sample_inventory_classification_is_unchanged(sample_dataframe, sample_period_columns):
    """示例数据在 V3.5.0-A-02 之后必须保持与 V3.4.0 相同的 X/Y/Z 结果。"""
    result = XYZAnalyzer(sample_dataframe, sample_period_columns).analyze()

    assert result.counts == {"X": 4, "Y": 6, "Z": 0}
    assert result.mean_cv == pytest.approx(SAMPLE_MEAN_CV, abs=0.0005)
    assert result.status_counts == _status_counts(valid=10)
    assert set(result.dataframe[QUALITY_COLUMN]) == {STATUS_VALID}
    assert UNCLASSIFIED not in set(result.dataframe["XYZ分类"])


def test_sample_classification_covers_every_row(sample_dataframe, sample_period_columns):
    result = XYZAnalyzer(sample_dataframe, sample_period_columns).analyze()
    assert sum(result.counts.values()) == len(sample_dataframe)
    assert len(result.dataframe) == len(sample_dataframe)


def test_sample_mean_cv_matches_manual_calculation(sample_dataframe, sample_period_columns):
    result = XYZAnalyzer(sample_dataframe, sample_period_columns).analyze()
    assert result.mean_cv == pytest.approx(SAMPLE_MEAN_CV, abs=0.0005)


def test_specific_sku_cv_values_match_manual_calculation(
    sample_dataframe, sample_period_columns
):
    result = XYZAnalyzer(sample_dataframe, sample_period_columns).analyze()
    cv_by_sku = dict(
        zip(result.dataframe["SKU"], result.dataframe["变异系数CV"], strict=True)
    )
    assert cv_by_sku["A001"] == pytest.approx(A001_CV, abs=1e-5)
    assert cv_by_sku["A010"] == pytest.approx(A010_CV, abs=1e-5)


def test_specific_sku_classification(sample_dataframe, sample_period_columns):
    """核对稳定 SKU 归属 X 类、波动 SKU 归属 Y 类。"""
    result = XYZAnalyzer(sample_dataframe, sample_period_columns).analyze()
    assignment = dict(
        zip(result.dataframe["SKU"], result.dataframe["XYZ分类"], strict=True)
    )
    for stable_sku in ("A001", "A002", "A004", "A007"):
        assert assignment[stable_sku] == "X"
    for fluctuating_sku in ("A003", "A005", "A006", "A008", "A009", "A010"):
        assert assignment[fluctuating_sku] == "Y"


def test_average_and_std_columns_match_manual_calculation(
    sample_dataframe, sample_period_columns
):
    result = XYZAnalyzer(sample_dataframe, sample_period_columns).analyze()
    row = result.dataframe[result.dataframe["SKU"] == "A001"].iloc[0]

    assert row["平均需求"] == pytest.approx(2000.0)
    assert row["需求标准差"] == pytest.approx(math.sqrt(7400 / 6), rel=1e-12)


def test_complete_data_classification_is_unchanged():
    """完整无缺失数据必须得到与 V3.4.0 一致的 X/Y/Z 结果。"""
    dataframe = pd.DataFrame(
        {
            "SKU": ["S_X", "S_X2", "S_Y", "S_Z"],
            "1月": [10, 0, 100, 10],
            "2月": [10, 0, 120, 50],
            "3月": [10, 0, 80, 20],
        }
    )
    result = XYZAnalyzer(dataframe, ["1月", "2月", "3月"]).analyze()

    # [100, 120, 80]：均值 100、总体标准差 16.3299、CV 0.1633 → Y
    # [10, 50, 20]：均值 26.6667、总体标准差 16.9967、CV 0.6374 → Z
    assert result.counts == {"X": 2, "Y": 1, "Z": 1}
    assert result.status_counts == _status_counts(valid=4)
    assert result.classified_count == 4


def test_coefficient_of_variation_uses_population_std():
    """CV 使用总体标准差（ddof=0）：[10, 20] → 均值 15、标准差 5、CV = 1/3。"""
    dataframe = pd.DataFrame({"SKU": ["V1"], "1月": [10], "2月": [20]})
    result = XYZAnalyzer(dataframe, ["1月", "2月"]).analyze()

    row = result.dataframe.iloc[0]
    assert row["平均需求"] == pytest.approx(15.0)
    assert row["需求标准差"] == pytest.approx(5.0)
    assert row["变异系数CV"] == pytest.approx(1 / 3, rel=1e-12)
    assert row["XYZ分类"] == "Z"


def test_threshold_boundaries_are_inclusive():
    """分类使用 `CV <= 阈值` 判定，正好等于阈值时归入较稳定类别。"""
    # 均值 100、总体标准差 10 → CV = 0.10 恰好等于 X 类阈值
    dataframe = pd.DataFrame({"SKU": ["T1"], "1月": [90], "2月": [110]})
    result = XYZAnalyzer(dataframe, ["1月", "2月"], x_rate=0.10, y_rate=0.25).analyze()
    assert result.dataframe.iloc[0]["变异系数CV"] == pytest.approx(0.10, rel=1e-12)
    assert result.dataframe.iloc[0]["XYZ分类"] == "X"


def test_custom_thresholds_change_classification():
    # 均值 100、总体标准差 10 → CV = 0.10
    dataframe = pd.DataFrame({"SKU": ["T1"], "1月": [90], "2月": [110]})
    strict = XYZAnalyzer(dataframe, ["1月", "2月"], x_rate=0.05, y_rate=0.08).analyze()
    loose = XYZAnalyzer(dataframe, ["1月", "2月"], x_rate=0.01, y_rate=0.20).analyze()

    assert strict.counts == {"X": 0, "Y": 0, "Z": 1}
    assert loose.counts == {"X": 0, "Y": 1, "Z": 0}


def test_result_dataframe_keeps_source_columns_and_adds_analysis_columns():
    dataframe = pd.DataFrame(
        {"SKU": ["R1"], "仓库": ["西安仓"], "1月": [10], "2月": [20]}
    )
    result = XYZAnalyzer(dataframe, ["1月", "2月"]).analyze()

    for column in ("SKU", "仓库", "1月", "2月"):
        assert column in result.dataframe.columns
    for column in ("平均需求", "需求标准差", "变异系数CV", QUALITY_COLUMN, "XYZ分类"):
        assert column in result.dataframe.columns


def test_source_dataframe_is_not_mutated():
    dataframe = pd.DataFrame({"SKU": ["R1"], "1月": [10], "2月": [20]})
    original = dataframe.copy(deep=True)
    XYZAnalyzer(dataframe, ["1月", "2月"]).analyze()

    pd.testing.assert_frame_equal(dataframe, original)


def test_source_dataframe_with_missing_values_is_not_mutated():
    """含缺失值时也不能就地填充，输入必须保持原样。"""
    dataframe = pd.DataFrame({"SKU": ["R1"], "1月": [10], "2月": [None]})
    original = dataframe.copy(deep=True)
    XYZAnalyzer(dataframe, ["1月", "2月"]).analyze()

    pd.testing.assert_frame_equal(dataframe, original)
    assert dataframe["2月"].isna().all()


# --------------------------------------------------------------------------- #
# 二、真实 0 需求：合法数据，正常参与分类
# --------------------------------------------------------------------------- #


def test_real_zero_demand_is_valid_and_classified_x():
    """全部周期真实为 0 属于合法数据，仍按 CV=0 归入 X 类。"""
    dataframe = pd.DataFrame({"SKU": ["Z1"], "1月": [0], "2月": [0], "3月": [0]})
    result = XYZAnalyzer(dataframe, ["1月", "2月", "3月"]).analyze()

    row = result.dataframe.iloc[0]
    assert row[QUALITY_COLUMN] == STATUS_VALID
    assert row["平均需求"] == pytest.approx(0.0)
    assert row["需求标准差"] == pytest.approx(0.0)
    assert row["变异系数CV"] == pytest.approx(0.0)
    assert row["XYZ分类"] == "X"
    assert result.counts == {"X": 1, "Y": 0, "Z": 0}


def test_real_zero_demand_is_not_treated_as_missing():
    """核心断言：真实 0 的数据质量状态是 valid，不是 missing。"""
    dataframe = pd.DataFrame({"SKU": ["Z1"], "1月": [0], "2月": [0], "3月": [0]})
    result = XYZAnalyzer(dataframe, ["1月", "2月", "3月"]).analyze()

    assert result.status_counts == _status_counts(valid=1)
    assert result.dataframe.iloc[0][QUALITY_COLUMN] != STATUS_MISSING


def test_zero_demand_and_all_missing_produce_different_status():
    """边界数据：mean=0 且真实全 0 与全部缺失，必须产生不同的数据状态。"""
    dataframe = pd.DataFrame(
        {
            "SKU": ["ZEROS", "MISSING"],
            "1月": [0, None],
            "2月": [0, None],
            "3月": [0, None],
        }
    )
    result = XYZAnalyzer(dataframe, ["1月", "2月", "3月"]).analyze()
    by_sku = result.dataframe.set_index("SKU")

    assert by_sku.loc["ZEROS", QUALITY_COLUMN] == STATUS_VALID
    assert by_sku.loc["MISSING", QUALITY_COLUMN] == STATUS_MISSING
    assert by_sku.loc["ZEROS", "XYZ分类"] == "X"
    assert by_sku.loc["MISSING", "XYZ分类"] == UNCLASSIFIED

    # 只有真实全 0 的 SKU 进入分类统计
    assert result.counts == {"X": 1, "Y": 0, "Z": 0}
    assert result.status_counts == _status_counts(valid=1, missing=1)


def test_partial_real_zero_is_valid():
    """部分月份真实为 0 也是合法数据，不视为缺失。"""
    dataframe = pd.DataFrame({"SKU": ["P0"], "1月": [0], "2月": [20], "3月": [0]})
    result = XYZAnalyzer(dataframe, ["1月", "2月", "3月"]).analyze()

    row = result.dataframe.iloc[0]
    assert row[QUALITY_COLUMN] == STATUS_VALID
    # 均值 6.6667、总体标准差 9.4281、CV 1.4142 → Z
    assert row["平均需求"] == pytest.approx(20 / 3)
    assert row["XYZ分类"] == "Z"


# --------------------------------------------------------------------------- #
# 三、缺失值：不参与分类，不得静默变成 0
# --------------------------------------------------------------------------- #


def test_partial_missing_sku_is_marked_missing_and_excluded():
    """部分月份缺失：不得 fillna(0)，该 SKU 不参与正常 XYZ 分类。"""
    dataframe = pd.DataFrame({"SKU": ["M1"], "1月": [10], "2月": [None], "3月": [20]})
    result = XYZAnalyzer(dataframe, ["1月", "2月", "3月"]).analyze()
    row = result.dataframe.iloc[0]

    assert row[QUALITY_COLUMN] == STATUS_MISSING
    assert row["XYZ分类"] == UNCLASSIFIED
    # 关键：缺失没有被当成 0 —— 若 fillna(0)，均值会是 10
    assert pd.isna(row["平均需求"])
    assert pd.isna(row["需求标准差"])
    assert pd.isna(row["变异系数CV"])

    assert result.counts == {"X": 0, "Y": 0, "Z": 0}
    assert result.status_counts == _status_counts(missing=1)


def test_partial_missing_sku_is_not_silently_zeroed():
    """反向断言：含缺失的 SKU 不会被算成 CV=0 的稳定需求。"""
    dataframe = pd.DataFrame({"SKU": ["M1"], "1月": [10], "2月": [None], "3月": [20]})
    result = XYZAnalyzer(dataframe, ["1月", "2月", "3月"]).analyze()
    row = result.dataframe.iloc[0]

    assert row["XYZ分类"] != "X"
    assert not row["变异系数CV"] == 0
    assert row["平均需求"] != 0


def test_all_missing_sku_is_marked_missing_and_not_x():
    """整行周期全部缺失：不得归入 X 类。"""
    dataframe = pd.DataFrame(
        {
            "SKU": ["STABLE", "MISSING"],
            "1月": [10, None],
            "2月": [10, None],
            "3月": [10, None],
        }
    )
    result = XYZAnalyzer(dataframe, ["1月", "2月", "3月"]).analyze()
    by_sku = result.dataframe.set_index("SKU")

    assert by_sku.loc["STABLE", QUALITY_COLUMN] == STATUS_VALID
    assert by_sku.loc["STABLE", "XYZ分类"] == "X"

    assert by_sku.loc["MISSING", QUALITY_COLUMN] == STATUS_MISSING
    assert by_sku.loc["MISSING", "XYZ分类"] == UNCLASSIFIED
    assert by_sku.loc["MISSING", "XYZ分类"] != "X"
    assert pd.isna(by_sku.loc["MISSING", "变异系数CV"])

    # 只有真实稳定的 SKU 计入 X 类
    assert result.counts == {"X": 1, "Y": 0, "Z": 0}
    assert result.status_counts == _status_counts(valid=1, missing=1)


def test_missing_sku_does_not_affect_other_skus():
    """增加一个缺失 SKU 不应改变其他 SKU 的 CV 与分类。"""
    clean = pd.DataFrame({"SKU": ["A"], "1月": [100], "2月": [120], "3月": [80]})
    dirty = pd.DataFrame(
        {
            "SKU": ["A", "B"],
            "1月": [100, None],
            "2月": [120, 50],
            "3月": [80, None],
        }
    )
    clean_result = XYZAnalyzer(clean, ["1月", "2月", "3月"]).analyze()
    dirty_result = XYZAnalyzer(dirty, ["1月", "2月", "3月"]).analyze()

    clean_row = clean_result.dataframe.iloc[0]
    dirty_row = dirty_result.dataframe[dirty_result.dataframe["SKU"] == "A"].iloc[0]

    assert dirty_row["变异系数CV"] == pytest.approx(clean_row["变异系数CV"], rel=1e-12)
    assert dirty_row["XYZ分类"] == clean_row["XYZ分类"]


def test_mean_cv_is_computed_over_valid_rows_only():
    """平均 CV 只统计 valid 的 SKU，不被缺失行稀释。"""
    dataframe = pd.DataFrame(
        {
            "SKU": ["A", "B"],
            "1月": [100, None],
            "2月": [200, None],
        }
    )
    result = XYZAnalyzer(dataframe, ["1月", "2月"]).analyze()

    # A：[100, 200] → 均值 150、总体标准差 50、CV = 1/3
    assert result.mean_cv == pytest.approx(1 / 3, rel=1e-12)


# --------------------------------------------------------------------------- #
# 四、Inf / -Inf：非法数值
# --------------------------------------------------------------------------- #


def test_positive_infinite_value_marks_sku_invalid():
    dataframe = pd.DataFrame(
        {
            "SKU": ["INF", "OK"],
            "1月": [float("inf"), 10],
            "2月": [10, 10],
            "3月": [20, 10],
        }
    )
    result = XYZAnalyzer(dataframe, ["1月", "2月", "3月"]).analyze()
    by_sku = result.dataframe.set_index("SKU")

    assert by_sku.loc["INF", QUALITY_COLUMN] == STATUS_INVALID
    assert by_sku.loc["INF", "XYZ分类"] == UNCLASSIFIED
    assert pd.isna(by_sku.loc["INF", "变异系数CV"])

    assert by_sku.loc["OK", QUALITY_COLUMN] == STATUS_VALID
    assert by_sku.loc["OK", "XYZ分类"] == "X"

    assert result.counts == {"X": 1, "Y": 0, "Z": 0}
    assert result.status_counts == _status_counts(valid=1, invalid=1)


def test_negative_infinite_value_marks_sku_invalid_not_negative_error():
    """-Inf 属于非法数值（invalid），不应触发「不能包含负数」的全局错误。"""
    dataframe = pd.DataFrame(
        {
            "SKU": ["NINF", "OK"],
            "1月": [float("-inf"), 10],
            "2月": [10, 10],
            "3月": [20, 10],
        }
    )
    result = XYZAnalyzer(dataframe, ["1月", "2月", "3月"]).analyze()
    by_sku = result.dataframe.set_index("SKU")

    assert by_sku.loc["NINF", QUALITY_COLUMN] == STATUS_INVALID
    assert by_sku.loc["NINF", "XYZ分类"] == UNCLASSIFIED
    assert by_sku.loc["OK", "XYZ分类"] == "X"
    assert result.status_counts == _status_counts(valid=1, invalid=1)


def test_infinite_value_does_not_affect_other_skus_cv():
    clean = pd.DataFrame({"SKU": ["A"], "1月": [100], "2月": [120], "3月": [80]})
    dirty = pd.DataFrame(
        {
            "SKU": ["A", "B"],
            "1月": [100, float("inf")],
            "2月": [120, 50],
            "3月": [80, 60],
        }
    )
    clean_result = XYZAnalyzer(clean, ["1月", "2月", "3月"]).analyze()
    dirty_result = XYZAnalyzer(dirty, ["1月", "2月", "3月"]).analyze()

    dirty_row = dirty_result.dataframe[dirty_result.dataframe["SKU"] == "A"].iloc[0]
    assert dirty_row["变异系数CV"] == pytest.approx(
        clean_result.dataframe.iloc[0]["变异系数CV"], rel=1e-12
    )
    assert dirty_result.mean_cv == pytest.approx(clean_result.mean_cv, rel=1e-12)


def test_invalid_status_takes_precedence_over_missing():
    """同一行既有非法值又有缺失时，判定为 invalid（更严重）。"""
    dataframe = pd.DataFrame(
        {"SKU": ["BOTH"], "1月": [float("inf")], "2月": [None], "3月": [10]}
    )
    result = XYZAnalyzer(dataframe, ["1月", "2月", "3月"]).analyze()

    assert result.dataframe.iloc[0][QUALITY_COLUMN] == STATUS_INVALID
    assert result.status_counts == _status_counts(invalid=1)


# --------------------------------------------------------------------------- #
# 五、状态统计与分类计数
# --------------------------------------------------------------------------- #


def test_counts_only_include_classified_skus():
    dataframe = pd.DataFrame(
        {
            "SKU": ["VALID", "MISSING", "INVALID"],
            "1月": [10, None, float("inf")],
            "2月": [10, None, 10],
            "3月": [10, None, 20],
        }
    )
    result = XYZAnalyzer(dataframe, ["1月", "2月", "3月"]).analyze()

    assert result.counts == {"X": 1, "Y": 0, "Z": 0}
    assert sum(result.counts.values()) == 1
    assert result.classified_count == 1
    assert len(result.dataframe) == 3


def test_status_counts_sum_to_row_count():
    dataframe = pd.DataFrame(
        {
            "SKU": ["VALID", "MISSING", "INVALID", "VALID2"],
            "1月": [10, None, float("inf"), 100],
            "2月": [10, None, 10, 200],
            "3月": [10, None, 20, 150],
        }
    )
    result = XYZAnalyzer(dataframe, ["1月", "2月", "3月"]).analyze()

    assert sum(result.status_counts.values()) == len(dataframe)
    assert result.status_counts == _status_counts(valid=2, missing=1, invalid=1)
    assert result.classified_count == 2


def test_status_counts_keys_are_stable():
    dataframe = pd.DataFrame({"SKU": ["A"], "1月": [10], "2月": [20]})
    result = XYZAnalyzer(dataframe, ["1月", "2月"]).analyze()

    assert set(result.status_counts) == {STATUS_VALID, STATUS_MISSING, STATUS_INVALID}
    assert ALL_VALID_STATUS.keys() == result.status_counts.keys()


def test_all_valid_dataset_reports_no_quality_issues():
    dataframe = pd.DataFrame(
        {"SKU": ["A", "B"], "1月": [10, 100], "2月": [20, 100], "3月": [30, 100]}
    )
    result = XYZAnalyzer(dataframe, ["1月", "2月", "3月"]).analyze()

    assert result.status_counts == _status_counts(valid=2)
    assert result.classified_count == len(dataframe)


def test_data_quality_column_is_added_to_result():
    dataframe = pd.DataFrame({"SKU": ["A"], "1月": [10], "2月": [20]})
    result = XYZAnalyzer(dataframe, ["1月", "2月"]).analyze()

    assert QUALITY_COLUMN in result.dataframe.columns
    assert result.dataframe.iloc[0][QUALITY_COLUMN] == STATUS_VALID


# --------------------------------------------------------------------------- #
# 六、错误处理
# --------------------------------------------------------------------------- #


def test_missing_period_column_raises_chinese_value_error():
    """周期字段不存在时，必须抛出明确的中文 ValueError 并列出缺失字段。"""
    dataframe = pd.DataFrame({"SKU": ["K1"], "1月": [10], "2月": [20]})

    with pytest.raises(ValueError) as excinfo:
        XYZAnalyzer(dataframe, ["1月", "不存在的月份", "也不存在的月份"]).analyze()

    message = str(excinfo.value)
    assert "缺少" in message
    assert "不存在的月份" in message
    assert "也不存在的月份" in message


def test_missing_period_column_error_lists_only_missing_fields():
    dataframe = pd.DataFrame({"SKU": ["K1"], "1月": [10], "2月": [20]})

    with pytest.raises(ValueError, match="缺少") as excinfo:
        XYZAnalyzer(dataframe, ["1月", "缺A"]).analyze()

    message = str(excinfo.value)
    assert "缺A" in message
    assert "1月" not in message
    assert "2月" not in message


def test_less_than_two_periods_is_rejected():
    dataframe = pd.DataFrame({"SKU": ["P1"], "1月": [10]})
    with pytest.raises(ValueError, match="至少需要选择 2 个历史需求周期字段"):
        XYZAnalyzer(dataframe, ["1月"]).analyze()


@pytest.mark.parametrize(("x_rate", "y_rate"), [(0.30, 0.20), (0.20, 0.20), (0.0, 0.20)])
def test_invalid_thresholds_are_rejected(x_rate, y_rate):
    dataframe = pd.DataFrame({"SKU": ["P1"], "1月": [10], "2月": [20]})
    with pytest.raises(ValueError, match="阈值必须满足"):
        XYZAnalyzer(dataframe, ["1月", "2月"], x_rate, y_rate).analyze()


def test_non_numeric_period_columns_are_rejected():
    dataframe = pd.DataFrame({"SKU": ["N1"], "1月": ["甲"], "2月": ["乙"]})
    with pytest.raises(ValueError, match="没有可用数值"):
        XYZAnalyzer(dataframe, ["1月", "2月"]).analyze()


def test_negative_demand_is_rejected():
    """真实负数仍是全局错误，行为与 V3.4.0 一致。"""
    dataframe = pd.DataFrame({"SKU": ["G1"], "1月": [10], "2月": [-20]})
    with pytest.raises(ValueError, match="不能包含负数"):
        XYZAnalyzer(dataframe, ["1月", "2月"]).analyze()


def test_negative_demand_is_still_rejected_when_other_rows_are_missing():
    dataframe = pd.DataFrame(
        {"SKU": ["G1", "M1"], "1月": [10, None], "2月": [-20, None]}
    )
    with pytest.raises(ValueError, match="不能包含负数"):
        XYZAnalyzer(dataframe, ["1月", "2月"]).analyze()
