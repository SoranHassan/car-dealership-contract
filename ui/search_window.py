# ui/search_window.py
import json
import sys
import sqlite3
import os
import time
from PySide6.QtWidgets import (
    QMessageBox, QVBoxLayout, QWidget, QLineEdit, QApplication,
    QPushButton, QTableWidget, QTableWidgetItem, QHBoxLayout, QComboBox, QHeaderView, QLabel
)
from PySide6.QtGui import QDesktopServices, QColor
from PySide6.QtCore import QUrl, Qt, QTimer, QThread, Signal

from word.generator import ContractGenerator


if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(__file__))

DB_PATH = os.path.join(BASE_DIR, "settings.db")


class SearchThread(QThread):
    results_ready = Signal(list)
    
    def __init__(self, db, name="", ncode="", dealnum=""):
        super().__init__()
        self.db = db
        self.name = name
        self.ncode = ncode
        self.dealnum = dealnum
    
    def run(self):
        results = self.db.search_contracts(self.name, self.ncode, self.dealnum)
        self.results_ready.emit(results)


class SearchApp(QWidget):
    def __init__(self, db):
        self.db = db
        super().__init__()
        self.setWindowTitle("جستجوی قراردادها")
        self.setMinimumWidth(950)
        self.setMinimumHeight(500)

        self.changed_rows = {}
        self.search_thread = None
        self.is_loading = False

        self.setStyleSheet("""
            QWidget { font-family: Aria, Pelak; font-size: 11pt; }
            QLineEdit { padding: 6px; border: 1px solid #aaa; border-radius: 6px; background: #fafafa; font-size: 11pt; }
            QPushButton { padding: 8px 14px; border-radius: 6px; font-weight: bold; font-size:11pt;}
            QPushButton:disabled { background-color: #cccccc; }
            QTableWidget { border: 1px solid #ccc; background: white; font-size: 11pt; }
            QHeaderView::section { background-color: #f0f0f0; padding: 6px; border: 1px solid #dcdcdc; font-weight: bold; font-size: 11pt; }
        """)

        # فیلدهای جستجو
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("نام یا نام خانوادگی خریدار/فروشنده")
        self.name_edit.setMinimumWidth(200)

        self.ncode_edit = QLineEdit()
        self.ncode_edit.setPlaceholderText("کد ملی خریدار/فروشنده")
        self.ncode_edit.setMinimumWidth(150)

        self.dealnum_edit = QLineEdit()
        self.dealnum_edit.setPlaceholderText("شماره قرارداد")
        self.dealnum_edit.setMinimumWidth(150)

        # دکمه‌ها
        self.search_btn = QPushButton("🔍 جستجو")
        self.search_btn.setStyleSheet("background-color: #1C4D8D; color: white;")
        self.search_btn.setMinimumWidth(100)

        self.show_all_btn = QPushButton("📋 نمایش همه")
        self.show_all_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        self.show_all_btn.setMinimumWidth(100)

        self.open_btn = QPushButton("📄 باز کردن قرارداد")
        self.open_btn.setStyleSheet("background-color: #1C4D8D; color: white;")

        self.delete_btn = QPushButton("🗑️ حذف")
        self.delete_btn.setStyleSheet("background-color: #C3110C; color: white;")

        self.loading_label = QLabel("")
        self.loading_label.setStyleSheet("color: #1C4D8D; font-size: 10pt;")
        self.loading_label.hide()

        # جدول
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "وضعیت پرداخت", "شماره قرارداد", "فروشنده", "خریدار"
        ])

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 140)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)

        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)

        # چیدمان
        top_layout = QHBoxLayout()
        top_layout.addWidget(self.name_edit)
        top_layout.addWidget(self.ncode_edit)
        top_layout.addWidget(self.dealnum_edit)
        top_layout.addWidget(self.search_btn)
        top_layout.addWidget(self.show_all_btn)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.open_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.loading_label)

        layout = QVBoxLayout(self)
        layout.addLayout(top_layout)
        layout.addWidget(self.table)
        layout.addLayout(btn_layout)

        # اتصال‌ها
        self.search_btn.clicked.connect(self.search_async)
        self.show_all_btn.clicked.connect(self.show_all_contracts)
        self.name_edit.returnPressed.connect(self.search_async)
        self.ncode_edit.returnPressed.connect(self.search_async)
        self.dealnum_edit.returnPressed.connect(self.search_async)
        self.open_btn.clicked.connect(self.open_selected)
        self.delete_btn.clicked.connect(self.delete_selected)

        # تاخیر در جستجو هنگام تایپ (Debounce)
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.search_async)
        
        self.name_edit.textChanged.connect(self.on_text_changed)
        self.ncode_edit.textChanged.connect(self.on_text_changed)
        self.dealnum_edit.textChanged.connect(self.on_text_changed)

        # ========== بارگذاری همه قراردادها هنگام باز شدن ==========
        self.show_all_contracts()

    def on_text_changed(self):
        self.search_timer.start(500)

    def show_all_contracts(self):
        """نمایش همه قراردادها (بدون فیلتر)"""
        self.name_edit.clear()
        self.ncode_edit.clear()
        self.dealnum_edit.clear()
        self.search_async()

    def search_async(self):
        if self.is_loading:
            return
        
        self.is_loading = True
        self.search_btn.setEnabled(False)
        self.show_all_btn.setEnabled(False)
        self.loading_label.setText("⏳ در حال جستجو...")
        self.loading_label.show()
        
        name = self.name_edit.text().strip()
        ncode = self.ncode_edit.text().strip()
        dealnum = self.dealnum_edit.text().strip()
        
        self.search_thread = SearchThread(self.db, name, ncode, dealnum)
        self.search_thread.results_ready.connect(self.on_search_complete)
        self.search_thread.start()

    def on_search_complete(self, rows):
        self.changed_rows.clear()
        self.table.setRowCount(len(rows))

        for row_idx, row in enumerate(rows):
            buyer_json = row.get('buyer_json', '{}')
            seller_json = row.get('seller_json', '{}')
            contract_number = row.get('contract_number', '')
            file_path = row.get('file_path', '')
            is_payed = row.get('is_payed', 0)

            try:
                buyer = json.loads(buyer_json) if buyer_json else {}
                seller = json.loads(seller_json) if seller_json else {}
            except:
                buyer = {}
                seller = {}

            buyer_name = f"{buyer.get('name', '')} {buyer.get('lname', '')}"
            seller_name = f"{seller.get('name', '')} {seller.get('lname', '')}"

            # کامبوباکس وضعیت پرداخت
            combo = QComboBox()
            combo.addItems(["پرداخت نشده", "پرداخت شده"])
            
            if is_payed is None:
                combo.setCurrentIndex(0)
                combo.setEnabled(True)
                color = QColor("#e0e0e0")
            else:
                current_index = 1 if is_payed == 1 else 0
                combo.setCurrentIndex(current_index)
                combo.currentIndexChanged.connect(
                    lambda _, cn=contract_number, c=combo: self.on_pay_changed(cn, c)
                )
                color = QColor("#c8e6c9") if is_payed == 1 else QColor("#ffcdd2")

            self.table.setCellWidget(row_idx, 0, combo)

            # شماره قرارداد
            cn_item = QTableWidgetItem(str(contract_number))
            cn_item.setData(Qt.UserRole, file_path)
            cn_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 1, cn_item)

            # فروشنده و خریدار
            seller_item = QTableWidgetItem(seller_name)
            seller_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row_idx, 2, seller_item)

            buyer_item = QTableWidgetItem(buyer_name)
            buyer_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row_idx, 3, buyer_item)

            # رنگ‌بندی ردیف
            for col in range(1, 4):
                item = self.table.item(row_idx, col)
                if item:
                    item.setBackground(color)

        self.is_loading = False
        self.search_btn.setEnabled(True)
        self.show_all_btn.setEnabled(True)
        self.loading_label.hide()

    def on_pay_changed(self, contract_number, combo):
        new_value = 1 if combo.currentIndex() == 1 else 0
        success = self.db.update_contract_payment(contract_number, new_value)
        
        if success:
            color = QColor("#c8e6c9") if new_value == 1 else QColor("#ffcdd2")
            for row in range(self.table.rowCount()):
                cn_item = self.table.item(row, 1)
                if cn_item and cn_item.text() == str(contract_number):
                    for col in range(1, 4):
                        item = self.table.item(row, col)
                        if item:
                            item.setBackground(color)
                    break
        else:
            old_value = 0 if new_value == 1 else 1
            combo.setCurrentIndex(old_value)
            QMessageBox.warning(self, "خطا", "تغییر وضعیت پرداخت انجام نشد.")

    def open_selected(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "خطا", "لطفاً یک قرارداد را انتخاب کنید.")
            return

        cn_item = self.table.item(row, 1)
        if not cn_item:
            return

        file_path = cn_item.data(Qt.UserRole)
        if file_path and os.path.exists(file_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
        else:
            QMessageBox.warning(self, "خطا", "فایل قرارداد یافت نشد.")

    def delete_selected(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "خطا", "لطفاً یک قرارداد را انتخاب کنید.")
            return

        cn_item = self.table.item(row, 1)
        if not cn_item:
            return

        contract_number = cn_item.text()

        confirm = QMessageBox.question(
            self,
            "تأیید حذف",
            f"آیا از حذف قرارداد شماره {contract_number} مطمئن هستید؟",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm != QMessageBox.Yes:
            return

        if self.db.delete_contract(int(contract_number)):
            QMessageBox.information(self, "حذف شد", "قرارداد با موفقیت حذف شد.")
            self.show_all_contracts()
        else:
            QMessageBox.critical(self, "خطا", "در حذف قرارداد مشکلی رخ داد.")

    def closeEvent(self, event):
        if self.search_thread and self.search_thread.isRunning():
            self.search_thread.quit()
            self.search_thread.wait(1000)
        event.accept()

    def refresh(self):
        """رفرش لیست (پاک کردن کش و بارگذاری مجدد)"""
        # پاک کردن کش دیتابیس
        self.db._clear_cache()
        # بارگذاری مجدد همه قراردادها
        self.show_all_contracts()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    from database.db import DatabaseManager
    db = DatabaseManager()
    w = SearchApp(db)
    w.show()
    sys.exit(app.exec())