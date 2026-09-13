import math
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

from core.config import APP_CONFIG
from utils.data_store import DataStore
from utils.matrix_utils import CELL_ORDER, CELL_STRATEGIES
from utils.quality_text import (
    coverage_text,
    excluded_reason_text,
    field_notice_line,
    format_issue_line,
    status_label,
)
from utils.quality_utils import assess_data_quality


def _format_mean_cv(value) -> str:
    """平均 CV 的展示：没有可计算 CV 的有效 SKU 时明确写「暂无有效数据」。"""
    if value is None:
        return "暂无有效数据"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "暂无有效数据"
    if math.isnan(number):
        return "暂无有效数据"
    return f"{number:.4f}"


def _add_heading(document: Document, text: str, level: int = 1) -> None:
    document.add_heading(text, level=level)


def _add_key_value_table(document: Document, rows: list[tuple[str, str]]) -> None:
    table = document.add_table(rows=1, cols=2)
    table.style = "Table Grid"
    table.rows[0].cells[0].text = "指标"
    table.rows[0].cells[1].text = "结果"
    for key, value in rows:
        cells = table.add_row().cells
        cells[0].text = key
        cells[1].text = str(value)


def generate_word_report(filename: str, store: DataStore) -> str:
    if not store.has_data():
        raise ValueError("当前没有可用于生成报告的数据。")

    path = Path(filename)
    if path.suffix.lower() != ".docx":
        path = path.with_suffix(".docx")

    document = Document()
    normal_style = document.styles["Normal"]
    normal_style.font.name = "Microsoft YaHei"
    normal_style.font.size = Pt(10.5)

    title = document.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run(f"LogiBox V{APP_CONFIG.version} 物流数据分析报告")
    run.bold = True
    run.font.size = Pt(18)

    subtitle = document.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.add_run(f"数据源：{store.filename_only()}")

    _add_heading(document, "一、数据概况")
    quality = assess_data_quality(store.dataframe())
    overview_rows = [
        ("数据行数", str(store.rows())),
        ("字段数量", str(store.cols())),
        ("缺失单元格", str(store.missing_cells())),
        ("重复行", str(store.duplicate_rows())),
        ("数据质量状态", status_label(quality.status)),
    ]
    if quality.has_key_metrics:
        overview_rows.extend(
            [
                (f"有效 SKU（{quality.key_column}）", str(quality.valid_key_count)),
                ("空值 SKU", str(quality.empty_key_count)),
                ("重复 SKU", str(quality.duplicate_key_count)),
            ]
        )
    overview_rows.append(
        (
            "数据质量问题",
            f"阻断 {quality.blocker_count} / 警告 {quality.warning_count} / 提示 {quality.info_count}",
        )
    )
    _add_key_value_table(document, overview_rows)

    if quality.issues:
        document.add_paragraph("数据质量问题明细：")
        for issue in quality.issues:
            document.add_paragraph(format_issue_line(issue), style="List Bullet")

    _add_heading(document, "二、ABC 分类分析")
    abc = store.get_analysis("abc")
    if abc:
        counts = abc.get("counts", {})
        contributions = abc.get("contributions", {})
        _add_key_value_table(
            document,
            [
                ("分析字段", abc.get("value_column", "")),
                ("A 类 SKU", counts.get("A", 0)),
                ("B 类 SKU", counts.get("B", 0)),
                ("C 类 SKU", counts.get("C", 0)),
                ("A 类金额贡献", f"{contributions.get('A', 0):.2%}"),
                ("B 类金额贡献", f"{contributions.get('B', 0):.2%}"),
                ("C 类金额贡献", f"{contributions.get('C', 0):.2%}"),
            ],
        )
    else:
        document.add_paragraph("当前尚未完成 ABC 分类分析。")

    _add_heading(document, "三、XYZ 稳定性分析")
    xyz = store.get_analysis("xyz")
    if xyz:
        counts = xyz.get("counts", {})
        classified = sum(int(counts.get(key, 0)) for key in ("X", "Y", "Z"))
        rows = [
            ("历史周期字段", ", ".join(xyz.get("period_columns", []))),
            ("X 类 SKU", counts.get("X", 0)),
            ("Y 类 SKU", counts.get("Y", 0)),
            ("Z 类 SKU", counts.get("Z", 0)),
            ("平均 CV", _format_mean_cv(xyz.get("mean_cv"))),
        ]
        # 字段语义风险：只在存在风险时追加，避免正常报告出现无意义行
        field_code = xyz.get("field_semantics")
        if field_code and field_code != "ok":
            rows.append(
                (
                    "字段语义",
                    field_notice_line(
                        field_code,
                        columns="、".join(xyz.get("atypical_period_columns") or []),
                        count=xyz.get("detected_period_count", 0),
                    ),
                )
            )
        total_count = xyz.get("total_count")
        if total_count:
            total_count = int(total_count)
            rows.extend(
                [
                    ("总 SKU", str(total_count)),
                    ("有效分类 SKU", str(classified)),
                    ("未参与分类 SKU", str(max(0, total_count - classified))),
                    ("分类覆盖率", coverage_text(classified, total_count)),
                ]
            )
        _add_key_value_table(document, rows)
        document.add_paragraph("X / Y / Z 分布基于已完成有效分类的 SKU。")
    else:
        document.add_paragraph("当前尚未完成 XYZ 稳定性分析。")

    _add_heading(document, "四、ABC × XYZ 交叉矩阵")
    matrix = store.get_analysis("matrix")
    if matrix:
        cell_counts = matrix.get("cell_counts", {})
        cell_values = matrix.get("cell_values", {})
        cell_amounts = matrix.get("cell_amounts", {})
        cell_sku_shares = matrix.get("cell_sku_shares", {})
        value_column = matrix.get("value_column", "")
        rows = [
            ("关键字段", matrix.get("key_column", "")),
            ("价值字段", value_column or "未选择，按 SKU 数量统计"),
            ("匹配 SKU 数", str(len(matrix.get("dataframe", [])))),
        ]
        input_sku_count = matrix.get("input_sku_count")
        if input_sku_count is not None:
            input_sku_count = int(input_sku_count)
            analyzed = len(matrix.get("dataframe", []))
            excluded = int(matrix.get("excluded_sku_count") or 0)
            rows.extend(
                [
                    ("矩阵分析覆盖", coverage_text(analyzed, input_sku_count)),
                    ("未参与分析 SKU", str(excluded)),
                ]
            )
            reason = excluded_reason_text(matrix.get("excluded_by_quality") or {})
            if reason:
                rows.append(("未参与原因", reason))
            rows.append(("占比口径", "基于已参与分析的 SKU"))
        for cell in CELL_ORDER:
            summary = (
                f"{cell_counts.get(cell, 0)} 个 SKU · SKU 占比 {cell_sku_shares.get(cell, 0):.2%}"
            )
            if value_column:
                summary += (
                    f" · {value_column} {cell_amounts.get(cell, 0):,.2f}"
                    f" · 金额占比 {cell_values.get(cell, 0):.2%}"
                )
            rows.append((cell, summary))
        _add_key_value_table(document, rows)
        document.add_paragraph("单元管理策略：")
        for cell in CELL_ORDER:
            strategy = CELL_STRATEGIES[cell]
            document.add_paragraph(
                f"{cell}（{strategy['title']}，优先级 {strategy['priority']}）：{strategy['action']}",
                style="List Bullet",
            )
    else:
        document.add_paragraph("当前尚未生成 ABC × XYZ 交叉矩阵。")

    _add_heading(document, "五、EOQ 计算结果")
    eoq = store.get_analysis("eoq")
    if eoq:
        rows = [(key, value) for key, value in eoq.items()]
        _add_key_value_table(document, rows)
    else:
        document.add_paragraph("当前尚未完成 EOQ 计算。")

    _add_heading(document, "六、安全库存与再订货点")
    safety = store.get_analysis("safety")
    if safety:
        _add_key_value_table(
            document,
            [
                ("安全库存", safety.get("安全库存", "")),
                ("再订货点 ROP", safety.get("再订货点 ROP", "")),
                ("Z 值", safety.get("Z 值", "")),
            ],
        )
    else:
        document.add_paragraph("当前尚未完成安全库存计算。")

    _add_heading(document, "七、分析建议")
    recommendations = [
        "优先关注 ABC 中 A 类库存的缺货风险与补货策略。",
        "对 XYZ 中 Z 类库存强化需求预测和安全库存复核。",
        "按 ABC × XYZ 矩阵区分管理强度：AZ / AY 单元优先配置安全库存与双源供应，CX / CY / CZ 单元简化流程、降低管理成本。",
        "结合 EOQ 与安全库存结果优化订货批量和再订货点。",
        "正式决策前建议结合业务周期、供应商交期和仓储容量进行校验。",
    ]
    for item in recommendations:
        document.add_paragraph(item, style="List Bullet")

    document.save(path)
    return str(path)
