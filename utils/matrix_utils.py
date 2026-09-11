from dataclasses import dataclass, field

import pandas as pd

ABC_ORDER = ["A", "B", "C"]
XYZ_ORDER = ["X", "Y", "Z"]
CELL_ORDER = [f"{a}{x}" for a in ABC_ORDER for x in XYZ_ORDER]

ABC_LABELS = {
    "A": "A 类 · 高价值",
    "B": "B 类 · 中价值",
    "C": "C 类 · 低价值",
}

XYZ_LABELS = {
    "X": "X 类 · 需求稳定",
    "Y": "Y 类 · 需求波动",
    "Z": "Z 类 · 需求不稳定",
}

# 每个矩阵单元的库存管理策略建议。它们是可解释的静态业务规则，不是预测模型。
CELL_STRATEGIES: dict[str, dict[str, str]] = {
    "AX": {
        "title": "精准补货 · 精益库存",
        "priority": "高",
        "action": "重点控制库存，采用精确需求预测和严格补货策略，保障供应连续性。",
        "target": "库存周转率、缺货率",
    },
    "AY": {
        "title": "重点监控 · 适度缓冲",
        "priority": "高",
        "action": "加强需求监控，适当设置安全库存，定期复核需求偏差并避免过量囤积。",
        "target": "预测准确率、库存天数",
    },
    "AZ": {
        "title": "最高优先级 · 强缓冲",
        "priority": "极高",
        "action": "重点关注需求不确定性，避免过量库存；提高安全库存复核频率并建立异常预警。",
        "target": "服务水平、缺货损失",
    },
    "BX": {
        "title": "标准自动化 · 常规管理",
        "priority": "中",
        "action": "采用常规库存控制策略，可结合 EOQ 参数进行周期性补货。",
        "target": "订货成本、周转率",
    },
    "BY": {
        "title": "常规管理 · 定期复核",
        "priority": "中",
        "action": "根据实际需求动态调整补货参数，定期复核安全库存与订货批量。",
        "target": "库存持有成本",
    },
    "BZ": {
        "title": "加强监控 · 提高缓冲",
        "priority": "中高",
        "action": "加强库存监控，避免库存积压；对异常波动及时复核补货计划。",
        "target": "缺货率、库存金额",
    },
    "CX": {
        "title": "简化管理 · 批量订货",
        "priority": "低",
        "action": "采用简化库存管理策略，可使用低频率、批量订货以降低管理成本。",
        "target": "订货成本、管理工时",
    },
    "CY": {
        "title": "简化管理 · 合并采购",
        "priority": "低",
        "action": "采用常规管理，适当合并采购批次，控制管理成本。",
        "target": "采购批次、管理成本",
    },
    "CZ": {
        "title": "最简管理 · 按需补货",
        "priority": "低",
        "action": "避免过度备货，可依据实际需求灵活补货，重点控制呆滞风险。",
        "target": "库存占用、呆滞风险",
    },
}


@dataclass
class MatrixResult:
    """ABC × XYZ 合并后的明细、分布与静态策略。"""

    dataframe: pd.DataFrame
    cell_counts: dict[str, int]
    cell_values: dict[str, float]
    cell_amounts: dict[str, float]
    cell_sku_shares: dict[str, float]
    total_value: float
    key_column: str
    value_column: str
    strategies: dict[str, dict[str, str]] = field(default_factory=dict)

    @property
    def has_amount(self) -> bool:
        """是否存在可展示的金额/价值字段，而非仅按 SKU 数量统计。"""
        return bool(self.value_column)

    @property
    def value_label(self) -> str:
        return self.value_column or "SKU 数量"

    def cell_label(self, abc: str, xyz: str) -> str:
        return f"{abc}{xyz}"

    def summary_rows(self) -> list[tuple[str, str]]:
        rows: list[tuple[str, str]] = []
        for cell in CELL_ORDER:
            row = f"{self.cell_counts.get(cell, 0)} 个 SKU · SKU 占比 {self.cell_sku_shares.get(cell, 0.0):.2%}"
            if self.has_amount:
                row += f" · {self.value_label}占比 {self.cell_values.get(cell, 0.0):.2%}"
            rows.append((cell, row))
        return rows


class ABCXYZMatrixAnalyzer:
    """将 ABC 价值分类和 XYZ 需求稳定性分类组合为 3×3 库存策略矩阵。"""

    def __init__(
        self,
        abc_dataframe: pd.DataFrame,
        xyz_dataframe: pd.DataFrame,
        key_column: str,
        value_column: str | None = None,
        abc_column: str = "ABC分类",
        xyz_column: str = "XYZ分类",
    ) -> None:
        self.abc_df = abc_dataframe.copy()
        self.xyz_df = xyz_dataframe.copy()
        self.key_column = key_column
        self.value_column = value_column or ""
        self.abc_column = abc_column
        self.xyz_column = xyz_column

    def _validate(self) -> None:
        if self.key_column not in self.abc_df.columns:
            raise ValueError(f"ABC 结果中找不到关键字段：{self.key_column}")
        if self.key_column not in self.xyz_df.columns:
            raise ValueError(f"XYZ 结果中找不到关键字段：{self.key_column}")
        if self.abc_column not in self.abc_df.columns:
            raise ValueError("ABC 结果缺少分类列，请先完成 ABC 分析。")
        if self.xyz_column not in self.xyz_df.columns:
            raise ValueError("XYZ 结果缺少分类列，请先完成 XYZ 分析。")
        if self.abc_df[self.key_column].duplicated().any():
            raise ValueError(
                f"关键字段「{self.key_column}」存在重复值，无法与 XYZ 结果一一对应。请选择唯一标识字段。"
            )
        if self.xyz_df[self.key_column].duplicated().any():
            raise ValueError(
                f"关键字段「{self.key_column}」在 XYZ 结果中存在重复值，请选择唯一标识字段。"
            )

    def _build_merge_frames(self) -> tuple[pd.DataFrame, pd.DataFrame, str]:
        """保留 ABC 原始字段，并只补充 XYZ 特有的结果字段。"""
        abc_part = self.abc_df.copy()
        if self.value_column and self.value_column in abc_part.columns:
            abc_part[self.value_column] = pd.to_numeric(
                abc_part[self.value_column], errors="coerce"
            ).fillna(0)
            value_field = self.value_column
        else:
            # 未选择数值字段时仅统计 SKU 数量，不伪造金额。
            self.value_column = ""
            value_field = "_matrix_count"
            abc_part[value_field] = 1.0

        # 大部分原始字段在两份结果中重复，避免 merge 产生 _x/_y；保留 XYZ 独有计算结果。
        xyz_columns = [self.key_column, self.xyz_column]
        for column in self.xyz_df.columns:
            if column not in abc_part.columns and column != self.key_column:
                xyz_columns.append(column)
        xyz_part = self.xyz_df.loc[:, list(dict.fromkeys(xyz_columns))].copy()
        return abc_part, xyz_part, value_field

    def analyze(self) -> MatrixResult:
        self._validate()
        abc_part, xyz_part, value_field = self._build_merge_frames()

        merged = abc_part.merge(xyz_part, on=self.key_column, how="inner", validate="one_to_one")
        if merged.empty:
            raise ValueError("ABC 与 XYZ 结果无法按关键字段匹配，请确认两者使用同一份数据。")

        merged["矩阵单元"] = (
            merged[self.abc_column].astype(str) + merged[self.xyz_column].astype(str)
        )
        merged = merged[merged["矩阵单元"].isin(CELL_ORDER)].reset_index(drop=True)
        if merged.empty:
            raise ValueError("ABC 与 XYZ 分类结果没有可用的交叉矩阵数据。")

        total_value = float(merged[value_field].sum())
        total_skus = len(merged)
        counts_raw = merged["矩阵单元"].value_counts().to_dict()
        amounts_raw = merged.groupby("矩阵单元")[value_field].sum().to_dict()

        cell_counts = {cell: int(counts_raw.get(cell, 0)) for cell in CELL_ORDER}
        cell_amounts = {cell: float(amounts_raw.get(cell, 0.0)) for cell in CELL_ORDER}
        cell_values = {
            cell: (cell_amounts[cell] / total_value if total_value > 0 else 0.0)
            for cell in CELL_ORDER
        }
        cell_sku_shares = {
            cell: (cell_counts[cell] / total_skus if total_skus > 0 else 0.0)
            for cell in CELL_ORDER
        }

        merged["SKU占比"] = 1 / total_skus if total_skus > 0 else 0.0
        if self.value_column:
            merged["金额占比"] = merged[value_field] / total_value if total_value > 0 else 0.0
        merged = merged.sort_values(
            by=["矩阵单元", value_field], ascending=[True, False]
        ).reset_index(drop=True)
        if value_field == "_matrix_count":
            merged = merged.drop(columns=[value_field])

        return MatrixResult(
            dataframe=merged,
            cell_counts=cell_counts,
            cell_values=cell_values,
            cell_amounts=cell_amounts,
            cell_sku_shares=cell_sku_shares,
            total_value=total_value,
            key_column=self.key_column,
            value_column=self.value_column,
            strategies={cell: CELL_STRATEGIES[cell] for cell in CELL_ORDER},
        )

    @staticmethod
    def recommend_key_column(columns: list[str]) -> str:
        candidates = [
            "SKU",
            "sku",
            "物料编码",
            "物料编号",
            "物料号",
            "商品编码",
            "商品编号",
            "货号",
            "编码",
            "编号",
            "产品编码",
            "Item",
            "item",
            "ID",
            "id",
        ]
        for name in candidates:
            if name in columns:
                return name
        return columns[0] if columns else ""
