from pathlib import Path
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget
)
from utils.excel_utils import ExcelManager

class ImportPage(QWidget):
    def __init__(self):
        super().__init__()
        self.manager = ExcelManager()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 30, 36, 30)
        layout.setSpacing(16)

        title = QLabel("数据中心")
        title.setObjectName("pageTitle")
        description = QLabel("导入 Excel / CSV 数据，并在软件中进行预览。")
        description.setObjectName("pageDescription")

        toolbar = QHBoxLayout()
        button = QPushButton("导入 Excel / CSV")
        button.clicked.connect(self.open_file)
        self.file_label = QLabel("尚未加载文件")
        self.file_label.setObjectName("mutedLabel")
        toolbar.addWidget(button)
        toolbar.addWidget(self.file_label)
        toolbar.addStretch()

        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addLayout(toolbar)
        layout.addWidget(self.table, 1)

    def open_file(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "选择数据文件", "",
            "Excel / CSV (*.xlsx *.xls *.csv)"
        )
        if not filename:
            return
        try:
            self.manager.load(filename)
            self.refresh_table()
            p = Path(filename)
            self.file_label.setText(
                f"{p.name} · {self.manager.rows()} 行 × {self.manager.cols()} 列"
            )
        except Exception as exc:
            QMessageBox.critical(self, "导入失败", str(exc))

    def refresh_table(self):
        df = self.manager.dataframe()
        if df is None:
            return
        self.table.clear()
        self.table.setRowCount(len(df))
        self.table.setColumnCount(len(df.columns))
        self.table.setHorizontalHeaderLabels([str(c) for c in df.columns])
        for r in range(len(df)):
            for c in range(len(df.columns)):
                self.table.setItem(r, c, QTableWidgetItem(str(df.iat[r, c])))
        self.table.resizeColumnsToContents()
