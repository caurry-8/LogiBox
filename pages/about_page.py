from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from core.config import APP_CONFIG


class AboutPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(34, 28, 34, 22)
        layout.setSpacing(14)

        title = QLabel("关于 LogiBox")
        title.setObjectName("pageTitle")
        subtitle = QLabel(f"物流工程分析平台 · V{APP_CONFIG.version}")
        subtitle.setObjectName("pageDescription")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        panel = QFrame()
        panel.setObjectName("contentPanel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(22, 22, 22, 22)

        product = QLabel(f"LogiBox V{APP_CONFIG.version} · {APP_CONFIG.edition}")
        product.setObjectName("aboutProduct")
        panel_layout.addWidget(product)

        text = QLabel(
            "面向物流工程、仓储管理与库存分析场景的桌面分析工具。\n\n"
            "核心能力：数据中心、ABC 分类、XYZ 稳定性分析、ABC × XYZ 交叉矩阵、"
            "EOQ 经济订货、安全库存 / ROP、结果导出与 Word 报告生成。\n\n"
            "产品定位：让物流专业模型从课堂公式走向可复用的数据分析工作台。"
        )
        text.setObjectName("aboutText")
        text.setWordWrap(True)
        panel_layout.addWidget(text)
        layout.addWidget(panel)

        architecture = QLabel(
            "技术栈：Python · PySide6 · pandas · matplotlib · openpyxl · python-docx\n"
            "架构分层：界面 UI / 页面 Pages / 工具 Utils / 组件 Widgets / 数据 DataStore"
        )
        architecture.setObjectName("mutedLabel")
        layout.addWidget(architecture)
        layout.addStretch()
