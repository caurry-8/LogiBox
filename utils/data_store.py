from pathlib import Path

import pandas as pd
from PySide6.QtCore import QObject, Signal

# 候选编码：中文版 Excel / WPS 另存为 CSV 默认 GBK，繁体环境常见 Big5。
CSV_ENCODINGS = ("utf-8-sig", "gb18030", "big5")
ENCODING_LABELS = {
    "utf-8-sig": "UTF-8",
    "gb18030": "GBK / GB18030",
    "big5": "Big5（繁体）",
}

# 用错编码解码时，这些区段会大量出现「像字但不是正常中文」的字符，作为判定依据。
_SUSPICIOUS_RANGES = (
    (0x2500, 0x257F),  # 制表符
    (0x2600, 0x26FF),  # 杂项符号
    (0x0370, 0x03FF),  # 希腊字母
    (0x0400, 0x04FF),  # 西里尔字母
    (0x3040, 0x30FF),  # 日文假名
    (0xE000, 0xF8FF),  # 私用区
    (0x3400, 0x4DBF),  # CJK 扩展 A（罕用字）
    (0x20000, 0x3FFFF),  # CJK 扩展 B 及以上
)
_PREVIEW_BYTES = 65536


def _suspicion_score(text: str) -> float:
    """估算一段文本「看起来不像正常中文」的程度，0 表示完全正常。"""
    if not text:
        return 0.0
    suspicious = 0
    counted = 0
    for char in text:
        code = ord(char)
        if code < 0x80 or char.isspace():
            continue
        counted += 1
        if 0x4E00 <= code <= 0x9FFF:  # 常用汉字
            continue
        if 0x3000 <= code <= 0x303F:  # 中文标点
            continue
        if 0xFF00 <= code <= 0xFFEF:  # 全角符号
            continue
        if any(low <= code <= high for low, high in _SUSPICIOUS_RANGES):
            suspicious += 1
    if counted == 0:
        return 0.0
    return suspicious / counted


def read_csv_any_encoding(path: Path) -> tuple[pd.DataFrame, str]:
    """自动识别 CSV 编码并读取，避免中文内容变成乱码。

    做法：先用每种候选编码解码文件开头，按「可疑字符占比」从低到高排序，
    再按这个顺序做严格解码读取。这样既能处理 GBK 文件，也能避免
    gb18030 过于宽松、把 Big5 文件误判成乱码的问题。
    """
    with path.open("rb") as handle:
        preview = handle.read(_PREVIEW_BYTES)

    ranked = sorted(
        CSV_ENCODINGS,
        key=lambda enc: _suspicion_score(preview.decode(enc, errors="ignore")),
    )

    last_error: UnicodeDecodeError | None = None
    for encoding in ranked:
        try:
            return pd.read_csv(path, encoding=encoding), encoding
        except UnicodeDecodeError as exc:
            last_error = exc
    raise ValueError(
        "无法识别该 CSV 文件的编码。请用记事本或 Excel 将其另存为 "
        "UTF-8 或 GBK 编码后重试。"
    ) from last_error


class DataStore(QObject):
    """Shared application data and analysis state."""

    data_changed = Signal()
    analysis_changed = Signal()
    status_changed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.df: pd.DataFrame | None = None
        self.filename: str = ""
        self.encoding: str = ""
        self.analysis_results: dict[str, dict] = {}

    def load(self, filename: str) -> pd.DataFrame:
        path = Path(filename)
        suffix = path.suffix.lower()
        if suffix == ".csv":
            df, encoding = read_csv_any_encoding(path)
            self.encoding = ENCODING_LABELS.get(encoding, encoding)
        elif suffix in {".xlsx", ".xls"}:
            df = pd.read_excel(filename)
            self.encoding = "Excel"
        else:
            raise ValueError("不支持的文件格式。请选择 CSV、XLS 或 XLSX。")
        if df.empty:
            raise ValueError("文件中没有可用数据。")
        self.df = df
        self.filename = str(path)
        self.analysis_results.clear()
        self.status_changed.emit(
            f"已加载 {path.name} · {len(df)} 行 × {len(df.columns)} 列 · 编码 {self.encoding}"
        )
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
        self.encoding = ""
        self.analysis_results.clear()
        self.status_changed.emit("数据已清空")
        self.data_changed.emit()
        self.analysis_changed.emit()
