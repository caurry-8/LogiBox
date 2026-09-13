"""数据质量结果的面向用户措辞。

本模块属于展示层：只把 utils/quality_utils.py 产出的结构化结果翻译成中文文案。
不包含任何判定逻辑，也不依赖 Qt，因此页面与报告可以共用同一套措辞。

判定规则请改 utils/quality_utils.py；本文件只改「怎么说」。
"""

from __future__ import annotations

import math

import pandas as pd

from utils.quality_utils import (
    ANALYSIS_ABC,
    ANALYSIS_EOQ,
    ANALYSIS_MATRIX,
    ANALYSIS_SAFETY,
    ANALYSIS_XYZ,
    SEVERITY_BLOCKER,
    SEVERITY_INFO,
    SEVERITY_WARNING,
    STATUS_BLOCKER,
    STATUS_OK,
    STATUS_WARNING,
    QualityIssue,
)
from utils.xyz_utils import STATUS_INVALID, STATUS_MISSING, STATUS_VALID

SEVERITY_LABELS = {
    SEVERITY_BLOCKER: "阻断",
    SEVERITY_WARNING: "警告",
    SEVERITY_INFO: "提示",
}

STATUS_LABELS = {
    STATUS_OK: "可分析",
    STATUS_WARNING: "存在风险",
    STATUS_BLOCKER: "无法分析",
}

XYZ_STATUS_LABELS = {
    STATUS_VALID: "有效",
    STATUS_MISSING: "缺失数据",
    STATUS_INVALID: "非法数据",
}

# 严重级配色，供页面与报告统一使用（与 dark_v3 主题的语义色一致）
SEVERITY_COLORS = {
    SEVERITY_BLOCKER: "#f85149",
    SEVERITY_WARNING: "#d29922",
    SEVERITY_INFO: "#8b949e",
}

# 表格单元格的统一占位符：缺失 / 未计算 → —，非法数值 → 非法值
PLACEHOLDER_EMPTY = "—"
PLACEHOLDER_INVALID = "非法值"


def format_cell_value(value, digits: int | None = None) -> str:
    """把单元格值格式化为界面文本。

    缺失值统一显示为「—」，±Inf 统一显示为「非法值」，避免用户直接看到 nan / inf。
    digits 不为 None 时按定点小数格式化数值（用于 CV 等需要固定精度的列）。
    """
    try:
        if pd.isna(value):
            return PLACEHOLDER_EMPTY
    except (TypeError, ValueError):
        pass
    if isinstance(value, float) and math.isinf(value):
        return PLACEHOLDER_INVALID
    if digits is not None and isinstance(value, (int, float)):
        return f"{float(value):.{digits}f}"
    return str(value)

ANALYSIS_LABELS = {
    ANALYSIS_ABC: "ABC 分类",
    ANALYSIS_XYZ: "XYZ 分析",
    ANALYSIS_MATRIX: "ABC × XYZ 矩阵",
    ANALYSIS_EOQ: "EOQ 计算",
    ANALYSIS_SAFETY: "安全库存",
}

# code -> (标题, 描述模板, 建议动作)
ISSUE_TEXT: dict[str, tuple[str, str, str]] = {
    "empty_dataset": (
        "数据集为空",
        "当前文件没有任何数据行。",
        "请导入包含数据的 Excel 或 CSV 文件。",
    ),
    "empty_key_value": (
        "主键存在空值",
        "{column} 列有 {count} 行为空。",
        "请补充主键值，或改选其他字段作为关键字段。",
    ),
    "period_column_missing": (
        "周期字段不存在",
        "缺少字段：{columns}。",
        "请重新选择实际存在的历史需求周期字段。",
    ),
    "period_column_not_numeric": (
        "周期字段无法解析为数值",
        "字段 {columns} 没有可用数值。",
        "请确认这些列存放的是需求量，而不是文本或编码。",
    ),
    "duplicate_key_value": (
        "主键存在重复",
        "{column} 列有 {count} 行重复。",
        "请先去重，否则 ABC × XYZ 矩阵无法生成。",
    ),
    "missing_cells": (
        "存在缺失单元格",
        "共 {count} 个单元格为空。",
        "缺失的月需求不会按 0 计算，相关 SKU 会被标记为缺失并排除在 XYZ 分类之外。",
    ),
    "negative_value": (
        "存在负值",
        "{columns} 列共有 {count} 个负值。",
        "需求量与金额不应为负数，请修正后再分析。",
    ),
    "period_missing_value": (
        "部分 SKU 的周期需求缺失",
        "{count} 个 SKU 的周期数据不完整。",
        "请补充对应期间数据后重新分析；这些 SKU 不会参与 XYZ 分类。",
    ),
    "all_zero_period": (
        "存在全零需求 SKU",
        "{count} 个 SKU 的全部周期需求都是 0。",
        "请确认这些 SKU 是否确实没有需求；它们会以 CV=0 归入 X 类。",
    ),
    "key_column_unidentified": (
        "未识别到主键字段",
        "未能高置信识别 SKU / 物料编码等主键列，因此不提供 SKU 级质量指标。",
        "如需 SKU 级指标，请使用标准主键列名（如 SKU、物料编码）。",
    ),
}


def severity_label(severity: str) -> str:
    return SEVERITY_LABELS.get(severity, severity)


def status_label(status: str) -> str:
    return STATUS_LABELS.get(status, status)


def analysis_label(key: str) -> str:
    return ANALYSIS_LABELS.get(key, key)


def _format_columns(value) -> str:
    if isinstance(value, (list, tuple)):
        return "、".join(str(item) for item in value)
    return str(value)


def describe(issue: QualityIssue) -> tuple[str, str, str]:
    """返回（标题, 描述, 建议动作）。未登记的编码回退为通用文案。"""
    title, description, action = ISSUE_TEXT.get(
        issue.code,
        (issue.code, "检测到一项数据质量问题。", "请检查数据后重新分析。"),
    )
    params = dict(issue.details or {})
    params["count"] = issue.affected_count
    if "columns" in params:
        params["columns"] = _format_columns(params["columns"])

    def _safe_format(template: str) -> str:
        try:
            return template.format(**params)
        except (KeyError, IndexError):
            return template

    return _safe_format(title), _safe_format(description), _safe_format(action)


def impact_text(issue: QualityIssue) -> str:
    """返回「影响：ABC 分类、XYZ 分析」；无影响范围时返回空字符串。"""
    if not issue.affected_analyses:
        return ""
    labels = "、".join(analysis_label(key) for key in issue.affected_analyses)
    return f"影响：{labels}"


def format_issue_line(issue: QualityIssue, include_action: bool = True) -> str:
    """把一条问题格式化为单行文本，供数据质量面板与报告复用。"""
    title, description, action = describe(issue)
    parts = [f"{severity_label(issue.severity)}｜{title}", description]
    if issue.affected_count:
        parts.append(f"受影响 {issue.affected_count} 项")
    impact = impact_text(issue)
    if impact:
        parts.append(impact)
    if include_action and action:
        parts.append(f"建议：{action}")
    return "；".join(parts)


def coverage_text(classified: int, total: int) -> str:
    """统一的覆盖率文案：M / N（xx%）。"""
    if total <= 0:
        return "0 / 0"
    return f"{classified} / {total}（{classified / total:.1%}）"


def xyz_status_label(key: str) -> str:
    return XYZ_STATUS_LABELS.get(key, key)


def excluded_reason_text(excluded_by_quality: dict[str, int]) -> str:
    """把「按数据质量统计的排除数量」翻译成中文，例如「缺失数据 1、非法数据 1」。"""
    if not excluded_by_quality:
        return ""
    return "、".join(
        f"{xyz_status_label(key)} {count}" for key, count in excluded_by_quality.items()
    )
