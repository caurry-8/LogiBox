from typing import Callable
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame,QGridLayout,QHBoxLayout,QLabel,QVBoxLayout,QWidget
from widgets.metric_card import MetricCard

class FunctionCard(QFrame):
    clicked=Signal()
    def __init__(self,icon,title,description)->None:
        super().__init__(); self.setObjectName("functionCard"); self.setCursor(Qt.PointingHandCursor)
        layout=QVBoxLayout(self); layout.setContentsMargins(18,16,18,16); layout.setSpacing(7)
        icon_label=QLabel(icon); icon_label.setObjectName("cardIcon")
        title_label=QLabel(title); title_label.setObjectName("cardTitle")
        desc_label=QLabel(description); desc_label.setObjectName("cardDescription"); desc_label.setWordWrap(True)
        layout.addWidget(icon_label); layout.addWidget(title_label); layout.addWidget(desc_label)
    def mousePressEvent(self,event)->None:
        if event.button()==Qt.LeftButton: self.clicked.emit()
        super().mousePressEvent(event)

class HomePage(QWidget):
    def __init__(self,navigate:Callable[[int],None],store)->None:
        super().__init__(); self.navigate=navigate; self.store=store; self._build_ui(); self.store.data_changed.connect(self.refresh); self.refresh()
    def _build_ui(self)->None:
        layout=QVBoxLayout(self); layout.setContentsMargins(34,28,34,28); layout.setSpacing(20)
        header=QHBoxLayout(); left=QVBoxLayout(); left.setSpacing(2)
        title=QLabel("工作台"); title.setObjectName("pageTitle")
        subtitle=QLabel("物流工程数据驾驶舱 · LogiBox V3.2"); subtitle.setObjectName("pageDescription")
        left.addWidget(title); left.addWidget(subtitle); header.addLayout(left); header.addStretch()
        self.data_status=QLabel("● 未加载数据"); self.data_status.setObjectName("statusBadge"); header.addWidget(self.data_status); layout.addLayout(header)
        metrics=QGridLayout(); metrics.setHorizontalSpacing(16); metrics.setVerticalSpacing(16)
        self.sku_card=MetricCard("数据行数","--","#28C7FA","当前加载数据规模")
        self.column_card=MetricCard("字段数量","--","#6C7BFF","可用于分析的字段")
        self.missing_card=MetricCard("缺失单元格","--","#FFB86B","数据质量快速检查")
        self.duplicate_card=MetricCard("重复行","--","#FF6B8A","建议分析前先清洗")
        metrics.addWidget(self.sku_card,0,0); metrics.addWidget(self.column_card,0,1); metrics.addWidget(self.missing_card,0,2); metrics.addWidget(self.duplicate_card,0,3); layout.addLayout(metrics)
        section=QLabel("快速进入"); section.setObjectName("sectionTitle"); layout.addWidget(section)
        grid=QGridLayout(); grid.setHorizontalSpacing(16); grid.setVerticalSpacing(16)
        cards=[("◈","数据中心","导入、预览、导出与检查数据",1),("◎","EOQ 计算","经济订货批量与年度成本",2),("◇","ABC 分类","库存价值贡献与结构分析",3),("△","安全库存 / ROP","服务水平与再订货点",4)]
        for i,(icon,name,desc,index) in enumerate(cards):
            card=FunctionCard(icon,name,desc); card.clicked.connect(lambda idx=index:self.navigate(idx)); grid.addWidget(card,i//2,i%2)
        layout.addLayout(grid)
        footer=QFrame(); footer.setObjectName("dashboardNote"); footer_layout=QHBoxLayout(footer); footer_layout.setContentsMargins(16,12,16,12)
        self.file_label=QLabel("当前数据：未加载"); self.file_label.setObjectName("dashboardNoteText"); footer_layout.addWidget(self.file_label); footer_layout.addStretch(); footer_layout.addWidget(QLabel("LogiBox Analytics Engine")); layout.addWidget(footer); layout.addStretch()
    def refresh(self)->None:
        if not self.store.has_data():
            for card in [self.sku_card,self.column_card,self.missing_card,self.duplicate_card]: card.set_value("--")
            self.data_status.setText("● 未加载数据"); self.file_label.setText("当前数据：未加载"); return
        self.sku_card.set_value(str(self.store.rows())); self.column_card.set_value(str(self.store.cols())); self.missing_card.set_value(str(self.store.missing_cells())); self.duplicate_card.set_value(str(self.store.duplicate_rows())); self.data_status.setText("● 数据已就绪"); self.file_label.setText(f"当前数据：{self.store.filename_only()}")
