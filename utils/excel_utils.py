from pathlib import Path

import pandas as pd


def export_dataframe(dataframe: pd.DataFrame, filename: str) -> None:
    suffix = Path(filename).suffix.lower()
    if suffix == ".csv":
        dataframe.to_csv(filename, index=False, encoding="utf-8-sig")
        return
    if suffix == ".xlsx":
        dataframe.to_excel(filename, index=False)
        return
    raise ValueError("导出文件请使用 .xlsx 或 .csv 后缀。")
