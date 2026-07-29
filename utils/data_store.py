from pathlib import Path

import pandas as pd
from PySide6.QtCore import QObject, Signal


class DataStore(QObject):
    """应用级共享数据中心。"""

    data_changed = Signal()
    status_changed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.df: pd.DataFrame | None = None
        self.filename: str = ''

    def load(self, filename: str) -> pd.DataFrame:
        path = Path(filename)

        if path.suffix.lower() == '.csv':
            df = pd.read_csv(filename)
        elif path.suffix.lower() in {'.xlsx', '.xls'}:
            df = pd.read_excel(filename)
        else:
            raise ValueError('暂不支持该文件格式。')

        if df.empty:
            raise ValueError('文件中没有可分析的数据。')

        self.df = df
        self.filename = filename
        self.status_changed.emit(
            f'已加载：{path.name} · {len(df)} 行 × {len(df.columns)} 列'
        )
        self.data_changed.emit()
        return df

    def replace_dataframe(self, dataframe: pd.DataFrame, status: str = '数据已更新') -> None:
        if dataframe is None or dataframe.empty:
            raise ValueError('不能写入空数据。')
        self.df = dataframe.copy()
        self.status_changed.emit(status)
        self.data_changed.emit()

    def dataframe(self) -> pd.DataFrame | None:
        return self.df

    def has_data(self) -> bool:
        return self.df is not None and not self.df.empty

    def rows(self) -> int:
        return 0 if self.df is None else len(self.df)

    def cols(self) -> int:
        return 0 if self.df is None else len(self.df.columns)

    def filename_only(self) -> str:
        return Path(self.filename).name if self.filename else ''

    def clear(self) -> None:
        self.df = None
        self.filename = ''
        self.status_changed.emit('数据已清空')
        self.data_changed.emit()
