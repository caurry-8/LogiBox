from __future__ import annotations

from matplotlib import font_manager, rcParams
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg


# 自动选择 Windows / 常见中文字体，避免 matplotlib 中文显示为方框。
def _pick_chinese_font() -> str:
    preferred = [
        'Microsoft YaHei',
        'SimHei',
        'SimSun',
        'Microsoft JhengHei',
        'Noto Sans CJK SC',
        'Source Han Sans CN',
    ]

    installed = {
        getattr(item, 'name', '')
        for item in font_manager.fontManager.ttflist
    }

    for name in preferred:
        if name in installed:
            return name

    return 'DejaVu Sans'


CHINESE_FONT = _pick_chinese_font()
rcParams['font.sans-serif'] = [CHINESE_FONT, 'Microsoft YaHei', 'SimHei', 'DejaVu Sans']
rcParams['axes.unicode_minus'] = False


class ChartCanvas(FigureCanvasQTAgg):
    def __init__(self) -> None:
        self.figure = Figure(
            figsize=(6, 4),
            dpi=100,
            facecolor='#21252A',
        )
        super().__init__(self.figure)
        self.axes = self.figure.add_subplot(111)
        self._setup_axes()

    def _setup_axes(self) -> None:
        self.axes.set_facecolor('#191C20')
        self.axes.tick_params(colors='#D9DEE5', labelsize=9)
        for spine in self.axes.spines.values():
            spine.set_color('#3A414A')

    def clear_chart(self) -> None:
        self.figure.clear()
        self.axes = self.figure.add_subplot(111)
        self._setup_axes()

    def plot_pie(
        self,
        labels: list[str],
        values: list[int],
        title: str = 'ABC 分类占比',
    ) -> None:
        self.clear_chart()

        colors = ['#4CAF50', '#2196F3', '#FFC107']
        safe_values = [max(0, int(value)) for value in values]

        if sum(safe_values) == 0:
            self.axes.text(
                0.5, 0.5, '暂无可用数据',
                transform=self.axes.transAxes,
                ha='center', va='center',
                color='#B9C2CC', fontsize=14,
            )
            self.axes.set_axis_off()
        else:
            wedges, _, autotexts = self.axes.pie(
                safe_values,
                labels=labels,
                autopct='%1.1f%%',
                startangle=90,
                colors=colors[:len(labels)],
                radius=0.78,
                pctdistance=0.68,
                labeldistance=1.04,
                wedgeprops={'linewidth': 1.2, 'edgecolor': '#191C20'},
                textprops={'color': '#F2F4F7', 'fontsize': 10},
            )
            for autotext in autotexts:
                autotext.set_color('#FFFFFF')
                autotext.set_fontsize(10)
                autotext.set_fontweight('bold')

            self.axes.set_title(
                title,
                color='#F5F7FA',
                fontsize=13,
                pad=12,
            )

        self.figure.tight_layout(pad=1.2)
        self.draw_idle()

    def plot_bar(
        self,
        labels: list[str],
        values: list[int],
        title: str = 'ABC 数量统计',
    ) -> None:
        self.clear_chart()

        colors = ['#4CAF50', '#2196F3', '#FFC107']
        bars = self.axes.bar(
            labels,
            values,
            width=0.55,
            color=colors[:len(labels)],
        )

        self.axes.set_title(
            title,
            color='#F5F7FA',
            fontsize=13,
            pad=12,
        )
        self.axes.set_ylabel(
            'SKU 数量',
            color='#D9DEE5',
        )
        self.axes.grid(
            axis='y',
            color='#3A414A',
            alpha=0.45,
            linestyle='--',
        )
        self.axes.set_axisbelow(True)

        for bar, value in zip(bars, values):
            self.axes.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                str(value),
                ha='center',
                va='bottom',
                color='#F5F7FA',
                fontsize=10,
                fontweight='bold',
                clip_on=False,
            )

        self.figure.tight_layout(pad=1.2)
        self.draw_idle()
