from pathlib import Path

import pandas as pd
from PySide6.QtCore import QObject, Signal


class DataStore(QObject):
    """Shared application data and analysis state."""

    data_changed = Signal()
    analysis_changed = Signal()
    status_changed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.df: pd.DataFrame | None = None
        self.filename: str = ""
        self.analysis_results: dict[str, dict] = {}

    def load(self, filename: str) -> pd.DataFrame:
        path = Path(filename)
        suffix = path.suffix.lower()
        if suffix == ".csv":
            df = pd.read_csv(filename)
        elif suffix in {".xlsx", ".xls"}:
            df = pd.read_excel(filename)
        else:
            raise ValueError("不支持的文件格式。请选择 CSV、XLS 或 XLSX。")
        if df.empty:
            raise ValueError("文件中没有可用数据。")
        self.df = df
        self.filename = str(path)
        self.analysis_results.clear()
        self.status_changed.emit(f"已加载 {path.name} · {len(df)} 行 × {len(df.columns)} 列")
        self.data_changed.emit()
        self.analysis_changed.emit()
        return df

    def dataframe(self) -> pd.DataFrame | None:
        return self.df

    def has_data(self) -> bool:
        return self.df is not None and not self.df.empty

    def rows(self) -> int:
        return 0 if self.df is None else len(self.df)

    def cols(self) -> int:
        return 0 if self.df is None else len(self.df.columns)

    def filename_only(self) -> str:
        return Path(self.filename).name if self.filename else "未加载数据"

    def numeric_columns(self) -> list[str]:
        if self.df is None:
            return []
        columns: list[str] = []
        for column in self.df.columns:
            values = pd.to_numeric(self.df[column], errors="coerce")
            if values.notna().any():
                columns.append(str(column))
        return columns

    def missing_cells(self) -> int:
        return 0 if self.df is None else int(self.df.isna().sum().sum())

    def duplicate_rows(self) -> int:
        return 0 if self.df is None else int(self.df.duplicated().sum())

    def set_analysis(self, name: str, result: dict) -> None:
        self.analysis_results[name] = result
        self.status_changed.emit(f"分析已更新：{name}")
        self.analysis_changed.emit()

    def get_analysis(self, name: str) -> dict | None:
        return self.analysis_results.get(name)

    def has_analysis(self, name: str) -> bool:
        return name in self.analysis_results

    def clear(self) -> None:
        self.df = None
        self.filename = ""
        self.analysis_results.clear()
        self.status_changed.emit("数据已清空")
        self.data_changed.emit()
        self.analysis_changed.emit()
