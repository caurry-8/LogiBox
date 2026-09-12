"""DataStore 共享数据层回归基线。

覆盖：CSV 导入（含 UTF-8 示例数据与 GBK 中文 CSV）、数据概览指标、
分析结果的写入 / 读取 / 状态、清空与重新导入后的状态一致性。
本文件只验证当前行为，不修改生产代码。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from utils.data_store import DataStore

SAMPLE_ROWS = 10
SAMPLE_COLUMNS = 10


def test_new_store_has_no_data():
    store = DataStore()
    assert store.has_data() is False
    assert store.dataframe() is None
    assert store.rows() == 0
    assert store.cols() == 0
    assert store.filename_only() == "未加载数据"


def test_load_sample_csv_returns_expected_shape(sample_store, sample_dataframe):
    assert sample_store.rows() == SAMPLE_ROWS
    assert sample_store.cols() == SAMPLE_COLUMNS
    assert len(sample_dataframe) == SAMPLE_ROWS


def test_load_sample_csv_detects_utf8_encoding(sample_store):
    assert sample_store.encoding == "UTF-8"
    assert sample_store.has_data() is True


def test_load_sample_csv_reports_status_message(sample_csv_path):
    messages: list[str] = []
    store = DataStore()
    store.status_changed.connect(messages.append)
    store.load(str(sample_csv_path))

    assert messages, "加载数据应发出状态消息"
    assert "UTF-8" in messages[0]
    assert f"{SAMPLE_ROWS} 行" in messages[0]


def test_filename_only_returns_basename(sample_store):
    assert sample_store.filename_only() == "sample_inventory.csv"


def test_load_emits_data_and_analysis_changed(sample_csv_path):
    store = DataStore()
    events: list[str] = []
    store.data_changed.connect(lambda: events.append("data"))
    store.analysis_changed.connect(lambda: events.append("analysis"))

    store.load(str(sample_csv_path))

    assert events == ["data", "analysis"]


def test_numeric_columns_excludes_text_columns(sample_store):
    numeric = sample_store.numeric_columns()
    assert "年需求量" in numeric
    assert "单价" in numeric
    assert "1月需求" in numeric
    assert "SKU" not in numeric
    assert "仓库" not in numeric


def test_sample_data_has_no_missing_or_duplicate_rows(sample_store):
    assert sample_store.missing_cells() == 0
    assert sample_store.duplicate_rows() == 0


def test_missing_and_duplicate_metrics_on_dirty_csv(tmp_path):
    dirty = tmp_path / "dirty.csv"
    dirty.write_text(
        "SKU,金额,1月,2月\nS1,10,1,2\nS1,10,1,2\nS2,20,,4\n",
        encoding="utf-8",
    )
    store = DataStore()
    store.load(str(dirty))

    assert store.rows() == 3
    assert store.duplicate_rows() == 1
    assert store.missing_cells() == 1


def test_gbk_chinese_csv_is_read_without_mojibake(tmp_path):
    """中文版 Excel 另存为 CSV 默认是 GBK，应能正确读取而不是乱码。"""
    gbk_file = tmp_path / "gbk_inventory.csv"
    gbk_file.write_text(
        "物料编码,物料名称,年需求量,单价\n"
        "A001,轴承组件,12000,15.5\n"
        "A002,液压阀体,8500,22.0\n",
        encoding="gbk",
    )
    store = DataStore()
    store.load(str(gbk_file))

    assert store.encoding == "GBK / GB18030"
    assert list(store.dataframe().columns) == ["物料编码", "物料名称", "年需求量", "单价"]
    assert store.dataframe().iat[0, 1] == "轴承组件"
    assert store.dataframe().iat[1, 0] == "A002"


def test_set_and_get_analysis_result(sample_store):
    result = {"EOQ": 894.43, "总成本": 4472.14}
    sample_store.set_analysis("eoq", result)

    assert sample_store.has_analysis("eoq") is True
    assert sample_store.get_analysis("eoq") == result


def test_get_unknown_analysis_returns_none(sample_store):
    assert sample_store.get_analysis("不存在的分析") is None
    assert sample_store.has_analysis("不存在的分析") is False


def test_set_analysis_emits_analysis_changed(sample_store):
    events: list[str] = []
    sample_store.analysis_changed.connect(lambda: events.append("analysis"))
    sample_store.set_analysis("abc", {"counts": {"A": 1, "B": 1, "C": 1}})

    assert events == ["analysis"]


def test_set_analysis_overwrites_previous_result(sample_store):
    sample_store.set_analysis("eoq", {"EOQ": 1.0})
    sample_store.set_analysis("eoq", {"EOQ": 2.0})

    assert sample_store.get_analysis("eoq") == {"EOQ": 2.0}


def test_clear_removes_data_and_analysis(sample_store):
    sample_store.set_analysis("abc", {"counts": {"A": 1}})
    sample_store.clear()

    assert sample_store.has_data() is False
    assert sample_store.analysis_results == {}
    assert sample_store.filename == ""
    assert sample_store.encoding == ""
    assert sample_store.rows() == 0
    assert sample_store.filename_only() == "未加载数据"


def test_reloading_data_discards_previous_analysis(sample_store):
    """重新导入数据后，旧的分析结果必须失效，避免出现新旧数据混用。"""
    sample_store.set_analysis("abc", {"counts": {"A": 1}})
    sample_store.set_analysis("xyz", {"counts": {"X": 1}})
    assert sample_store.has_analysis("abc") is True

    sample_store.load(str(sample_store.filename))

    assert sample_store.analysis_results == {}
    assert sample_store.has_analysis("abc") is False


def test_reload_after_clear_restores_data(sample_csv_path):
    store = DataStore()
    store.load(str(sample_csv_path))
    store.clear()
    assert store.has_data() is False

    store.load(str(sample_csv_path))

    assert store.has_data() is True
    assert store.rows() == SAMPLE_ROWS
    assert store.encoding == "UTF-8"


def test_unsupported_extension_is_rejected(tmp_path):
    unsupported = tmp_path / "notes.txt"
    unsupported.write_text("这不是表格数据", encoding="utf-8")

    store = DataStore()
    with pytest.raises(ValueError, match="不支持的文件格式"):
        store.load(str(unsupported))


def test_header_only_csv_is_rejected(tmp_path):
    empty = tmp_path / "empty.csv"
    empty.write_text("SKU,金额,1月\n", encoding="utf-8")

    store = DataStore()
    with pytest.raises(ValueError, match="没有可用数据"):
        store.load(str(empty))


def test_missing_file_is_rejected():
    store = DataStore()
    with pytest.raises(FileNotFoundError):
        store.load(str(Path("__不存在的文件__.csv")))


def test_dataframe_reference_is_shared_not_copied(sample_store):
    """记录当前行为：dataframe() 返回的是内部引用，页面直接修改会影响共享数据。"""
    first = sample_store.dataframe()
    second = sample_store.dataframe()

    assert first is second


def test_analysis_result_is_reused_not_copied(sample_store):
    """记录当前行为：get_analysis 返回内部字典引用，外部改动会写回 DataStore。"""
    payload = {"counts": {"A": 1}}
    sample_store.set_analysis("abc", payload)

    assert sample_store.get_analysis("abc") is payload
