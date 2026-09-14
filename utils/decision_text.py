"""库存决策摘要的面向用户措辞。

本模块属于展示层：只把 utils/decision_utils.py 产出的编码翻译成中文文案。
不包含任何判定逻辑，也不依赖 Qt，因此页面与报告可以共用同一套措辞。

判定规则请改 utils/decision_utils.py；本文件只改「怎么说」。
"""

from __future__ import annotations

from utils.decision_utils import (
    ACTION_MONITOR_BUFFER,
    ACTION_PRECISE_REPLENISH,
    ACTION_ROUTINE,
    ACTION_STANDARD_REPLENISH,
    ACTION_TIGHT_CONTROL_BUFFER,
    BLOCK_MISSING_ABC,
    BLOCK_MISSING_MATRIX,
    BLOCK_MISSING_XYZ,
    BLOCK_NO_DATA,
    BLOCK_QUALITY_BLOCKER,
    NEXT_FIX_DATA_QUALITY,
    NEXT_IMPORT_DATA,
    NEXT_MONITOR_ROUTINE,
    NEXT_REVIEW_HIGH_PRIORITY,
    NEXT_REVIEW_PERIOD_FIELDS,
    NEXT_REVIEW_UNCLASSIFIED,
    NEXT_RUN_INVENTORY_MODELS,
    NEXT_RUN_MISSING_ANALYSIS,
    PRIORITY_HIGH,
    PRIORITY_MEDIUM,
    PRIORITY_NORMAL,
    PRIORITY_UNDETERMINED,
    REASON_HIGH_VALUE_FLUCTUATING,
    REASON_HIGH_VALUE_STABLE,
    REASON_HIGH_VALUE_VOLATILE,
    REASON_MEDIUM_VALUE_STABLE,
    REASON_NORMAL_CATEGORY,
    SEVERITY_CRITICAL,
    SEVERITY_ELEVATED,
    SEVERITY_NORMAL,
    SEVERITY_UNDETERMINED,
    SUMMARY_BLOCKED_BY_QUALITY,
    SUMMARY_MISSING_ANALYSIS,
    SUMMARY_NO_DATA,
    SUMMARY_READY,
    DecisionItem,
    DecisionSummary,
)

STATUS_LABELS = {
    SUMMARY_READY: "可决策",
    SUMMARY_NO_DATA: "无数据",
    SUMMARY_BLOCKED_BY_QUALITY: "数据不可靠",
    SUMMARY_MISSING_ANALYSIS: "分析未就绪",
}

PRIORITY_LABELS = {
    PRIORITY_HIGH: "高优先级",
    PRIORITY_MEDIUM: "中优先级",
    PRIORITY_NORMAL: "一般关注",
    PRIORITY_UNDETERMINED: "未判定",
}

SEVERITY_LABELS = {
    SEVERITY_CRITICAL: "严重",
    SEVERITY_ELEVATED: "较高",
    SEVERITY_NORMAL: "正常",
    SEVERITY_UNDETERMINED: "未判定",
}

REASON_TEXT = {
    REASON_HIGH_VALUE_VOLATILE: "高价值且需求不稳定，缺货与积压风险同时存在",
    REASON_HIGH_VALUE_STABLE: "高价值且需求相对稳定，一旦断供影响较大",
    REASON_HIGH_VALUE_FLUCTUATING: "高价值且需求存在波动，需要持续监控",
    REASON_MEDIUM_VALUE_STABLE: "中等价值且需求相对稳定，适合标准化补货",
    REASON_NORMAL_CATEGORY: "价值与波动组合正常，按常规节奏管理即可",
}

ACTION_TEXT = {
    ACTION_TIGHT_CONTROL_BUFFER: "优先配置安全库存并提高复核频率",
    ACTION_PRECISE_REPLENISH: "采用精确补货与严格库存控制，保障供应连续性",
    ACTION_MONITOR_BUFFER: "设置适度缓冲并定期复核需求偏差",
    ACTION_STANDARD_REPLENISH: "按标准周期补货，并结合 EOQ 参数",
    ACTION_ROUTINE: "按常规流程管理，无需额外投入",
}

BLOCKING_TEXT = {
    BLOCK_NO_DATA: "尚未导入数据",
    BLOCK_QUALITY_BLOCKER: "数据质量存在阻断问题，无法给出可靠决策建议",
    BLOCK_MISSING_ABC: "尚未完成 ABC 分类",
    BLOCK_MISSING_XYZ: "尚未完成 XYZ 稳定性分析",
    BLOCK_MISSING_MATRIX: "尚未生成 ABC × XYZ 交叉矩阵",
}

NEXT_ACTION_TEXT = {
    NEXT_IMPORT_DATA: "在数据中心导入库存数据",
    NEXT_FIX_DATA_QUALITY: "先处理数据中心列出的数据质量问题",
    NEXT_RUN_MISSING_ANALYSIS: "补齐缺失的分析后重新查看决策摘要",
    NEXT_REVIEW_HIGH_PRIORITY: "查看需要重点关注的 SKU 清单并安排处理",
    NEXT_MONITOR_ROUTINE: "当前没有重点风险，按常规节奏监控即可",
    NEXT_REVIEW_UNCLASSIFIED: "确认未参与分类的 SKU 数据是否完整",
    NEXT_REVIEW_PERIOD_FIELDS: "检查 XYZ 的历史周期字段选择",
    NEXT_RUN_INVENTORY_MODELS: "补充 EOQ / 安全库存计算以完善补货参数",
}


def status_label(status: str) -> str:
    return STATUS_LABELS.get(status, status)


def priority_label(priority: str) -> str:
    return PRIORITY_LABELS.get(priority, priority)


def severity_label(severity: str) -> str:
    return SEVERITY_LABELS.get(severity, severity)


def blocking_label(code: str) -> str:
    return BLOCKING_TEXT.get(code, code)


def next_action_label(code: str) -> str:
    return NEXT_ACTION_TEXT.get(code, code)


def describe_item(item: DecisionItem) -> tuple[str, str]:
    """返回单个决策条目的（风险原因, 建议动作）。"""
    return (
        REASON_TEXT.get(item.reason, item.reason),
        ACTION_TEXT.get(item.suggested_action, item.suggested_action),
    )


def describe_status(summary: DecisionSummary) -> str:
    """一句话说明当前是否适合做决策。"""
    if summary.status == SUMMARY_READY:
        return f"数据可支撑决策，共 {summary.analyzed_sku_count} 个 SKU 参与决策分析。"
    if summary.status == SUMMARY_NO_DATA:
        return "尚未导入数据，无法生成决策建议。"
    if summary.status == SUMMARY_BLOCKED_BY_QUALITY:
        return "数据质量存在阻断问题，暂不生成决策建议。"
    return "必要分析尚未完成，暂不生成决策建议。"


def describe_blocking(summary: DecisionSummary) -> list[str]:
    return [blocking_label(code) for code in summary.blocking_reasons]


def describe_focus(summary: DecisionSummary) -> str:
    """重点 SKU 概览。"""
    if not summary.is_ready:
        return "分析未就绪，暂无重点 SKU。"
    if not summary.has_focus:
        return "当前没有需要重点关注的 SKU。"
    return (
        f"需要重点关注 {summary.focus_count} 个 SKU"
        f"（高优先级 {summary.high_priority_count} / 中优先级 {summary.medium_priority_count}）。"
    )


def describe_risk_categories(summary: DecisionSummary) -> str:
    """风险集中的矩阵单元说明。"""
    if not summary.risk_category_counts:
        return "暂无集中的风险单元。"
    parts = "、".join(
        f"{category} {count} 个" for category, count in summary.risk_category_counts.items()
    )
    return f"风险集中在：{parts}。"


def describe_unclassified(summary: DecisionSummary) -> str:
    if not summary.unclassified_sku_count:
        return ""
    return f"另有 {summary.unclassified_sku_count} 个 SKU 未参与分类，未纳入决策建议。"


def describe_next_actions(summary: DecisionSummary) -> list[str]:
    return [next_action_label(code) for code in summary.next_actions]


def describe_item_line(item: DecisionItem) -> str:
    """把一条决策条目压缩成一行文本。"""
    reason, action = describe_item(item)
    return (
        f"{item.sku}（{item.matrix_category}｜{priority_label(item.priority)}）"
        f"：{reason}；建议：{action}"
    )
