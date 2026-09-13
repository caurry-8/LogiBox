"""数据质量判定与结构化结果。

本模块只负责「判断」与「结构化」：
- 输入 DataFrame（可选主键列、可选周期列）
- 输出 DataQualityResult：状态、计数、以及带严重级别的 QualityIssue 列表

本模块**不包含任何面向用户的措辞或界面布局逻辑**；
面向用户的文案由 utils/quality_text.py 提供，展示由页面负责。

判定原则：
- 只实现能够从当前数据模型可靠判断的规则，不为了凑数量机械添加；
- 主键列只在**高置信**匹配时才使用，识别不到就明确标记为未识别，不猜测。
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

# ---------------------------------------------------------------- 严重级别

SEVERITY_BLOCKER = "blocker"
SEVERITY_WARNING = "warning"
SEVERITY_INFO = "info"
SEVERITY_ORDER = (SEVERITY_BLOCKER, SEVERITY_WARNING, SEVERITY_INFO)

# ---------------------------------------------------------------- 整体状态

STATUS_OK = "ok"
STATUS_WARNING = "warning"
STATUS_BLOCKER = "blocker"

# ------------------------------------------------------------ 受影响的分析

ANALYSIS_ABC = "abc"
ANALYSIS_XYZ = "xyz"
ANALYSIS_MATRIX = "matrix"
ANALYSIS_EOQ = "eoq"
ANALYSIS_SAFETY = "safety"

# ---------------------------------------------------------------- 问题编码

CODE_EMPTY_DATASET = "empty_dataset"
CODE_EMPTY_KEY_VALUE = "empty_key_value"
CODE_PERIOD_COLUMN_MISSING = "period_column_missing"
CODE_PERIOD_COLUMN_NOT_NUMERIC = "period_column_not_numeric"
CODE_DUPLICATE_KEY_VALUE = "duplicate_key_value"
CODE_MISSING_CELLS = "missing_cells"
CODE_NEGATIVE_VALUE = "negative_value"
CODE_PERIOD_MISSING_VALUE = "period_missing_value"
CODE_ALL_ZERO_PERIOD = "all_zero_period"
CODE_KEY_COLUMN_UNIDENTIFIED = "key_column_unidentified"

# 只有在高置信命中这些名称时才把该列当作主键，不做任何推断。
KEY_COLUMN_CANDIDATES = (
    "SKU",
    "sku",
    "Sku",
    "物料编码",
    "物料编号",
    "物料号",
    "商品编码",
    "商品编号",
    "产品编码",
    "货号",
)


@dataclass(frozen=True)
class QualityIssue:
    """一条数据质量问题。不含面向用户的措辞，只描述事实。"""

    code: str
    severity: str
    affected_count: int = 0
    affected_analyses: tuple[str, ...] = ()
    details: dict = field(default_factory=dict)


@dataclass
class DataQualityResult:
    """数据质量判定结果。"""

    total_rows: int = 0
    total_columns: int = 0
    key_column: str | None = None
    key_column_confident: bool = False
    valid_key_count: int = 0
    empty_key_count: int = 0
    duplicate_key_count: int = 0
    missing_cell_count: int = 0
    issues: list[QualityIssue] = field(default_factory=list)
    severity_counts: dict[str, int] = field(default_factory=dict)
    status: str = STATUS_OK

    def issues_by_severity(self, severity: str) -> list[QualityIssue]:
        return [issue for issue in self.issues if issue.severity == severity]

    @property
    def blocker_count(self) -> int:
        return self.severity_counts.get(SEVERITY_BLOCKER, 0)

    @property
    def warning_count(self) -> int:
        return self.severity_counts.get(SEVERITY_WARNING, 0)

    @property
    def info_count(self) -> int:
        return self.severity_counts.get(SEVERITY_INFO, 0)

    @property
    def is_analyzable(self) -> bool:
        return self.status != STATUS_BLOCKER

    @property
    def has_key_metrics(self) -> bool:
        """是否具备 SKU 级指标（主键被高置信识别或显式指定）。"""
        return self.key_column is not None and self.key_column_confident


def detect_key_column(columns) -> str | None:
    """只在名称高置信命中候选列表时返回主键列，否则返回 None（不猜测）。"""
    for name in KEY_COLUMN_CANDIDATES:
        if name in columns:
            return name
    return None


def _count_negative_values(dataframe: pd.DataFrame) -> tuple[int, list[str]]:
    total = 0
    columns: list[str] = []
    for column in dataframe.columns:
        numeric = pd.to_numeric(dataframe[column], errors="coerce")
        count = int((numeric < 0).sum())
        if count:
            total += count
            columns.append(str(column))
    return total, columns


def _assess_period_columns(
    dataframe: pd.DataFrame, period_columns: list[str]
) -> tuple[list[QualityIssue], int]:
    """周期列相关判定。返回（问题列表，存在缺失的周期数据行数）。"""
    issues: list[QualityIssue] = []

    missing_columns = [c for c in period_columns if c not in dataframe.columns]
    if missing_columns:
        issues.append(
            QualityIssue(
                code=CODE_PERIOD_COLUMN_MISSING,
                severity=SEVERITY_BLOCKER,
                affected_count=len(missing_columns),
                affected_analyses=(ANALYSIS_XYZ,),
                details={"columns": missing_columns},
            )
        )
        return issues, 0

    numeric = dataframe[period_columns].apply(pd.to_numeric, errors="coerce")
    not_numeric = [c for c in period_columns if int(numeric[c].notna().sum()) == 0]
    if not_numeric:
        issues.append(
            QualityIssue(
                code=CODE_PERIOD_COLUMN_NOT_NUMERIC,
                severity=SEVERITY_BLOCKER,
                affected_count=len(not_numeric),
                affected_analyses=(ANALYSIS_XYZ,),
                details={"columns": not_numeric},
            )
        )
        return issues, 0

    rows_with_missing = int(numeric.isna().any(axis=1).sum())
    if rows_with_missing:
        issues.append(
            QualityIssue(
                code=CODE_PERIOD_MISSING_VALUE,
                severity=SEVERITY_WARNING,
                affected_count=rows_with_missing,
                affected_analyses=(ANALYSIS_XYZ,),
                details={"columns": list(period_columns)},
            )
        )

    # 只把「周期数据完整且全为 0」的行算作全零需求；含缺失的行已单独统计，不重复计数。
    complete = ~numeric.isna().any(axis=1)
    all_zero_rows = int((complete & numeric.eq(0).all(axis=1)).sum())
    if all_zero_rows:
        issues.append(
            QualityIssue(
                code=CODE_ALL_ZERO_PERIOD,
                severity=SEVERITY_WARNING,
                affected_count=all_zero_rows,
                affected_analyses=(ANALYSIS_XYZ,),
                details={},
            )
        )

    return issues, rows_with_missing


def assess_data_quality(
    dataframe: pd.DataFrame | None,
    key_column: str | None = None,
    period_columns: list[str] | None = None,
) -> DataQualityResult:
    """评估数据质量，返回结构化结果。

    key_column 为 None 时尝试高置信自动识别；识别不到则不产出 SKU 级指标。
    period_columns 由调用方（分析页面）传入用户实际选择的周期列，本模块不做猜测。
    """
    if dataframe is None or len(dataframe) == 0:
        issues = [
            QualityIssue(
                code=CODE_EMPTY_DATASET,
                severity=SEVERITY_BLOCKER,
                affected_count=0,
                affected_analyses=(
                    ANALYSIS_ABC,
                    ANALYSIS_XYZ,
                    ANALYSIS_MATRIX,
                ),
                details={},
            )
        ]
        return DataQualityResult(
            total_rows=0,
            total_columns=0 if dataframe is None else len(dataframe.columns),
            issues=issues,
            severity_counts=_severity_counts(issues),
            status=STATUS_BLOCKER,
        )

    total_rows = len(dataframe)
    total_columns = len(dataframe.columns)
    issues = []

    # ---- 主键 ----
    resolved_key = key_column
    confident = key_column is not None
    if resolved_key is None:
        resolved_key = detect_key_column(dataframe.columns)
        confident = resolved_key is not None

    valid_key_count = 0
    empty_key_count = 0
    duplicate_key_count = 0

    if resolved_key is not None and resolved_key in dataframe.columns:
        key_series = dataframe[resolved_key]
        blank = key_series.isna() | key_series.astype(str).str.strip().eq("")
        empty_key_count = int(blank.sum())
        valid_key_count = int((~blank).sum())
        duplicate_key_count = int(key_series[~blank].duplicated().sum())

        if empty_key_count:
            issues.append(
                QualityIssue(
                    code=CODE_EMPTY_KEY_VALUE,
                    severity=SEVERITY_BLOCKER,
                    affected_count=empty_key_count,
                    affected_analyses=(ANALYSIS_ABC, ANALYSIS_XYZ, ANALYSIS_MATRIX),
                    details={"column": resolved_key},
                )
            )
        if duplicate_key_count:
            issues.append(
                QualityIssue(
                    code=CODE_DUPLICATE_KEY_VALUE,
                    severity=SEVERITY_WARNING,
                    affected_count=duplicate_key_count,
                    affected_analyses=(ANALYSIS_MATRIX,),
                    details={"column": resolved_key},
                )
            )
    else:
        # 主键不可用（未识别或指定了不存在的列）：不产出 SKU 级指标，也不猜测。
        resolved_key = None
        confident = False
        issues.append(
            QualityIssue(
                code=CODE_KEY_COLUMN_UNIDENTIFIED,
                severity=SEVERITY_INFO,
                affected_count=0,
                affected_analyses=(ANALYSIS_MATRIX,),
                details={},
            )
        )

    # ---- 单元格缺失 ----
    missing_cell_count = int(dataframe.isna().sum().sum())
    if missing_cell_count:
        issues.append(
            QualityIssue(
                code=CODE_MISSING_CELLS,
                severity=SEVERITY_WARNING,
                affected_count=missing_cell_count,
                affected_analyses=(ANALYSIS_ABC, ANALYSIS_XYZ),
                details={},
            )
        )

    # ---- 负值 ----
    negative_count, negative_columns = _count_negative_values(dataframe)
    if negative_count:
        issues.append(
            QualityIssue(
                code=CODE_NEGATIVE_VALUE,
                severity=SEVERITY_WARNING,
                affected_count=negative_count,
                affected_analyses=(ANALYSIS_ABC, ANALYSIS_XYZ),
                details={"columns": negative_columns},
            )
        )

    # ---- 周期列（仅在调用方明确给出时判定）----
    if period_columns:
        period_issues, _rows_with_missing = _assess_period_columns(
            dataframe, list(period_columns)
        )
        issues.extend(period_issues)

    return DataQualityResult(
        total_rows=total_rows,
        total_columns=total_columns,
        key_column=resolved_key,
        key_column_confident=confident,
        valid_key_count=valid_key_count,
        empty_key_count=empty_key_count,
        duplicate_key_count=duplicate_key_count,
        missing_cell_count=missing_cell_count,
        issues=issues,
        severity_counts=_severity_counts(issues),
        status=_resolve_status(issues),
    )


def _severity_counts(issues: list[QualityIssue]) -> dict[str, int]:
    return {
        severity: sum(1 for issue in issues if issue.severity == severity)
        for severity in SEVERITY_ORDER
    }


def _resolve_status(issues: list[QualityIssue]) -> str:
    if any(issue.severity == SEVERITY_BLOCKER for issue in issues):
        return STATUS_BLOCKER
    if any(issue.severity == SEVERITY_WARNING for issue in issues):
        return STATUS_WARNING
    return STATUS_OK
