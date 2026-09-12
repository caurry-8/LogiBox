"""EOQ 经济订货批量回归基线。

覆盖：标准公式结果、已知结果回归、EOQ 最优性数学性质、边界与非法输入。
本文件不修改任何生产代码。
"""

from __future__ import annotations

import math

import pytest

from utils.eoq_utils import EOQCalculator

# 已知结果：D=10000, S=200, H=5
# EOQ = sqrt(2 × 10000 × 200 / 5) = sqrt(800000) = 894.4271909999159
KNOWN_DEMAND = 10000.0
KNOWN_ORDER_COST = 200.0
KNOWN_HOLD_COST = 5.0
KNOWN_EOQ = 894.43


def test_eoq_matches_known_result():
    """已知输入应得到已知的 EOQ 结果 894.43。"""
    calculator = EOQCalculator(KNOWN_DEMAND, KNOWN_ORDER_COST, KNOWN_HOLD_COST)
    assert calculator.eoq() == pytest.approx(KNOWN_EOQ, abs=0.01)


def test_eoq_equals_independent_formula():
    """EOQ 应与独立书写的公式 sqrt(2DS/H) 一致。"""
    demand, order_cost, hold_cost = 1200.0, 150.0, 8.0
    expected = math.sqrt(2 * demand * order_cost / hold_cost)
    calculator = EOQCalculator(demand, order_cost, hold_cost)
    assert calculator.eoq() == pytest.approx(expected, rel=1e-12)


def test_average_inventory_is_half_of_eoq():
    calculator = EOQCalculator(KNOWN_DEMAND, KNOWN_ORDER_COST, KNOWN_HOLD_COST)
    assert calculator.average_inventory() == pytest.approx(calculator.eoq() / 2, rel=1e-12)


def test_order_times_equals_demand_over_eoq():
    calculator = EOQCalculator(KNOWN_DEMAND, KNOWN_ORDER_COST, KNOWN_HOLD_COST)
    assert calculator.order_times() == pytest.approx(
        KNOWN_DEMAND / calculator.eoq(), rel=1e-12
    )


def test_order_cycle_is_365_days_divided_by_order_times():
    calculator = EOQCalculator(KNOWN_DEMAND, KNOWN_ORDER_COST, KNOWN_HOLD_COST)
    assert calculator.order_cycle() == pytest.approx(
        365 / calculator.order_times(), rel=1e-12
    )


def test_total_cost_equals_ordering_cost_plus_holding_cost():
    calculator = EOQCalculator(KNOWN_DEMAND, KNOWN_ORDER_COST, KNOWN_HOLD_COST)
    total = calculator.total_cost()
    parts = calculator.ordering_cost() + calculator.holding_cost()
    assert total == pytest.approx(parts, rel=1e-12)


def test_ordering_cost_equals_holding_cost_at_eoq():
    """EOQ 的定义性质：在该批量下年订货成本与年持有成本相等。"""
    calculator = EOQCalculator(KNOWN_DEMAND, KNOWN_ORDER_COST, KNOWN_HOLD_COST)
    assert calculator.ordering_cost() == pytest.approx(
        calculator.holding_cost(), rel=1e-9
    )


def test_report_contains_all_expected_metrics():
    report = EOQCalculator(KNOWN_DEMAND, KNOWN_ORDER_COST, KNOWN_HOLD_COST).report()
    assert set(report) == {
        "EOQ",
        "平均库存",
        "订货次数",
        "订货周期",
        "年订货成本",
        "年库存持有成本",
        "总成本",
    }


def test_report_rounds_values_to_two_decimals():
    report = EOQCalculator(KNOWN_DEMAND, KNOWN_ORDER_COST, KNOWN_HOLD_COST).report()
    assert report["EOQ"] == KNOWN_EOQ
    assert report["平均库存"] == round(KNOWN_EOQ / 2, 2)
    assert report["总成本"] == pytest.approx(
        report["年订货成本"] + report["年库存持有成本"], abs=0.01
    )


@pytest.mark.parametrize(
    ("demand", "order_cost", "hold_cost", "expected_message"),
    [
        (0.0, 200.0, 5.0, "年需求量必须大于 0。"),
        (-1.0, 200.0, 5.0, "年需求量必须大于 0。"),
        (10000.0, 0.0, 5.0, "每次订货成本必须大于 0。"),
        (10000.0, -5.0, 5.0, "每次订货成本必须大于 0。"),
        (10000.0, 200.0, 0.0, "单位持有成本必须大于 0。"),
        (10000.0, 200.0, -1.0, "单位持有成本必须大于 0。"),
    ],
)
def test_eoq_rejects_non_positive_inputs(demand, order_cost, hold_cost, expected_message):
    calculator = EOQCalculator(demand, order_cost, hold_cost)
    with pytest.raises(ValueError) as excinfo:
        calculator.eoq()
    assert str(excinfo.value) == expected_message


def test_validate_raises_for_non_positive_demand():
    calculator = EOQCalculator(0.0, 200.0, 5.0)
    with pytest.raises(ValueError, match="年需求量必须大于 0"):
        calculator.validate()


def test_minimum_valid_inputs_still_compute():
    """边界：三个参数都取最小值 1 时应能正常计算。"""
    calculator = EOQCalculator(1.0, 1.0, 1.0)
    assert calculator.eoq() == pytest.approx(math.sqrt(2), rel=1e-12)
