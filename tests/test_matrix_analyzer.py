"""ABC × XYZ 交叉矩阵回归基线。

覆盖：3×3 矩阵单元与 SKU 数量、单元金额与占比、按关键字段合并（而非行号对齐）、
一对一校验、缺少价值字段时的退化行为、以及 9 个单元的策略表完整性。
本文件只验证当前行为，不修改算法。
"""

from __future__ import annotations

import pandas as pd
import pytest

from utils.abc_utils import ABCAnalyzer
from utils.matrix_utils import (
    ABC_ORDER,
    CELL_ORDER,
    CELL_STRATEGIES,
    XYZ_ORDER,
    ABCXYZMatrixAnalyzer,
)
from utils.xyz_utils import XYZAnalyzer

MATRIX_PERIOD_COLUMNS = ["1月", "2月", "3月", "4月"]

# 6 行测试数据的人工计算结果
EXPECTED_CELL_COUNTS = {"AX": 2, "AY": 0, "AZ": 0, "BX": 0, "BY": 1, "BZ": 0, "CX": 0, "CY": 1, "CZ": 2}
EXPECTED_CELL_VALUES = {"AX": 0.70, "BY": 0.20, "CY": 0.06, "CZ": 0.04}
EXPECTED_ABC_COUNTS = {"A": 2, "B": 1, "C": 3}
EXPECTED_XYZ_COUNTS = {"X": 2, "Y": 2, "Z": 2}
EXPECTED_UNITS_BY_SKU = {
    "X1": "AX",
    "X2": "AX",
    "Y1": "BY",
    "Y2": "CY",
    "Z1": "CZ",
    "Z2": "CZ",
}


def _abc_result(dataframe: pd.DataFrame):
    return ABCAnalyzer(dataframe, "年消耗金额").analyze()


def _xyz_result(dataframe: pd.DataFrame):
    return XYZAnalyzer(dataframe, MATRIX_PERIOD_COLUMNS).analyze()


@pytest.fixture
def abc_dataframe(matrix_source_dataframe: pd.DataFrame) -> pd.DataFrame:
    return _abc_result(matrix_source_dataframe).dataframe


@pytest.fixture
def xyz_dataframe(matrix_source_dataframe: pd.DataFrame) -> pd.DataFrame:
    return _xyz_result(matrix_source_dataframe).dataframe


@pytest.fixture
def matrix_result(abc_dataframe: pd.DataFrame, xyz_dataframe: pd.DataFrame):
    return ABCXYZMatrixAnalyzer(
        abc_dataframe,
        xyz_dataframe,
        key_column="SKU",
        value_column="年消耗金额",
    ).analyze()


def test_source_classification_matches_manual_calculation(
    abc_dataframe, xyz_dataframe
):
    """先确认输入侧分类正确，矩阵结果才有意义。"""
    abc_counts = abc_dataframe["ABC分类"].value_counts().to_dict()
    xyz_counts = xyz_dataframe["XYZ分类"].value_counts().to_dict()
    assert abc_counts == EXPECTED_ABC_COUNTS
    assert xyz_counts == EXPECTED_XYZ_COUNTS


def test_matrix_cell_counts_match_manual_calculation(matrix_result):
    assert matrix_result.cell_counts == EXPECTED_CELL_COUNTS


def test_matrix_covers_every_sku(matrix_result, matrix_source_dataframe):
    assert sum(matrix_result.cell_counts.values()) == len(matrix_source_dataframe)
    assert len(matrix_result.dataframe) == len(matrix_source_dataframe)


def test_matrix_cell_amounts_and_shares_match_manual_calculation(matrix_result):
    assert matrix_result.total_value == pytest.approx(1000.0)
    assert matrix_result.cell_amounts["AX"] == pytest.approx(700.0)
    assert matrix_result.cell_amounts["BY"] == pytest.approx(200.0)
    assert matrix_result.cell_amounts["CY"] == pytest.approx(60.0)
    assert matrix_result.cell_amounts["CZ"] == pytest.approx(40.0)

    for cell, expected_share in EXPECTED_CELL_VALUES.items():
        assert matrix_result.cell_values[cell] == pytest.approx(expected_share, rel=1e-9)


def test_matrix_shares_sum_to_one(matrix_result):
    assert sum(matrix_result.cell_values.values()) == pytest.approx(1.0, rel=1e-9)
    assert sum(matrix_result.cell_sku_shares.values()) == pytest.approx(1.0, rel=1e-9)


def test_sku_share_is_one_over_total_skus(matrix_result):
    assert matrix_result.cell_sku_shares["AX"] == pytest.approx(2 / 6, rel=1e-12)
    assert matrix_result.cell_sku_shares["BY"] == pytest.approx(1 / 6, rel=1e-12)


def test_each_sku_is_assigned_to_expected_unit(matrix_result):
    units = dict(
        zip(matrix_result.dataframe["SKU"], matrix_result.dataframe["矩阵单元"], strict=True)
    )
    assert units == EXPECTED_UNITS_BY_SKU


def test_matrix_units_are_valid_cells(matrix_result):
    assert set(matrix_result.dataframe["矩阵单元"]).issubset(set(CELL_ORDER))


def test_merge_uses_key_column_not_row_order(
    abc_dataframe, xyz_dataframe, matrix_result
):
    """把 XYZ 结果行序完全颠倒后重新合并，结果必须完全一致。

    若实现依赖行号对齐，本测试会立刻失败。
    """
    shuffled_xyz = xyz_dataframe.iloc[::-1].reset_index(drop=True)
    shuffled = ABCXYZMatrixAnalyzer(
        abc_dataframe,
        shuffled_xyz,
        key_column="SKU",
        value_column="年消耗金额",
    ).analyze()

    assert shuffled.cell_counts == matrix_result.cell_counts
    for cell, amount in matrix_result.cell_amounts.items():
        assert shuffled.cell_amounts[cell] == pytest.approx(amount, rel=1e-12)

    shuffled_units = dict(
        zip(shuffled.dataframe["SKU"], shuffled.dataframe["矩阵单元"], strict=True)
    )
    assert shuffled_units == EXPECTED_UNITS_BY_SKU


def test_merge_is_also_stable_when_abc_rows_are_reversed(
    abc_dataframe, xyz_dataframe, matrix_result
):
    shuffled_abc = abc_dataframe.iloc[::-1].reset_index(drop=True)
    shuffled = ABCXYZMatrixAnalyzer(
        shuffled_abc,
        xyz_dataframe,
        key_column="SKU",
        value_column="年消耗金额",
    ).analyze()

    assert shuffled.cell_counts == matrix_result.cell_counts
    assert shuffled.cell_amounts["AX"] == pytest.approx(
        matrix_result.cell_amounts["AX"], rel=1e-12
    )


def test_duplicate_key_is_rejected(abc_dataframe, xyz_dataframe):
    duplicated = pd.concat([abc_dataframe, abc_dataframe.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="存在重复值"):
        ABCXYZMatrixAnalyzer(
            duplicated, xyz_dataframe, key_column="SKU", value_column="年消耗金额"
        ).analyze()


def test_missing_key_column_is_rejected(abc_dataframe, xyz_dataframe):
    with pytest.raises(ValueError, match="找不到关键字段"):
        ABCXYZMatrixAnalyzer(
            abc_dataframe, xyz_dataframe, key_column="不存在的字段"
        ).analyze()


def test_missing_classification_column_is_rejected(xyz_dataframe):
    without_classification = pd.DataFrame({"SKU": ["X1", "X2"], "金额": [1.0, 2.0]})
    with pytest.raises(ValueError, match="缺少分类列"):
        ABCXYZMatrixAnalyzer(
            without_classification, xyz_dataframe, key_column="SKU"
        ).analyze()


def test_no_matching_keys_is_rejected(abc_dataframe, xyz_dataframe):
    other_abc = abc_dataframe.copy()
    other_abc["SKU"] = ["OTHER1", "OTHER2", "OTHER3", "OTHER4", "OTHER5", "OTHER6"]
    with pytest.raises(ValueError, match="无法按关键字段匹配"):
        ABCXYZMatrixAnalyzer(
            other_abc, xyz_dataframe, key_column="SKU", value_column="年消耗金额"
        ).analyze()


def test_without_value_column_falls_back_to_sku_counts(abc_dataframe, xyz_dataframe):
    """未选择价值字段时，矩阵只统计 SKU 数量，不新增单元金额占比。

    注意：结果中出现的「金额占比」列来自 ABC 分析结果本身（SKU 级价值占比），
    并不是矩阵计算的单元金额占比，使用时需要区分。
    """
    result = ABCXYZMatrixAnalyzer(
        abc_dataframe, xyz_dataframe, key_column="SKU", value_column=None
    ).analyze()

    assert result.has_amount is False
    assert result.value_label == "SKU 数量"
    assert result.cell_counts == EXPECTED_CELL_COUNTS
    assert "_matrix_count" not in result.dataframe.columns
    # 无价值字段时，单元占比退化为 SKU 占比
    assert result.cell_values == result.cell_sku_shares
    # 该列是 ABC 结果自带字段，合计仍为 1
    assert result.dataframe["金额占比"].sum() == pytest.approx(1.0, rel=1e-9)


def test_all_nine_cells_have_strategy_entries(matrix_result):
    assert set(matrix_result.strategies) == set(CELL_ORDER)
    assert set(CELL_STRATEGIES) == set(CELL_ORDER)
    for cell in CELL_ORDER:
        strategy = matrix_result.strategies[cell]
        assert strategy["title"]
        assert strategy["priority"]
        assert strategy["action"]
        assert strategy["target"]


def test_rows_are_sorted_by_unit_then_value_descending(matrix_result):
    units = matrix_result.dataframe["矩阵单元"].tolist()
    assert units == sorted(units)

    for cell in CELL_ORDER:
        values = matrix_result.dataframe.loc[
            matrix_result.dataframe["矩阵单元"] == cell, "年消耗金额"
        ].tolist()
        assert values == sorted(values, reverse=True)


@pytest.mark.parametrize("cell", CELL_ORDER)
def test_cell_name_is_abc_then_xyz(cell, matrix_result):
    """单元名必须是 ABC 字母在前、XYZ 字母在后。"""
    assert cell[0] in ABC_ORDER
    assert cell[1] in XYZ_ORDER
    assert cell in matrix_result.cell_counts


def test_recommend_key_column_prefers_sku():
    assert ABCXYZMatrixAnalyzer.recommend_key_column(["仓库", "SKU", "金额"]) == "SKU"
    assert ABCXYZMatrixAnalyzer.recommend_key_column(["物料编码", "名称"]) == "物料编码"


def test_recommend_key_column_falls_back_to_first_column():
    assert ABCXYZMatrixAnalyzer.recommend_key_column(["甲", "乙"]) == "甲"
    assert ABCXYZMatrixAnalyzer.recommend_key_column([]) == ""
