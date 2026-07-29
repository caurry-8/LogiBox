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

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 30, 36, 30)
        layout.setSpacing(16)

        title = QLabel('数据中心')
        title.setObjectName('pageTitle')
        description = QLabel(
            '统一导入、查看、清空和导出数据。导入后的数据会与 ABC 分类模块实时共享。'
        )
        description.setObjectName('pageDescription')

        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        open_button = QPushButton('导入 Excel / CSV')
        open_button.clicked.connect(self.open_file)
        export_button = QPushButton('导出当前数据')
        export_button.clicked.connect(self.export_current)
        clear_button = QPushButton('清空数据')
        clear_button.clicked.connect(self.clear_data)

        self.file_label = QLabel('尚未加载文件')
        self.file_label.setObjectName('mutedLabel')
        self.stats_label = QLabel('0 行 × 0 列')
        self.stats_label.setObjectName('mutedLabel')

        toolbar.addWidget(open_button)
        toolbar.addWidget(export_button)
        toolbar.addWidget(clear_button)
        toolbar.addWidget(self.file_label)
        toolbar.addStretch()
        toolbar.addWidget(self.stats_label)

        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setDefaultSectionSize(30)
        self.table.horizontalHeader().setStretchLastSection(True)

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addLayout(toolbar)
        layout.addWidget(self.table, 1)

    def open_file(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            '选择数据文件',
            '',
            'Excel / CSV (*.xlsx *.xls *.csv)',
        )
        if not filename:
            return
        try:
            self.store.load(filename)
        except Exception as exc:
            QMessageBox.critical(self, '导入失败', str(exc))

    def clear_data(self) -> None:
        self.store.clear()

    def export_current(self) -> None:
        if not self.store.has_data():
            QMessageBox.information(self, '提示', '当前没有可导出的数据。')
            return

        filename, _ = QFileDialog.getSaveFileName(
            self,
            '导出当前数据',
            'LogiBox数据.xlsx',
            'Excel 文件 (*.xlsx);;CSV 文件 (*.csv)',
        )
        if not filename:
            return

        try:
            export_dataframe(self.store.dataframe(), filename)
            QMessageBox.information(self, '导出成功', f'数据已导出：\n{filename}')
        except Exception as exc:
            QMessageBox.critical(self, '导出失败', str(exc))

    def refresh_table(self) -> None:
        df = self.store.dataframe()
        self.table.setSortingEnabled(False)
        self.table.clear()

        if df is None:
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
            self.table.setSortingEnabled(True)
            self.file_label.setText('尚未加载文件')
            self.stats_label.setText('0 行 × 0 列')
            return

        self.table.setRowCount(len(df))
        self.table.setColumnCount(len(df.columns))
        self.table.setHorizontalHeaderLabels([str(column) for column in df.columns])

        for row in range(len(df)):
            for col in range(len(df.columns)):
                self.table.setItem(row, col, QTableWidgetItem(str(df.iat[row, col])))

        self.table.resizeColumnsToContents()
        self.table.setSortingEnabled(True)
        self.file_label.setText(Path(self.store.filename).name if self.store.filename else '未命名数据')
        self.stats_label.setText(f'{self.store.rows()} 行 × {self.store.cols()} 列')
