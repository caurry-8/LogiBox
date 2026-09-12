"""安全库存 / ROP 回归基线。

安全库存公式当前直接实现在 pages/safety_page.py 的 SafetyPage.calculate() 中，
没有独立的 utils 模块。按任务要求，测试通过页面实例调用，不重构生产代码。

公式：
    安全库存 = z × σ × sqrt(L)
    ROP      = 平均需求 × L + 安全库存
"""

from __future__ import annotations

import math

import pytest

from pages.safety_page import SafetyPage

# 已知结果：mean=100, std=20, L=5, z=1.65
# 安全库存 = 1.65 × 20 × sqrt(5) = 73.7905... → 73.79
# ROP      = 100 × 5 + 73.79 = 573.79
KNOWN_MEAN = 100.0
KNOWN_STD = 20.0
KNOWN_LEAD = 5.0
KNOWN_Z = 1.65
KNOWN_SAFETY = 73.79
KNOWN_ROP = 573.79


def _fill_and_calculate(page: SafetyPage, mean: str, std: str, lead: str, z: str) -> None:
    page.mean.setText(mean)
    page.std.setText(std)
    page.lead.setText(lead)
    page.z.setText(z)
    page.calculate()


def test_safety_stock_matches_known_result():
    page = SafetyPage()
    _fill_and_calculate(page, "100", "20", "5", "1.65")

    assert page.last_result["安全库存"] == pytest.approx(KNOWN_SAFETY, abs=0.01)
    assert page.last_result["再订货点 ROP"] == pytest.approx(KNOWN_ROP, abs=0.01)
    assert page.last_result["Z 值"] == pytest.approx(KNOWN_Z)


def test_safety_stock_matches_independent_formula():
    """页面结果应与独立书写的 z × σ × sqrt(L) 一致。"""
    mean, std, lead, z = 250.0, 35.0, 7.0, 2.33
    expected_safety = z * std * math.sqrt(lead)
    expected_rop = mean * lead + expected_safety

    page = SafetyPage()
    _fill_and_calculate(page, str(mean), str(std), str(lead), str(z))

    assert page.last_result["安全库存"] == pytest.approx(expected_safety, abs=0.01)
    assert page.last_result["再订货点 ROP"] == pytest.approx(expected_rop, abs=0.01)


def test_cards_show_calculated_values():
    page = SafetyPage()
    _fill_and_calculate(page, "100", "20", "5", "1.65")

    assert page.safety_card.value_label.text() == "73.79"
    assert page.rop_card.value_label.text() == "573.79"


def test_result_is_published_to_data_store(sample_store):
    page = SafetyPage(store=sample_store)
    _fill_and_calculate(page, "100", "20", "5", "1.65")

    assert sample_store.has_analysis("safety") is True
    stored = sample_store.get_analysis("safety")
    assert stored["安全库存"] == pytest.approx(KNOWN_SAFETY, abs=0.01)
    assert stored["再订货点 ROP"] == pytest.approx(KNOWN_ROP, abs=0.01)


def test_works_without_data_store():
    """store 为 None 时不应抛异常（页面构造函数默认允许）。"""
    page = SafetyPage(store=None)
    _fill_and_calculate(page, "100", "20", "5", "1.65")
    assert page.last_result["安全库存"] == pytest.approx(KNOWN_SAFETY, abs=0.01)


def test_zero_service_factor_gives_zero_safety_stock():
    """边界：z = 0 时安全库存为 0，ROP 退化为平均需求 × 提前期。"""
    page = SafetyPage()
    _fill_and_calculate(page, "100", "20", "5", "0")

    assert page.last_result["安全库存"] == pytest.approx(0.0)
    assert page.last_result["再订货点 ROP"] == pytest.approx(100 * 5)


def test_zero_lead_time_gives_zero_safety_stock_and_rop():
    """边界：提前期为 0 时安全库存与 ROP 均为 0（当前实现允许 0）。"""
    page = SafetyPage()
    _fill_and_calculate(page, "100", "20", "0", "1.65")

    assert page.last_result["安全库存"] == pytest.approx(0.0)
    assert page.last_result["再订货点 ROP"] == pytest.approx(0.0)


def test_zero_demand_std_gives_safety_stock_from_mean_only():
    """边界：需求标准差为 0 时安全库存为 0，ROP = 平均需求 × 提前期。"""
    page = SafetyPage()
    _fill_and_calculate(page, "100", "0", "5", "1.65")

    assert page.last_result["安全库存"] == pytest.approx(0.0)
    assert page.last_result["再订货点 ROP"] == pytest.approx(500.0)


def test_zero_demand_is_allowed():
    """边界：平均需求为 0 不被视为非法（校验只拦截负数）。"""
    page = SafetyPage()
    _fill_and_calculate(page, "0", "20", "5", "1.65")

    assert page.last_result["安全库存"] == pytest.approx(
        1.65 * 20 * math.sqrt(5), abs=0.01
    )


@pytest.mark.parametrize(
    ("mean", "std", "lead", "z", "expected_fragment"),
    [
        ("-1", "20", "5", "1.65", "输入值不能为负数。"),
        ("100", "-20", "5", "1.65", "输入值不能为负数。"),
        ("100", "20", "-5", "1.65", "输入值不能为负数。"),
        ("100", "20", "5", "-1.65", "输入值不能为负数。"),
    ],
)
def test_negative_inputs_are_rejected_with_message(
    message_box_recorder, mean, std, lead, z, expected_fragment
):
    page = SafetyPage()
    _fill_and_calculate(page, mean, std, lead, z)

    assert message_box_recorder.calls, "应弹出一个提示"
    assert expected_fragment in message_box_recorder.texts[0]
    assert not hasattr(page, "last_result"), "非法输入不应产生结果"


@pytest.mark.parametrize("invalid_text", ["", "abc", "  ", "1,65"])
def test_non_numeric_inputs_are_rejected_with_message(message_box_recorder, invalid_text):
    page = SafetyPage()
    _fill_and_calculate(page, invalid_text, "20", "5", "1.65")

    assert message_box_recorder.calls, "应弹出一个提示"
    assert not hasattr(page, "last_result"), "非法输入不应产生结果"
