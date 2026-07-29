from dataclasses import dataclass

import pandas as pd


@dataclass
class ABCResult:
    dataframe: pd.DataFrame
    counts: dict[str, int]
    contributions: dict[str, float]


class ABCAnalyzer:
    def __init__(
        self,
        dataframe: pd.DataFrame,
        value_column: str,
        a_rate: float = 0.80,
        b_rate: float = 0.95,
    ) -> None:
        self.df = dataframe.copy()
        self.value_column = value_column
        self.a_rate = a_rate
        self.b_rate = b_rate

    def analyze(self) -> ABCResult:
        if self.value_column not in self.df.columns:
            raise ValueError(f'找不到分析字段：{self.value_column}')

        if not 0 < self.a_rate < self.b_rate < 1:
            raise ValueError('阈值必须满足：0 < A 阈值 < B 阈值 < 1。')

        values = pd.to_numeric(self.df[self.value_column], errors='coerce')
        if values.isna().all():
            raise ValueError('分析字段不是有效的数值列。')

        self.df[self.value_column] = values.fillna(0)
        if (self.df[self.value_column] < 0).any():
            raise ValueError('分析字段不能包含负数。')

        total = self.df[self.value_column].sum()
        if total <= 0:
            raise ValueError('分析字段总值必须大于 0。')

        self.df = self.df.sort_values(by=self.value_column, ascending=False).reset_index(drop=True)
        self.df['金额占比'] = self.df[self.value_column] / total
        self.df['累计占比'] = self.df['金额占比'].cumsum()

        def classify(rate: float) -> str:
            if rate <= self.a_rate:
                return 'A'
            if rate <= self.b_rate:
                return 'B'
            return 'C'

        self.df['ABC分类'] = self.df['累计占比'].apply(classify)

        counts_raw = self.df['ABC分类'].value_counts().to_dict()
        counts = {
            'A': int(counts_raw.get('A', 0)),
            'B': int(counts_raw.get('B', 0)),
            'C': int(counts_raw.get('C', 0)),
        }

        contributions_raw = self.df.groupby('ABC分类')[self.value_column].sum().to_dict()
        contributions = {
            'A': float(contributions_raw.get('A', 0)) / total,
            'B': float(contributions_raw.get('B', 0)) / total,
            'C': float(contributions_raw.get('C', 0)) / total,
        }

        return ABCResult(
            dataframe=self.df,
            counts=counts,
            contributions=contributions,
        )

    @staticmethod
    def build_consumption_value(
        dataframe: pd.DataFrame,
        demand_column: str,
        price_column: str,
    ) -> pd.DataFrame:
        df = dataframe.copy()
        if demand_column not in df.columns:
            raise ValueError(f'找不到需求量字段：{demand_column}')
        if price_column not in df.columns:
            raise ValueError(f'找不到单价字段：{price_column}')

        demand = pd.to_numeric(df[demand_column], errors='coerce')
        price = pd.to_numeric(df[price_column], errors='coerce')

        if demand.isna().all() or price.isna().all():
            raise ValueError('需求量或单价字段无法转换为有效数值。')

        df['年消耗金额'] = demand.fillna(0) * price.fillna(0)
        return df
