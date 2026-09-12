"""LogiBox 测试套件的公共 fixture。

本文件只提供测试基础设施，不修改任何生产代码。

设计要求：
- 在导入 PySide6 之前设置无头平台，否则无显示器环境会启动失败；
- 把项目根目录加入 sys.path，使 `utils` / `pages` / `core` 可直接导入；
- 提供小型、可人工计算的测试数据，避免测试依赖复杂数据难以核对；
- 提供消息框记录器，避免测试中被模态弹窗阻塞。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 必须在导入 PySide6 之前完成，保证无头环境下 QApplication 可以创建。
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pandas as pd  # noqa: E402
from PySide6.QtGui import QFont, QFontDatabase  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

# 示例数据中的 6 个真实历史需求周期字段（不含单价、年需求量等非周期列）。
SAMPLE_PERIOD_COLUMNS = [
    "1月需求",
    "2月需求",
    "3月需求",
    "4月需求",
    "5月需求",
    "6月需求",
]

CHINESE_FONT_CANDIDATES = (
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
)


@pytest.fixture(scope="session", autouse=True)
def qapp():
    """整个测试会话共用一个无头 QApplication，并加载中文字体。

    DataStore 是 QObject，页面测试需要 QWidget，因此统一在这里初始化 Qt。
    """
    app = QApplication.instance() or QApplication([])
    for font_path in CHINESE_FONT_CANDIDATES:
        if Path(font_path).exists():
            font_id = QFontDatabase.addApplicationFont(font_path)
            families = QFontDatabase.applicationFontFamilies(font_id)
            if families:
                app.setFont(QFont(families[0], 10))
            break
    return app


@pytest.fixture(scope="session")
def project_root() -> Path:
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def sample_csv_path(project_root: Path) -> Path:
    """项目自带的示例库存数据（10 行，UTF-8）。"""
    return project_root / "data" / "sample_inventory.csv"


@pytest.fixture(scope="session")
def sample_dataframe(sample_csv_path: Path) -> pd.DataFrame:
    """直接读取示例 CSV，供算法测试使用，不经过 DataStore。"""
    return pd.read_csv(sample_csv_path, encoding="utf-8-sig")


@pytest.fixture(scope="session")
def sample_period_columns() -> list[str]:
    """示例数据中真正可用的历史需求周期字段。"""
    return list(SAMPLE_PERIOD_COLUMNS)


@pytest.fixture
def sample_store(sample_csv_path: Path):
    """已加载示例数据的 DataStore 实例。"""
    from utils.data_store import DataStore

    store = DataStore()
    store.load(str(sample_csv_path))
    return store


@pytest.fixture
def small_pricing_dataframe() -> pd.DataFrame:
    """4 行小数据，用于人工核验 ABC 与年消耗金额。

    年消耗金额 = 年需求量 × 单价 → 80 / 30 / 15 / 5（合计 130）。
    """
    return pd.DataFrame(
        {
            "SKU": ["S1", "S2", "S3", "S4"],
            "年需求量": [8, 1, 3, 1],
            "单价": [10, 30, 5, 5],
        }
    )


@pytest.fixture
def matrix_source_dataframe() -> pd.DataFrame:
    """6 行交叉矩阵测试数据，ABC 与 XYZ 结果均可人工计算。

    年消耗金额合计 1000，ABC 分类为 A=2 / B=1 / C=3；
    需求波动（CV，ddof=0）为 X=2 / Y=2 / Z=2；
    交叉后 AX=2 / BY=1 / CY=1 / CZ=2。
    """
    return pd.DataFrame(
        {
            "SKU": ["X1", "X2", "Y1", "Y2", "Z1", "Z2"],
            "年消耗金额": [400.0, 300.0, 200.0, 60.0, 30.0, 10.0],
            "1月": [100, 200, 100, 50, 10, 5],
            "2月": [100, 200, 120, 60, 50, 40],
            "3月": [100, 200, 80, 70, 20, 15],
            "4月": [100, 200, 100, 60, 40, 20],
        }
    )


class RecordedMessageBox:
    """记录弹窗调用，替代真实 QMessageBox，避免测试被模态窗口阻塞。

    只替换 UI 提示层，不涉及任何算法或业务逻辑。
    """

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    def _record(self, level: str, *args, **kwargs) -> None:
        title = args[1] if len(args) > 1 else kwargs.get("title", "")
        text = args[2] if len(args) > 2 else kwargs.get("text", "")
        self.calls.append((level, str(title), str(text)))

    def information(self, *args, **kwargs) -> None:
        self._record("information", *args, **kwargs)

    def warning(self, *args, **kwargs) -> None:
        self._record("warning", *args, **kwargs)

    def critical(self, *args, **kwargs) -> None:
        self._record("critical", *args, **kwargs)

    def question(self, *args, **kwargs):
        self._record("question", *args, **kwargs)
        return None

    @property
    def texts(self) -> list[str]:
        return [text for _level, _title, text in self.calls]


@pytest.fixture
def message_box_recorder(monkeypatch):
    """把页面模块中的 QMessageBox 替换为记录器。

    页面通过模块级名字 `QMessageBox` 调用，因此替换模块属性即可拦截，
    无需也不应改动生产代码。
    """
    recorder = RecordedMessageBox()
    module_paths = (
        "pages.safety_page.QMessageBox",
        "pages.eoq_page.QMessageBox",
        "pages.abc_page.QMessageBox",
        "pages.xyz_page.QMessageBox",
        "pages.matrix_page.QMessageBox",
        "pages.import_page.QMessageBox",
        "pages.report_page.QMessageBox",
    )
    for module_path in module_paths:
        monkeypatch.setattr(module_path, recorder, raising=False)
    return recorder
