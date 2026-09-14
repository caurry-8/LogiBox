"""库存决策摘要的规则层与结构化结果。

本模块只负责「判断」与「结构化」：
- 输入现有分析结果（ABC / XYZ / ABC×XYZ / EOQ / 安全库存 / 数据质量）
- 输出 DecisionSummary：可决策性、优先级分布、重点 SKU 与下一步建议编码

本模块**不包含面向用户的措辞**，中文文案由 utils/decision_text.py 提供。

数据来源约束（重要）：
- ABC / XYZ / ABC×XYZ 的结果都是 per-SKU 的，可作为决策输入；
- **EOQ 与安全库存当前是全局单次计算，没有 per-SKU 结果**，
  因此这里只把它们记为「模型是否已运行」，不伪造 per-SKU 的订货/安全库存判断；
- 未参与 ABC×XYZ 矩阵的 SKU（missing / invalid / 未分类）不会进入决策项。

规则版本：v1（可解释、可替换）。规则集中在 CATEGORY_RULE_OVERRIDES 与
DEFAULT_CATEGORY_RULE，调整规则不需要改动调用方。
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

import pandas as pd

from utils.matrix_utils import CELL_ORDER
from utils.quality_utils import STATUS_BLOCKER, assess_data_quality

# ------------------------------------------------------------------ 摘要状态

SUMMARY_READY = "ready"
SUMMARY_NO_DATA = "no_data"
SUMMARY_BLOCKED_BY_QUALITY = "blocked_by_quality"
SUMMARY_MISSING_ANALYSIS = "missing_analysis"

# -------------------------------------------------------------- 关注优先级

PRIORITY_HIGH = "high"
PRIORITY_MEDIUM = "medium"
PRIORITY_NORMAL = "normal"
PRIORITY_UNDETERMINED = "undetermined"
PRIORITY_ORDER = (
    PRIORITY_HIGH,
    PRIORITY_MEDIUM,
    PRIORITY_NORMAL,
    PRIORITY_UNDETERMINED,
)

# -------------------------------------------------------------- 风险严重度

SEVERITY_CRITICAL = "critical"
SEVERITY_ELEVATED = "elevated"
SEVERITY_NORMAL = "normal"
SEVERITY_UNDETERMINED = "undetermined"
SEVERITY_ORDER = (
    SEVERITY_CRITICAL,
    SEVERITY_ELEVATED,
    SEVERITY_NORMAL,
    SEVERITY_UNDETERMINED,
)

# ------------------------------------------------------------ 阻塞原因编码

BLOCK_NO_DATA = "no_data"
BLOCK_QUALITY_BLOCKER = "quality_blocker"
BLOCK_MISSING_ABC = "missing_abc"
BLOCK_MISSING_XYZ = "missing_xyz"
BLOCK_MISSING_MATRIX = "missing_matrix"

# ---------------------------------------------------------------- 原因编码

REASON_HIGH_VALUE_VOLATILE = "high_value_volatile"
REASON_HIGH_VALUE_STABLE = "high_value_stable"
REASON_HIGH_VALUE_FLUCTUATING = "high_value_fluctuating"
REASON_MEDIUM_VALUE_STABLE = "medium_value_stable"
REASON_NORMAL_CATEGORY = "normal_category"

# ------------------------------------------------------------ 建议动作编码

ACTION_TIGHT_CONTROL_BUFFER = "tight_control_buffer"
ACTION_PRECISE_REPLENISH = "precise_replenish"
ACTION_MONITOR_BUFFER = "monitor_buffer"
ACTION_STANDARD_REPLENISH = "standard_replenish"
ACTION_ROUTINE = "routine"

# -------------------------------------------------------------- 下一步编码

NEXT_IMPORT_DATA = "import_data"
NEXT_FIX_DATA_QUALITY = "fix_data_quality"
NEXT_RUN_MISSING_ANALYSIS = "run_missing_analysis"
NEXT_REVIEW_HIGH_PRIORITY = "review_high_priority"
NEXT_MONITOR_ROUTINE = "monitor_routine"
NEXT_REVIEW_UNCLASSIFIED = "review_unclassified"
NEXT_REVIEW_PERIOD_FIELDS = "review_period_fields"
NEXT_RUN_INVENTORY_MODELS = "run_inventory_models"

# 库存决策模型（当前为全局计算，非 per-SKU）
INVENTORY_MODEL_KEYS = ("eoq", "safety")

DEFAULT_MAX_ITEMS = 20

# 矩阵结果列名（来自 utils/matrix_utils）
CATEGORY_COLUMN = "矩阵单元"
ABC_COLUMN = "ABC分类"
XYZ_COLUMN = "XYZ分类"


@dataclass(frozen=True)
class CategoryDecisionRule:
    """单个矩阵单元的决策规则。"""

    category: str
    priority: str
    severity: str
    reason: str
    action: str


# 默认规则：正常组合 → 一般关注
DEFAULT_CATEGORY_RULE = CategoryDecisionRule(
    category="*",
    priority=PRIORITY_NORMAL,
    severity=SEVERITY_NORMAL,
    reason=REASON_NORMAL_CATEGORY,
    action=ACTION_ROUTINE,
)

# v1 规则覆盖：AZ / AX 高优先级；AY / BX 中优先级；其余走默认
#
# 与 matrix_utils.CELL_STRATEGIES 的口径对齐说明：
#   矩阵侧优先级为 AX 高 / AY 高 / AZ 极高 / BX 中 / BY 中 / BZ 中高 / CX-CZ 低。
#   决策侧用 priority 表示「关注优先级」，用 severity 表示「风险严重度」，
#   因此 AZ 与 AX 同为 high，但 AZ 的风险严重度更高（critical > elevated），
#   以保留矩阵侧「AZ 高于 AX」的层次。
CATEGORY_RULE_OVERRIDES: dict[str, CategoryDecisionRule] = {
    "AZ": CategoryDecisionRule(
        "AZ", PRIORITY_HIGH, SEVERITY_CRITICAL,
        REASON_HIGH_VALUE_VOLATILE, ACTION_TIGHT_CONTROL_BUFFER,
    ),
    "AX": CategoryDecisionRule(
        "AX", PRIORITY_HIGH, SEVERITY_ELEVATED,
        REASON_HIGH_VALUE_STABLE, ACTION_PRECISE_REPLENISH,
    ),
    "AY": CategoryDecisionRule(
        "AY", PRIORITY_MEDIUM, SEVERITY_ELEVATED,
        REASON_HIGH_VALUE_FLUCTUATING, ACTION_MONITOR_BUFFER,
    ),
    "BX": CategoryDecisionRule(
        "BX", PRIORITY_MEDIUM, SEVERITY_ELEVATED,
        REASON_MEDIUM_VALUE_STABLE, ACTION_STANDARD_REPLENISH,
    ),
}


def category_rule(category: str) -> CategoryDecisionRule:
    """取某个矩阵单元的规则；未覆盖的单元走默认规则。"""
    return CATEGORY_RULE_OVERRIDES.get(str(category), DEFAULT_CATEGORY_RULE)


def all_category_rules() -> dict[str, CategoryDecisionRule]:
    """覆盖全部 9 个矩阵单元的规则表（便于测试与后续调整）。"""
    return {category: category_rule(category) for category in CELL_ORDER}


@dataclass(frozen=True)
class DecisionItem:
    """单个 SKU 的决策条目。只保存决策所需字段，不复制整行数据。"""

    sku: str
    abc_class: str
    xyz_class: str
    matrix_category: str
    priority: str
    severity: str
    reason: str
    suggested_action: str
    value: float | None = None


@dataclass
class DecisionSummary:
    """库存决策摘要。供 Dashboard / 后续 Decision Workspace 使用。"""

    status: str = SUMMARY_NO_DATA
    decidable: bool = False
    total_sku_count: int = 0
    analyzed_sku_count: int = 0
    unclassified_sku_count: int = 0
    priority_counts: dict[str, int] = field(default_factory=dict)
    risk_category_counts: dict[str, int] = field(default_factory=dict)
    # 需要关注（高 / 中优先级）的条目，已按优先级与价值排序并截断
    priority_items: list[DecisionItem] = field(default_factory=list)
    # 高优先级条目（priority_items 的子集）
    top_risk_items: list[DecisionItem] = field(default_factory=list)
    quality_status: str = ""
    blocking_reasons: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    field_semantics: str = ""
    models_run: list[str] = field(default_factory=list)

    @property
    def is_ready(self) -> bool:
        return self.status == SUMMARY_READY

    @property
    def high_priority_count(self) -> int:
        return self.priority_counts.get(PRIORITY_HIGH, 0)

    @property
    def medium_priority_count(self) -> int:
        return self.priority_counts.get(PRIORITY_MEDIUM, 0)

    @property
    def normal_priority_count(self) -> int:
        return self.priority_counts.get(PRIORITY_NORMAL, 0)

    @property
    def focus_count(self) -> int:
        """值得重点关注的 SKU 数量（高 + 中优先级）。"""
        return self.high_priority_count + self.medium_priority_count

    @property
    def has_focus(self) -> bool:
        return self.focus_count > 0

    @property
    def missing_models(self) -> list[str]:
        return [key for key in INVENTORY_MODEL_KEYS if key not in self.models_run]


def _unclassified_count(analyses: Mapping[str, dict]) -> int:
    """未参与正常 XYZ 分类的 SKU 数量。优先复用 XYZ 结果里的既有统计。"""
    xyz = analyses.get("xyz") or {}
    total_count = xyz.get("total_count")
    counts = xyz.get("counts") or {}
    if total_count is not None and counts:
        classified = sum(int(counts.get(key, 0)) for key in ("X", "Y", "Z"))
        return max(0, int(total_count) - classified)
    status_counts = xyz.get("status_counts") or {}
    if status_counts:
        return int(status_counts.get("missing", 0)) + int(status_counts.get("invalid", 0))
    return 0


def _matrix_frame(analyses: Mapping[str, dict]) -> pd.DataFrame | None:
    """取出可用的矩阵结果明细；列不完整时视为不可用。"""
    frame = (analyses.get("matrix") or {}).get("dataframe")
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        return None
    if not {CATEGORY_COLUMN, ABC_COLUMN, XYZ_COLUMN}.issubset(frame.columns):
        return None
    return frame


def _collect_blocking_reasons(
    dataframe: pd.DataFrame | None, analyses: Mapping[str, dict], quality_status: str
) -> list[str]:
    if dataframe is None or len(dataframe) == 0:
        return [BLOCK_NO_DATA]
    reasons: list[str] = []
    if quality_status == STATUS_BLOCKER:
        reasons.append(BLOCK_QUALITY_BLOCKER)
    if "abc" not in analyses:
        reasons.append(BLOCK_MISSING_ABC)
    if "xyz" not in analyses:
        reasons.append(BLOCK_MISSING_XYZ)
    if _matrix_frame(analyses) is None:
        reasons.append(BLOCK_MISSING_MATRIX)
    return reasons


def _resolve_status(blocking_reasons: list[str]) -> str:
    if BLOCK_NO_DATA in blocking_reasons:
        return SUMMARY_NO_DATA
    if BLOCK_QUALITY_BLOCKER in blocking_reasons:
        return SUMMARY_BLOCKED_BY_QUALITY
    if blocking_reasons:
        return SUMMARY_MISSING_ANALYSIS
    return SUMMARY_READY


def _next_actions(summary: DecisionSummary) -> list[str]:
    if summary.status == SUMMARY_NO_DATA:
        return [NEXT_IMPORT_DATA]
    if summary.status == SUMMARY_BLOCKED_BY_QUALITY:
        return [NEXT_FIX_DATA_QUALITY]
    if summary.status == SUMMARY_MISSING_ANALYSIS:
        return [NEXT_RUN_MISSING_ANALYSIS]

    actions = [NEXT_REVIEW_HIGH_PRIORITY if summary.has_focus else NEXT_MONITOR_ROUTINE]
    if summary.unclassified_sku_count:
        actions.append(NEXT_REVIEW_UNCLASSIFIED)
    if summary.field_semantics and summary.field_semantics != "ok":
        actions.append(NEXT_REVIEW_PERIOD_FIELDS)
    if summary.missing_models:
        actions.append(NEXT_RUN_INVENTORY_MODELS)
    return actions


def build_decision_summary(
    dataframe: pd.DataFrame | None,
    analyses: Mapping[str, dict] | None = None,
    max_items: int = DEFAULT_MAX_ITEMS,
) -> DecisionSummary:
    """根据现有分析结果构建决策摘要。

    analyses 为 DataStore 中按名称存放的分析结果映射（abc / xyz / matrix / eoq / safety）。
    数据质量 BLOCKER 或缺少必要分析时，不生成任何正常决策建议。
    """
    analyses = analyses or {}
    quality = assess_data_quality(dataframe)
    summary = DecisionSummary(
        total_sku_count=0 if dataframe is None else int(len(dataframe)),
        unclassified_sku_count=_unclassified_count(analyses),
        quality_status=quality.status,
        field_semantics=str((analyses.get("xyz") or {}).get("field_semantics") or ""),
        models_run=[key for key in INVENTORY_MODEL_KEYS if key in analyses],
        priority_counts={key: 0 for key in PRIORITY_ORDER},
    )

    summary.blocking_reasons = _collect_blocking_reasons(
        dataframe, analyses, quality.status
    )
    summary.status = _resolve_status(summary.blocking_reasons)
    summary.decidable = not summary.blocking_reasons

    frame = _matrix_frame(analyses)
    if summary.decidable and frame is not None:
        _fill_priorities(summary, analyses, frame, max_items)

    # next_actions 依赖优先级分布与未分类数量，必须在统计完成后再计算
    summary.next_actions = _next_actions(summary)
    return summary


def _fill_priorities(
    summary: DecisionSummary,
    analyses: Mapping[str, dict],
    frame: pd.DataFrame,
    max_items: int,
) -> None:
    """填充优先级分布、风险单元与重点条目。"""
    matrix_payload = analyses.get("matrix") or {}
    key_column = str(matrix_payload.get("key_column") or "")
    value_column = str(matrix_payload.get("value_column") or "")
    has_value = bool(value_column) and value_column in frame.columns

    rules = all_category_rules()
    categories = frame[CATEGORY_COLUMN].astype(str)
    priorities = categories.map(
        {category: rule.priority for category, rule in rules.items()}
    ).fillna(DEFAULT_CATEGORY_RULE.priority)
    severities = categories.map(
        {category: rule.severity for category, rule in rules.items()}
    ).fillna(DEFAULT_CATEGORY_RULE.severity)

    counts = priorities.value_counts().to_dict()
    summary.priority_counts = {key: int(counts.get(key, 0)) for key in PRIORITY_ORDER}
    summary.analyzed_sku_count = int(len(frame))

    focus = frame.loc[priorities.isin([PRIORITY_HIGH, PRIORITY_MEDIUM])]
    if focus.empty:
        return

    focus_categories = categories.loc[focus.index]
    summary.risk_category_counts = {
        str(key): int(value)
        for key, value in focus_categories.value_counts().to_dict().items()
    }

    focus = focus.copy()
    focus["_priority"] = priorities.loc[focus.index]
    focus["_severity"] = severities.loc[focus.index]
    focus["_rank"] = focus["_priority"].map({PRIORITY_HIGH: 0, PRIORITY_MEDIUM: 1})

    sort_columns = ["_rank"]
    ascending = [True]
    if has_value:
        sort_columns.append(value_column)
        ascending.append(False)
    if key_column and key_column in focus.columns:
        sort_columns.append(key_column)
        ascending.append(True)
    focus = focus.sort_values(sort_columns, ascending=ascending, kind="stable")

    items: list[DecisionItem] = []
    for record in focus.head(max_items).to_dict("records"):
        category = str(record.get(CATEGORY_COLUMN, ""))
        raw_value = record.get(value_column) if has_value else None
        try:
            value = None if raw_value is None or pd.isna(raw_value) else float(raw_value)
        except (TypeError, ValueError):
            value = None
        rule = category_rule(category)
        items.append(
            DecisionItem(
                sku=str(record.get(key_column, "")) if key_column else "",
                abc_class=str(record.get(ABC_COLUMN, "")),
                xyz_class=str(record.get(XYZ_COLUMN, "")),
                matrix_category=category,
                priority=str(record["_priority"]),
                severity=str(record["_severity"]),
                reason=rule.reason,
                suggested_action=rule.action,
                value=value,
            )
        )

    summary.priority_items = items
    summary.top_risk_items = [item for item in items if item.priority == PRIORITY_HIGH]
