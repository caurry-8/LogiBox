from dataclasses import dataclass, field

import pandas as pd

# 每个 SKU 的数据质量状态。使用稳定的内部语义，界面展示留给后续版本处理。
STATUS_VALID = "valid"
STATUS_MISSING = "missing"
STATUS_INVALID = "invalid"
STATUS_ORDER = (STATUS_VALID, STATUS_MISSING, STATUS_INVALID)

# 数据质量状态列名
QUALITY_COLUMN = "数据质量"

# 无法参与正常 XYZ 分类时的分类标记
UNCLASSIFIED = "未分类"


@dataclass
class XYZResult:
    dataframe: pd.DataFrame
    counts: dict[str, int]
    mean_cv: float
    status_counts: dict[str, int] = field(default_factory=dict)

    @property
    def classified_count(self) -> int:
        """实际参与 X / Y / Z 分类的 SKU 数量。"""
        return sum(self.counts.values())


class XYZAnalyzer:
    """Classify demand stability with coefficient of variation (CV).

    数据可信规则（V3.5.0-A-02）：
    - 真实 0 需求是合法数据，正常参与 XYZ 分析；
    - NaN 表示数据缺失，不再 fillna(0)，该 SKU 不参与正常分类（status = missing）；
    - Inf / -Inf 表示非法数值，不参与计算（status = invalid）；
    - 只有 status = valid 的 SKU 才会得到 X / Y / Z 分类，其余为「未分类」。
    """

    def __init__(
        self,
        dataframe: pd.DataFrame,
        period_columns: list[str],
        x_rate: float = 0.10,
        y_rate: float = 0.25,
    ) -> None:
        self.df = dataframe.copy()
        self.period_columns = period_columns
        self.x_rate = x_rate
        self.y_rate = y_rate

    def _validate_columns(self) -> None:
        """周期字段不存在时给出明确的中文提示，而不是抛 KeyError。"""
        missing = [column for column in self.period_columns if column not in self.df.columns]
        if missing:
            raise ValueError(
                "缺少历史需求周期字段："
                + "、".join(str(column) for column in missing)
                + "。请重新选择实际存在的周期列。"
            )

    def analyze(self) -> XYZResult:
        self._validate_columns()
        if len(self.period_columns) < 2:
            raise ValueError("XYZ 分析至少需要选择 2 个历史需求周期字段。")
        if not 0 < self.x_rate < self.y_rate:
            raise ValueError("阈值必须满足：0 < X 阈值 < Y 阈值。")

        numeric = self.df[self.period_columns].apply(pd.to_numeric, errors="coerce")
        if numeric.notna().sum().sum() == 0:
            raise ValueError("所选周期字段没有可用数值。")

        # Inf / -Inf 属于非法数值，先识别出来，避免污染负数判定与后续统计量。
        has_infinite = numeric.abs().eq(float("inf")).any(axis=1)
        finite = numeric.where(~has_infinite)

        # 真实负数仍是整体性错误，保持与 V3.4.0 一致的行为。
        if (finite < 0).any().any():
            raise ValueError("历史需求数据不能包含负数。")

        # 每个 SKU 的数据质量状态：非法数值优先于缺失。
        status = pd.Series(STATUS_VALID, index=numeric.index, dtype=object)
        status.loc[numeric.isna().any(axis=1)] = STATUS_MISSING
        status.loc[has_infinite] = STATUS_INVALID
        valid_mask = status.eq(STATUS_VALID)

        # 非 valid 的 SKU 不提供统计量，避免把部分数据算出的均值误当成完整周期统计。
        # 统计量只在有限值上计算，避免对 Inf 做减法产生无效运算告警。
        means = finite.mean(axis=1).where(valid_mask)
        stds = finite.std(axis=1, ddof=0).where(valid_mask)

        cv = pd.Series(float("nan"), index=numeric.index, dtype="float64")
        nonzero_mean = valid_mask & means.ne(0)
        cv.loc[nonzero_mean] = stds.loc[nonzero_mean] / means.loc[nonzero_mean]
        # 真实全零需求属于合法数据，约定 CV = 0，保持与 V3.4.0 相同的分类结论。
        cv.loc[valid_mask & means.eq(0)] = 0.0

        def classify(rate: float) -> str:
            if rate <= self.x_rate:
                return "X"
            if rate <= self.y_rate:
                return "Y"
            return "Z"

        classification = pd.Series(UNCLASSIFIED, index=numeric.index, dtype=object)
        classification.loc[valid_mask] = cv.loc[valid_mask].apply(classify)

        result = self.df.copy()
        result["平均需求"] = means
        result["需求标准差"] = stds
        result["变异系数CV"] = cv
        result[QUALITY_COLUMN] = status
        result["XYZ分类"] = classification

        counts_raw = classification.value_counts().to_dict()
        counts = {key: int(counts_raw.get(key, 0)) for key in ("X", "Y", "Z")}
        status_raw = status.value_counts().to_dict()
        status_counts = {key: int(status_raw.get(key, 0)) for key in STATUS_ORDER}
        # 平均 CV 只统计 valid 的 SKU；完全没有可分类 SKU 时返回 0.0，
        # 以免把 nan 带入报告等下游文本输出（可分类数量由 counts / status_counts 表达）。
        mean_cv = float(cv.loc[valid_mask].mean()) if valid_mask.any() else 0.0
        return XYZResult(result, counts, mean_cv, status_counts)
