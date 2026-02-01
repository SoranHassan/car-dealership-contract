import sys
import sqlite3
import json
from PySide6.QtWidgets import (
    QApplication, QWidget, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem
)
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl
import os

# مسیر صحیح دیتابیس در روت پروژه
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR)
DB_PATH = os.path.join(BASE_DIR, "settings.db")


class SearchApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("جستجوی قراردادها")
        self.setMinimumWidth(750)

        # استایل کلی
        self.setStyleSheet("""
            QWidget {
                font-family: Vazirmatn, Arial;
                font-size: 14px;
            }

            QLineEdit {
                padding: 6px;
                border: 1px solid #aaa;
                border-radius: 6px;
                background: #fafafa;
            }

            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 14px;
                border-radius: 6px;
                font-weight: bold;
            }

            QPushButton:hover {
                background-color: #43a047;
            }

            QTableWidget {
                border: 1px solid #ccc;
                gridline-color: #bbb;
                selection-background-color: #0078d7;
                selection-color: white;
                background: white;
            }

            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 6px;
                border: 1px solid #dcdcdc;
                font-weight: bold;
            }
        """)

        # فیلدهای ورودی
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("نام یا نام خانوادگی")

        self.ncode_edit = QLineEdit()
        self.ncode_edit.setPlaceholderText("کد ملی")

        self.dealnum_edit = QLineEdit()
        self.dealnum_edit.setPlaceholderText("شماره قرارداد")

        # دکمه‌ها
        self.search_btn = QPushButton("جستجو")
        self.open_btn = QPushButton("باز کردن قرارداد")

        # جدول
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["خریدار", "فروشنده", "شماره قرارداد"])

        # تنظیم سایز سلول‌ها
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setDefaultSectionSize(220)
        self.table.verticalHeader().setDefaultSectionSize(34)

        # چیدمان
        top_layout = QHBoxLayout()
        top_layout.addWidget(self.name_edit)
        top_layout.addWidget(self.ncode_edit)
        top_layout.addWidget(self.dealnum_edit)
        top_layout.addWidget(self.search_btn)

        layout = QVBoxLayout(self)
        layout.addLayout(top_layout)
        layout.addWidget(self.table)
        layout.addWidget(self.open_btn)

        # اتصال‌ها
        self.search_btn.clicked.connect(self.search)
        self.name_edit.textChanged.connect(self.search)
        self.ncode_edit.textChanged.connect(self.search)
        self.dealnum_edit.textChanged.connect(self.search)
        self.open_btn.clicked.connect(self.open_selected)

        # اولین بار همه را نمایش بده
        self.search()

    def search(self):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        name = self.name_edit.text().strip()
        ncode = self.ncode_edit.text().strip()
        dealnum = self.dealnum_edit.text().strip()

        query = """
            SELECT buyer_json, seller_json, buyer_id, contract_number, file_path
            FROM contracts
            WHERE 1=1
        """
        params = []

        if name:
            query += " AND (buyer_json LIKE ? OR seller_json LIKE ?)"
            params.append(f"%{name}%")
            params.append(f"%{name}%")

        if ncode:
            query += " AND buyer_id LIKE ?"
            params.append(f"%{ncode}%")

        if dealnum:
            query += " AND contract_number LIKE ?"
            params.append(f"%{dealnum}%")

        cur.execute(query, params)
        rows = cur.fetchall()
        conn.close()

        self.table.setRowCount(len(rows))

        for row_idx, (buyer_json, seller_json, buyer_id, contract_number, file_path) in enumerate(rows):

            # تبدیل JSON به dict
            buyer = json.loads(buyer_json)
            seller = json.loads(seller_json)

            buyer_name = f"{buyer['name']} {buyer['lname']}"
            seller_name = f"{seller['name']} {seller['lname']}"

            # نمایش فقط نام‌ها و شماره قرارداد
            self.table.setItem(row_idx, 0, QTableWidgetItem(buyer_name))
            self.table.setItem(row_idx, 1, QTableWidgetItem(seller_name))
            self.table.setItem(row_idx, 2, QTableWidgetItem(str(contract_number)))

    def open_selected(self):
        row = self.table.currentRow()
        if row < 0:
            return

        # ستون مسیر فایل دیگر در جدول نیست → باید دوباره از دیتابیس بخوانیم
        contract_number = self.table.item(row, 2).text()

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT file_path FROM contracts WHERE contract_number = ?", (contract_number,))
        result = cur.fetchone()
        conn.close()

        if result:
            file_path = result[0]
            if file_path:
                QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = SearchApp()
    w.show()
    sys.exit(app.exec())