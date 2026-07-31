from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from utils.data_store import DataStore
from utils.excel_utils import export_dataframe


class ImportPage(QWidget):
    def __init__(self, store: DataStore) -> None:
        super().__init__()
        self.store = store
        self._build_ui()
        self.store.data_changed.connect(self.refresh_table)
        self.refresh_table()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(34, 28, 34, 22)
        layout.setSpacing(14)

        title = QLabel("数据中心")
        title.setObjectName("pageTitle")
        description = QLabel("统一管理数据源。支持 Excel / CSV 导入、预览、质量检查、示例数据与导出。")
        description.setObjectName("pageDescription")
        layout.addWidget(title)
        layout.addWidget(description)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        open_button = QPushButton("导入数据")
        open_button.clicked.connect(self.open_file)
        sample_button = QPushButton("加载示例数据")
        sample_button.setObjectName("secondaryButton")
        sample_button.clicked.connect(self.load_sample)
        export_button = QPushButton("导出当前数据")
        export_button.clicked.connect(self.export_current)
        clear_button = QPushButton("清空")
        clear_button.setObjectName("dangerButton")
        clear_button.clicked.connect(self.clear_data)
        self.file_label = QLabel("未加载文件")
        self.file_label.setObjectName("mutedLabel")
        self.stats_label = QLabel("0 行 × 0 列")
        self.stats_label.setObjectName("mutedLabel")
        toolbar.addWidget(open_button)
        toolbar.addWidget(sample_button)
        toolbar.addWidget(export_button)
        toolbar.addWidget(clear_button)
        toolbar.addSpacing(10)
        toolbar.addWidget(self.file_label)
        toolbar.addStretch()
        toolbar.addWidget(self.stats_label)
        layout.addLayout(toolbar)

        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.DoubleClicked)
        layout.addWidget(self.table, 1)

    def open_file(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "选择数据文件",
            "",
            "Excel / CSV (*.xlsx *.xls *.csv)",
        )
        if not filename:
            return
        try:
            self.store.load(filename)
        except Exception as exc:
            QMessageBox.critical(self, "导入失败", str(exc))

    def load_sample(self) -> None:
        sample_path = Path(__file__).resolve().parents[1] / "data" / "sample_inventory.csv"
        try:
            self.store.load(str(sample_path))
            QMessageBox.information(self, "加载成功", "已加载 LogiBox 示例库存数据。")
        except Exception as exc:
            QMessageBox.critical(self, "加载失败", str(exc))

    def clear_data(self) -> None:
        self.store.clear()

    def export_current(self) -> None:
        if not self.store.has_data():
            QMessageBox.information(self, "提示", "当前没有可导出的数据。")
            return
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "导出当前数据",
            "LogiBox数据.xlsx",
            "Excel 文件 (*.xlsx);;CSV 文件 (*.csv)",
        )
        if not filename:
            return
        try:
            export_dataframe(self.store.dataframe(), filename)
            QMessageBox.information(self, "导出成功", f"已导出：\n{filename}")
        except Exception as exc:
            QMessageBox.critical(self, "导出失败", str(exc))

    def refresh_table(self) -> None:
        df = self.store.dataframe()
        self.table.setSortingEnabled(False)
        self.table.clear()

        if df is None:
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
            self.table.setSortingEnabled(True)
            self.file_label.setText("未加载文件")
            self.stats_label.setText("0 行 × 0 列")
            return

        self.table.setRowCount(len(df))
        self.table.setColumnCount(len(df.columns))
        self.table.setHorizontalHeaderLabels([str(c) for c in df.columns])

        for r in range(len(df)):
            for c in range(len(df.columns)):
                self.table.setItem(r, c, QTableWidgetItem(str(df.iat[r, c])))

        self.table.resizeColumnsToContents()
        self.table.setSortingEnabled(True)
        self.file_label.setText(Path(self.store.filename).name if self.store.filename else "未加载文件")
        self.stats_label.setText(f"{self.store.rows()} 行 × {self.store.cols()} 列")
