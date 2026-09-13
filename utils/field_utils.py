"""历史需求周期字段的语义识别。

本模块只负责「判断」与「结构化结果」：
- 输入一组候选列名（通常是数值列）
- 输出哪些列像历史需求周期字段、哪些明确不属于、哪些无法判断

本模块**不包含任何面向用户的措辞**，中文文案由 utils/quality_text.py 提供，
页面负责展示。与 A-03 的 quality_utils / quality_text 分层保持一致。

识别原则：保守优先，不做激进猜测。
- 「年需求量」「单价」这类字段即使包含「需求」，也不属于按周期记录的需求量；
- 无法可靠判断时归入 other / possible，交由用户手动选择，而不是替用户猜。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ------------------------------------------------------------------ 判定结果

# 单个列的语义分类
CLASS_PERIOD = "period"        # 高置信：像历史需求周期字段
CLASS_POSSIBLE = "possible"    # 可能相关，但证据不足
CLASS_OTHER = "other"          # 与周期语义无关的普通数值列
CLASS_NON_PERIOD = "non_period"  # 明确不属于历史需求周期

# 整次选择的语义评估
FIELD_OK = "ok"
FIELD_NO_PERIOD_FIELDS = "no_period_fields"
FIELD_FEW_PERIOD_FIELDS = "few_period_fields"
FIELD_ATYPICAL_SELECTION = "atypical_selection"

# ---------------------------------------------------------------- 语义词表

# 明确不属于「历史需求周期」的语义。优先于其他规则判定，
# 因此「年需求量」不会被「需求」二字误判成周期字段。
NON_PERIOD_TOKENS = (
    "单价",
    "价格",
    "price",
    "金额",
    "amount",
    "value",
    "成本",
    "cost",
    "年需求量",
    "年度需求",
    "年销量",
    "年销售额",
    "销售额",
    "annual",
    "yearly",
    "ytd",
    "sku",
    "编码",
    "编号",
    "名称",
    "类别",
    "分类",
    "仓库",
    "供应商",
)

# 周期单位
PERIOD_UNITS = (
    "月",
    "周",
    "日",
    "季度",
    "季",
    "period",
    "month",
    "week",
    "day",
    "quarter",
)

# 需求量语义
DEMAND_TOKENS = (
    "需求",
    "demand",
    "用量",
    "consumption",
    "出库",
    "出货",
    "销量",
)

# 英文月份缩写，作为「有周期序号」的补充证据
MONTH_NAME_TOKENS = (
    "jan",
    "feb",
    "mar",
    "apr",
    "may",
    "jun",
    "jul",
    "aug",
    "sep",
    "oct",
    "nov",
    "dec",
)

_INDEX_PATTERN = re.compile(r"\d")

# 至少两个周期字段才可能构成「历史序列」
MIN_PERIOD_COLUMNS = 2


@dataclass
class PeriodFieldDetection:
    """一组候选列的周期语义识别结果。"""

    period_columns: list[str] = field(default_factory=list)
    possible_columns: list[str] = field(default_factory=list)
    other_columns: list[str] = field(default_factory=list)
    # 明确不属于历史需求周期的字段。**仍保留在候选列表中**，只是不推荐、不默认选中。
    non_period_columns: list[str] = field(default_factory=list)

    @property
    def has_confident_periods(self) -> bool:
        return bool(self.period_columns)

    @property
    def has_usable_sequence(self) -> bool:
        """是否存在足以构成历史序列的周期字段。"""
        return len(self.period_columns) >= MIN_PERIOD_COLUMNS

    def ordered_columns(self) -> list[str]:
        """推荐展示顺序：周期字段在前，明确非周期的字段排在最后。"""
        return (
            list(self.period_columns)
            + list(self.possible_columns)
            + list(self.other_columns)
            + list(self.non_period_columns)
        )


@dataclass
class PeriodFieldAssessment:
    """用户实际选择与识别结果的对比评估。"""

    selected: list[str] = field(default_factory=list)
    code: str = FIELD_OK
    atypical_selected: list[str] = field(default_factory=list)
    period_count: int = 0

    @property
    def is_ok(self) -> bool:
        return self.code == FIELD_OK


def _classify(column: str) -> str:
    """把单个列名归类。判定顺序：明确非周期 → 周期 → 可能 → 其他。"""
    name = str(column).strip().lower()
    if not name:
        return CLASS_OTHER
    if any(token in name for token in NON_PERIOD_TOKENS):
        return CLASS_NON_PERIOD

    has_index = bool(_INDEX_PATTERN.search(name))
    has_unit = any(token in name for token in PERIOD_UNITS)
    has_demand = any(token in name for token in DEMAND_TOKENS)
    has_month_name = any(token in name for token in MONTH_NAME_TOKENS)

    # 高置信：需求语义 + 序号（或月份名），或者周期单位 + 序号
    if has_demand and (has_index or has_month_name):
        return CLASS_PERIOD
    if has_unit and has_index:
        return CLASS_PERIOD

    # 证据不足但语义相关。
    # 只认「需求」语义，避免「周转天数」这类含单个周期字（周）但与需求无关的列被误判。
    if has_demand:
        return CLASS_POSSIBLE
    return CLASS_OTHER


def detect_period_fields(columns) -> PeriodFieldDetection:
    """识别候选列中的历史需求周期字段。

    只做保守识别：识别不到就返回空列表，交由用户手动选择，不猜测。
    """
    detection = PeriodFieldDetection()
    buckets = {
        CLASS_PERIOD: detection.period_columns,
        CLASS_POSSIBLE: detection.possible_columns,
        CLASS_OTHER: detection.other_columns,
        CLASS_NON_PERIOD: detection.non_period_columns,
    }
    seen: set[str] = set()
    for column in columns:
        name = str(column)
        if name in seen:
            continue
        seen.add(name)
        buckets[_classify(name)].append(name)
    return detection


def assess_period_selection(
    selected, detection: PeriodFieldDetection
) -> PeriodFieldAssessment:
    """评估用户实际选择是否符合历史需求周期语义。

    优先级：选中了明确非周期字段 > 数据中识别不到周期字段 > 周期字段数量偏少 > 正常。
    """
    selected_list = [str(column) for column in selected]
    non_period = set(detection.non_period_columns)
    atypical = [column for column in selected_list if column in non_period]

    assessment = PeriodFieldAssessment(
        selected=selected_list,
        atypical_selected=atypical,
        period_count=len(detection.period_columns),
    )

    if atypical:
        assessment.code = FIELD_ATYPICAL_SELECTION
    elif not detection.period_columns:
        assessment.code = FIELD_NO_PERIOD_FIELDS
    elif not detection.has_usable_sequence:
        assessment.code = FIELD_FEW_PERIOD_FIELDS
    else:
        assessment.code = FIELD_OK
    return assessment
