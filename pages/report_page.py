from PySide6.QtWidgets import QFileDialog, QGridLayout, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget

from utils.data_store import DataStore
from utils.report_utils import generate_word_report
from widgets.metric_card import MetricCard


class ReportPage(QWidget):
    def __init__(self, store: DataStore) -> None:
        super().__init__()
        self.store = store
        self._build_ui()
        self.store.data_changed.connect(self.refresh)
        self.store.analysis_changed.connect(self.refresh)
        self.store.status_changed.connect(self.refresh)
        self.refresh()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(34, 28, 34, 22)
        root.setSpacing(14)

        title = QLabel("报告中心")
        title.setObjectName("pageTitle")
        desc = QLabel("汇总 LogiBox 当前数据与分析结果，一键生成可提交、可归档的 Word 分析报告。")
        desc.setObjectName("pageDescription")
        root.addWidget(title)
        root.addWidget(desc)

        cards = QGridLayout()
        self.data_card = MetricCard("数据源", "--", "#28C7FA", "当前数据文件")
        self.abc_card = MetricCard("ABC 分析", "未完成", "#6C7BFF", "价值贡献分析")
        self.xyz_card = MetricCard("XYZ 分析", "未完成", "#A970FF", "需求稳定性分析")
        self.model_card = MetricCard("模型计算", "0 / 2", "#64D8CB", "EOQ + 安全库存")
        cards.addWidget(self.data_card, 0, 0)
        cards.addWidget(self.abc_card, 0, 1)
        cards.addWidget(self.xyz_card, 0, 2)
        cards.addWidget(self.model_card, 0, 3)
        root.addLayout(cards)

        actions = QHBoxLayout()
        generate_button = QPushButton("生成 Word 分析报告")
        generate_button.clicked.connect(self.generate_report)
        refresh_button = QPushButton("刷新状态")
        refresh_button.setObjectName("secondaryButton")
        refresh_button.clicked.connect(self.refresh)
        actions.addWidget(generate_button)
        actions.addWidget(refresh_button)
        actions.addStretch()
        root.addLayout(actions)

        self.status = QLabel("报告中心已就绪")
        self.status.setObjectName("statusBadge")
        root.addWidget(self.status)
        root.addStretch()

    def refresh(self, *_args) -> None:
        if self.store.has_data():
            self.data_card.set_value(self.store.filename_only())
        else:
            self.data_card.set_value("未加载")

        abc = self.store.get_analysis("abc")
        xyz = self.store.get_analysis("xyz")
        self.abc_card.set_value("已完成" if abc else "未完成")
        self.xyz_card.set_value("已完成" if xyz else "未完成")
        model_count = int(self.store.has_analysis("eoq")) + int(self.store.has_analysis("safety"))
        self.model_card.set_value(f"{model_count} / 2")

    def generate_report(self) -> None:
        if not self.store.has_data():
            QMessageBox.information(self, "提示", "请先在数据中心加载数据。")
            return
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "生成 Word 分析报告",
            "LogiBox_V3.2_分析报告.docx",
            "Word 文档 (*.docx)",
        )
        if not filename:
            return
        try:
            output = generate_word_report(filename, self.store)
            self.status.setText("报告生成完成")
            QMessageBox.information(self, "生成成功", f"报告已保存：\n{output}")
        except Exception as exc:
            self.status.setText("报告生成失败")
            QMessageBox.critical(self, "生成失败", str(exc))
