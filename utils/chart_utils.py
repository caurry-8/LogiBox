import matplotlib
from matplotlib import font_manager
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

def configure_chinese_font()->None:
    preferred=["Microsoft YaHei","SimHei","SimSun","Microsoft JhengHei","Noto Sans CJK SC","Source Han Sans CN"]
    installed={font.name for font in font_manager.fontManager.ttflist}
    for name in preferred:
        if name in installed:
            matplotlib.rcParams["font.sans-serif"]=[name]; break
    matplotlib.rcParams["axes.unicode_minus"]=False

configure_chinese_font()

class ChartCanvas(FigureCanvasQTAgg):
    def __init__(self)->None:
        self.figure=Figure(figsize=(5,3.2),dpi=100,facecolor="#161A1F")
        super().__init__(self.figure); self.axes=self.figure.add_subplot(111); self._apply_axes_theme()
    def _apply_axes_theme(self)->None:
        self.axes.set_facecolor("#1C2128"); self.axes.tick_params(colors="#B6C0CC",labelsize=9)
        for spine in self.axes.spines.values(): spine.set_color("#39414B")
    def clear_chart(self)->None:
        self.axes.clear(); self._apply_axes_theme()
    def draw_abc_pie(self,labels:list[str],values:list[int],title:str="ABC 分类数量占比")->None:
        self.clear_chart()
        if sum(values)<=0:
            self.axes.text(0.5,0.5,"暂无数据",ha="center",va="center",color="#B6C0CC",fontsize=12); self.axes.set_axis_off(); self.draw(); return
        self.axes.pie(values,labels=labels,autopct="%1.1f%%",startangle=90,colors=["#28C7FA","#6C7BFF","#A970FF"],textprops={"color":"#E8EDF3","fontsize":9},wedgeprops={"linewidth":1.2,"edgecolor":"#161A1F"})
        self.axes.set_title(title,color="#E8EDF3",fontsize=11,pad=10); self.draw()
    def draw_abc_bar(self,labels:list[str],values:list[int],title:str="ABC 分类 SKU 数量")->None:
        self.clear_chart(); colors=["#28C7FA","#6C7BFF","#A970FF"]
        bars=self.axes.bar(labels,values,color=colors,width=0.58)
        self.axes.set_title(title,color="#E8EDF3",fontsize=11,pad=10); self.axes.set_ylabel("SKU 数量",color="#9CA8B5",fontsize=9); self.axes.grid(axis="y",alpha=0.15,color="#AAB4C0")
        for bar,value in zip(bars,values): self.axes.text(bar.get_x()+bar.get_width()/2,bar.get_height(),str(value),ha="center",va="bottom",color="#E8EDF3",fontsize=9,padding=3)
        self.draw()
