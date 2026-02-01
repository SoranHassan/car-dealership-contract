import sys
import sqlite3
from PySide6.QtWidgets import (
    QApplication, QWidget, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem
)
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database", "contracts.db")


class SearchApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("جستجوی قراردادها")

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("نام یا نام خانوادگی")

        self.ncode_edit = QLineEdit()
        self.ncode_edit.setPlaceholderText("کد ملی")

        self.dealnum_edit = QLineEdit()
        self.dealnum_edit.setPlaceholderText("شماره قرارداد")

        self.search_btn = QPushButton("جستجو")
        self.open_btn = QPushButton("باز کردن قرارداد انتخاب‌شده")

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["نام", "کد ملی", "شماره قرارداد", "مسیر فایل"])

        top_layout = QHBoxLayout()
        top_layout.addWidget(self.name_edit)
        top_layout.addWidget(self.ncode_edit)
        top_layout.addWidget(self.dealnum_edit)
        top_layout.addWidget(self.search_btn)

        layout = QVBoxLayout(self)
        layout.addLayout(top_layout)
        layout.addWidget(self.table)
        layout.addWidget(self.open_btn)

        self.search_btn.clicked.connect(self.search)
        self.open_btn.clicked.connect(self.open_selected)

    def search(self):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        name = self.name_edit.text().strip()
        ncode = self.ncode_edit.text().strip()
        dealnum = self.dealnum_edit.text().strip()

        query = "SELECT buyer_json, buyer_id, contract_number, file_path FROM contracts WHERE 1=1"
        params = []

        if name:
            query += " AND buyer_json LIKE ?"
            params.append(f"%{name}%")

        if ncode:
            query += " AND buyer_id = ?"
            params.append(ncode)

        if dealnum:
            query += " AND contract_number = ?"
            params.append(dealnum)

        cur.execute(query, params)
        rows = cur.fetchall()
        conn.close()

        self.table.setRowCount(len(rows))
        for row_idx, (buyer_json, buyer_id, contract_number, file_path) in enumerate(rows):
            # اگر خواستی می‌تونی از json فقط name رو دربیاری، فعلاً ساده:
            self.table.setItem(row_idx, 0, QTableWidgetItem(buyer_json))
            self.table.setItem(row_idx, 1, QTableWidgetItem(str(buyer_id)))
            self.table.setItem(row_idx, 2, QTableWidgetItem(str(contract_number)))
            self.table.setItem(row_idx, 3, QTableWidgetItem(file_path))

    def open_selected(self):
        row = self.table.currentRow()
        if row < 0:
            return
        file_path = self.table.item(row, 3).text()
        if file_path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = SearchApp()
    w.show()
    sys.exit(app.exec())