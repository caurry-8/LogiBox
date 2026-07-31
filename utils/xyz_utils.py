from dataclasses import dataclass

import pandas as pd


@dataclass
class XYZResult:
    dataframe: pd.DataFrame
    counts: dict[str, int]
    mean_cv: float


class XYZAnalyzer:
    """Classify demand stability with coefficient of variation (CV)."""

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

    def analyze(self) -> XYZResult:
        if len(self.period_columns) < 2:
            raise ValueError("XYZ 分析至少需要选择 2 个历史需求周期字段。")
        if not 0 < self.x_rate < self.y_rate:
            raise ValueError("阈值必须满足：0 < X 阈值 < Y 阈值。")

        numeric = self.df[self.period_columns].apply(pd.to_numeric, errors="coerce")
        if numeric.notna().sum().sum() == 0:
            raise ValueError("所选周期字段没有可用数值。")
        numeric = numeric.fillna(0)
        if (numeric < 0).any().any():
            raise ValueError("历史需求数据不能包含负数。")

        means = numeric.mean(axis=1)
        stds = numeric.std(axis=1, ddof=0)
        cv = stds.div(means.replace(0, pd.NA)).fillna(0)

        def classify(rate: float) -> str:
            if rate <= self.x_rate:
                return "X"
            if rate <= self.y_rate:
                return "Y"
            return "Z"

        result = self.df.copy()
        result["平均需求"] = means
        result["需求标准差"] = stds
        result["变异系数CV"] = cv
        result["XYZ分类"] = cv.apply(classify)

        counts_raw = result["XYZ分类"].value_counts().to_dict()
        counts = {key: int(counts_raw.get(key, 0)) for key in ["X", "Y", "Z"]}
        return XYZResult(result, counts, float(cv.mean()))
