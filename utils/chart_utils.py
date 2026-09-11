from __future__ import annotations

import warnings

import matplotlib
from matplotlib import font_manager
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle


BACKGROUND = "#161A1F"
AXES_BACKGROUND = "#1C2128"
TEXT_PRIMARY = "#E8EDF3"
TEXT_SECONDARY = "#B6C0CC"
BORDER = "#39414B"
GRID = "#AAB4C0"
ABC_COLORS = ["#28C7FA", "#6C7BFF", "#A970FF"]
MATRIX_COLORS = ["#131A20", "#17415A", "#1E7FA8", "#28C7FA"]
MATRIX_CMAP = LinearSegmentedColormap.from_list("logibox_matrix", MATRIX_COLORS)


def configure_chinese_font() -> None:
    preferred = [
        "Microsoft YaHei",
        "SimHei",
        "SimSun",
        "Microsoft JhengHei",
        "Noto Sans CJK SC",
        "Source Han Sans CN",
    ]
    installed = {font.name for font in font_manager.fontManager.ttflist}
    for name in preferred:
        if name in installed:
            matplotlib.rcParams["font.sans-serif"] = [name]
            break
    matplotlib.rcParams["axes.unicode_minus"] = False


configure_chinese_font()


def _safe_tight_layout(figure: Figure, pad: float = 1.4) -> None:
    """画布过小时 tight_layout 会告警，这里静默处理，避免控制台刷警告。"""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            figure.tight_layout(pad=pad)
    except Exception:
        pass


class ChartCanvas(FigureCanvasQTAgg):
    """Reusable Matplotlib canvas with the LogiBox dark theme."""

    def __init__(self) -> None:
        self.figure = Figure(figsize=(5, 3.2), dpi=100, facecolor=BACKGROUND)
        super().__init__(self.figure)
        self.axes = self.figure.add_subplot(111)
        self._apply_axes_theme()

    def _apply_axes_theme(self) -> None:
        self.axes.set_axis_on()
        self.axes.set_facecolor(AXES_BACKGROUND)
        self.axes.tick_params(colors=TEXT_SECONDARY, labelsize=9)
        for spine in self.axes.spines.values():
            spine.set_color(BORDER)

    def clear_chart(self) -> None:
        # Pareto 图会创建第二个 Y 轴；完整清空 Figure 才不会把旧坐标轴残留到下一张图。
        self.figure.clear()
        self.axes = self.figure.add_subplot(111)
        self._apply_axes_theme()

    def _show_empty_state(self, message: str = "暂无数据") -> None:
        self.axes.text(
            0.5,
            0.5,
            message,
            ha="center",
            va="center",
            color=TEXT_SECONDARY,
            fontsize=12,
            transform=self.axes.transAxes,
        )
        self.axes.set_axis_off()
        self.draw_idle()

    def show_empty(self, message: str = "暂无数据") -> None:
        """Public empty-state helper for pages that have not produced data yet."""
        self.clear_chart()
        self._show_empty_state(message)

    def draw_abc_pie(
        self,
        labels: list[str],
        values: list[int],
        title: str = "ABC 分类数量占比",
    ) -> None:
        self.clear_chart()
        if not values or sum(values) <= 0:
            self._show_empty_state()
            return

        self.axes.pie(
            values,
            labels=labels,
            autopct="%1.1f%%",
            startangle=90,
            colors=ABC_COLORS[: len(values)],
            textprops={"color": TEXT_PRIMARY, "fontsize": 9},
            wedgeprops={"linewidth": 1.2, "edgecolor": BACKGROUND},
        )
        self.axes.set_title(title, color=TEXT_PRIMARY, fontsize=11, pad=10)
        self.draw_idle()

    def draw_abc_bar(
        self,
        labels: list[str],
        values: list[int],
        title: str = "ABC 分类 SKU 数量",
    ) -> None:
        self.clear_chart()
        if not values or sum(values) <= 0:
            self._show_empty_state()
            return

        bars = self.axes.bar(
            labels,
            values,
            color=ABC_COLORS[: len(values)],
            width=0.58,
        )
        self.axes.set_title(title, color=TEXT_PRIMARY, fontsize=11, pad=10)
        self.axes.set_ylabel("SKU 数量", color="#9CA8B5", fontsize=9)
        self.axes.grid(axis="y", alpha=0.15, color=GRID)
        self.axes.set_axisbelow(True)

        for bar, value in zip(bars, values):
            self.axes.annotate(
                str(value),
                xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                xytext=(0, 4),
                textcoords="offset points",
                ha="center",
                va="bottom",
                color=TEXT_PRIMARY,
                fontsize=9,
            )

        _safe_tight_layout(self.figure)
        self.draw_idle()

    def draw_pareto(
        self,
        labels: list[str],
        values: list[float],
        title: str = "ABC Pareto 图",
        value_label: str = "金额",
    ) -> None:
        """绘制库存价值的 Pareto 柱线图：柱为金额，线为累计金额占比。"""
        self.clear_chart()
        if not values or sum(abs(float(value)) for value in values) <= 0:
            self._show_empty_state()
            return

        numeric_values = [max(0.0, float(value)) for value in values]
        total = sum(numeric_values)
        cumulative = []
        running = 0.0
        for value in numeric_values:
            running += value
            cumulative.append(running / total if total else 0.0)

        indices = list(range(len(labels)))
        bars = self.axes.bar(indices, numeric_values, color="#2f81f7", width=0.68, label=value_label)
        self.axes.set_title(title, color=TEXT_PRIMARY, fontsize=11, pad=10)
        self.axes.set_ylabel(value_label, color=TEXT_SECONDARY, fontsize=9)
        self.axes.set_xticks(indices)
        self.axes.set_xticklabels(labels, rotation=35, ha="right", color=TEXT_SECONDARY, fontsize=8)
        self.axes.tick_params(axis="y", colors=TEXT_SECONDARY, labelsize=8)
        self.axes.grid(axis="y", alpha=0.15, color=GRID)
        self.axes.set_axisbelow(True)

        cumulative_axes = self.axes.twinx()
        cumulative_axes.set_facecolor("none")
        cumulative_axes.plot(
            indices,
            cumulative,
            color="#d29922",
            marker="o",
            markersize=3.5,
            linewidth=1.8,
            label="累计金额占比",
        )
        cumulative_axes.set_ylim(0, 1.05)
        cumulative_axes.set_ylabel("累计金额占比", color="#d29922", fontsize=9)
        cumulative_axes.tick_params(axis="y", colors="#d29922", labelsize=8)
        cumulative_axes.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1])
        cumulative_axes.set_yticklabels([f"{rate:.0%}" for rate in [0, 0.2, 0.4, 0.6, 0.8, 1]])
        for spine in cumulative_axes.spines.values():
            spine.set_color(BORDER)

        self.axes.legend([bars, cumulative_axes.lines[0]], [value_label, "累计金额占比"],
                         loc="upper right", frameon=False, labelcolor=TEXT_PRIMARY, fontsize=8)
        _safe_tight_layout(self.figure)
        self.draw_idle()

    def draw_bar_chart(
        self,
        labels: list[str],
        values: list[float],
        title: str = "",
        ylabel: str = "",
        colors: list[str] | None = None,
        percent: bool = False,
    ) -> None:
        """Generic category bar chart used by the cross matrix view."""
        self.clear_chart()
        if not values or sum(abs(v) for v in values) <= 0:
            self._show_empty_state()
            return

        palette = colors or ABC_COLORS
        bar_colors = [palette[i % len(palette)] for i in range(len(values))]
        bars = self.axes.bar(labels, values, color=bar_colors, width=0.6)
        if title:
            self.axes.set_title(title, color=TEXT_PRIMARY, fontsize=11, pad=10)
        if ylabel:
            self.axes.set_ylabel(ylabel, color="#9CA8B5", fontsize=9)
        self.axes.grid(axis="y", alpha=0.15, color=GRID)
        self.axes.set_axisbelow(True)
        self.axes.tick_params(axis="x", labelsize=9)

        top = max(values) if values else 0.0
        for bar, value in zip(bars, values):
            text = f"{value:.1%}" if percent else (
                str(int(value)) if float(value).is_integer() else f"{value:.2f}"
            )
            self.axes.annotate(
                text,
                xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                xytext=(0, 4),
                textcoords="offset points",
                ha="center",
                va="bottom",
                color=TEXT_PRIMARY,
                fontsize=8,
            )

        if top > 0:
            self.axes.set_ylim(0, top * 1.18)
        _safe_tight_layout(self.figure)
        self.draw_idle()

    def draw_matrix_heatmap(
        self,
        row_labels: list[str],
        column_labels: list[str],
        matrix: list[list[float]],
        title: str = "ABC × XYZ 交叉矩阵",
        value_labels: list[list[str]] | None = None,
        selected_cell: tuple[int, int] | None = None,
    ) -> None:
        """Render an ABC x XYZ cross matrix as an annotated heatmap."""
        self.clear_chart()
        if not matrix or not matrix[0]:
            self._show_empty_state()
            return

        data = [[float(value) for value in row] for row in matrix]
        peak = max((max(row) for row in data), default=0.0)
        if peak <= 0:
            self._show_empty_state("矩阵暂无数据")
            return

        self.axes.imshow(
            data,
            cmap=MATRIX_CMAP,
            vmin=0,
            vmax=peak,
            aspect="auto",
        )
        self.axes.set_xticks(range(len(column_labels)))
        self.axes.set_xticklabels(column_labels, color=TEXT_PRIMARY, fontsize=10)
        self.axes.set_yticks(range(len(row_labels)))
        self.axes.set_yticklabels(row_labels, color=TEXT_PRIMARY, fontsize=10)
        self.axes.set_title(title, color=TEXT_PRIMARY, fontsize=11, pad=10)

        self.axes.set_xticks([x - 0.5 for x in range(1, len(column_labels))], minor=True)
        self.axes.set_yticks([y - 0.5 for y in range(1, len(row_labels))], minor=True)
        self.axes.grid(which="minor", color=BACKGROUND, linewidth=2)
        self.axes.tick_params(which="minor", bottom=False, left=False)

        threshold = peak * 0.55
        for r, row in enumerate(data):
            for c, value in enumerate(row):
                text = str(int(value)) if float(value).is_integer() else f"{value:.2f}"
                if value_labels is not None:
                    text = value_labels[r][c]
                self.axes.text(
                    c,
                    r,
                    text,
                    ha="center",
                    va="center",
                    color="#0B1116" if value >= threshold else TEXT_PRIMARY,
                    fontsize=11,
                    fontweight="bold",
                )

        if selected_cell is not None:
            selected_row, selected_column = selected_cell
            if 0 <= selected_row < len(data) and 0 <= selected_column < len(data[0]):
                self.axes.add_patch(
                    Rectangle(
                        (selected_column - 0.5, selected_row - 0.5),
                        1,
                        1,
                        fill=False,
                        edgecolor="#f0f6fc",
                        linewidth=2.4,
                    )
                )

        _safe_tight_layout(self.figure)
        self.draw_idle()
