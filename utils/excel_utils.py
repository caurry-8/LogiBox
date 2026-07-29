from pathlib import Path

import pandas as pd


def read_table(filename: str) -> pd.DataFrame:
    path = Path(filename)

    if path.suffix.lower() == '.csv':
        return pd.read_csv(filename)
    if path.suffix.lower() in {'.xlsx', '.xls'}:
        return pd.read_excel(filename)

    raise ValueError('不支持的文件格式。')


def export_dataframe(dataframe: pd.DataFrame, filename: str) -> None:
    path = Path(filename)

    if path.suffix.lower() == '.csv':
        dataframe.to_csv(filename, index=False, encoding='utf-8-sig')
        return
    if path.suffix.lower() == '.xlsx':
        dataframe.to_excel(filename, index=False)
        return

    raise ValueError('导出文件必须使用 .xlsx 或 .csv 后缀。')


class ExcelManager:
    """兼容旧代码的 Excel 管理器。"""

    def __init__(self) -> None:
        self.df: pd.DataFrame | None = None
        self.filename: str = ''

    def load(self, filename: str) -> pd.DataFrame:
        self.filename = filename
        self.df = read_table(filename)
        return self.df

    def dataframe(self) -> pd.DataFrame | None:
        return self.df

    def rows(self) -> int:
        return 0 if self.df is None else len(self.df)

    def cols(self) -> int:
        return 0 if self.df is None else len(self.df.columns)
