import json
import sys, sqlite3, os
from PySide6.QtWidgets import (
    QMessageBox, QVBoxLayout, QWidget, QLineEdit, QApplication,
    QPushButton, QTableWidget, QTableWidgetItem, QHBoxLayout, QComboBox, QHeaderView
)
from PySide6.QtGui import QDesktopServices, QColor
from PySide6.QtCore import QUrl, Qt

from word.generator import ContractGenerator  # مسیر را با پروژه‌ات تنظیم کن


if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(__file__))

DB_PATH = os.path.join(BASE_DIR, "settings.db")


class SearchApp(QWidget):
    def __init__(self, db):
        self.db = db
        super().__init__()
        self.setWindowTitle("جستجوی قراردادها")
        self.setMinimumWidth(900)

        self.changed_rows = {}  # contract_number -> new_is_payed

        self.setStyleSheet("""
            QWidget { font-family: Aria, Pelak; font-size: 11pt; }
            QLineEdit { padding: 6px; border: 1px solid #aaa; border-radius: 6px; background: #fafafa; font-size: 11pt; }
            QPushButton { padding: 8px 14px; border-radius: 6px; font-weight: bold; font-size:11pt;}
            QTableWidget { border: 1px solid #ccc; background: white; font-size: 11pt; }
            QHeaderView::section { background-color: #f0f0f0; padding: 6px; border: 1px solid #dcdcdc; font-weight: bold; font-size: 11pt; }
        """)

        # فیلدهای جستجو
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("نام یا نام خانوادگی خریدار/فروشنده")

        self.ncode_edit = QLineEdit()
        self.ncode_edit.setPlaceholderText("کد ملی خریدار/فروشنده")

        self.dealnum_edit = QLineEdit()
        self.dealnum_edit.setPlaceholderText("شماره قرارداد")

        # دکمه‌ها
        self.search_btn = QPushButton("جستجو")
        self.search_btn.setStyleSheet("background-color: #1C4D8D; color: white;")

        self.open_btn = QPushButton("باز کردن قرارداد")
        self.open_btn.setStyleSheet("background-color: #1C4D8D; color: white;")

        self.delete_btn = QPushButton("حذف")
        self.delete_btn.setStyleSheet("background-color: #C3110C; color: white;")

        self.save_changes_btn = QPushButton("ذخیره تغییرات وضعیت پرداخت")
        self.save_changes_btn.setStyleSheet("background-color: #4CAF50; color: white;")

        # جدول
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "وضعیت پرداخت", "شماره قرارداد", "فروشنده", "خریدار"
        ])

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        self.table.setColumnWidth(0, 130)

        self.table.verticalHeader().setDefaultSectionSize(34)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setDefaultAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # چیدمان
        top_layout = QHBoxLayout()
        top_layout.addWidget(self.name_edit)
        top_layout.addWidget(self.ncode_edit)
        top_layout.addWidget(self.dealnum_edit)
        top_layout.addWidget(self.search_btn)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.open_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.save_changes_btn)
        btn_layout.addStretch()

        layout = QVBoxLayout(self)
        layout.addLayout(top_layout)
        layout.addWidget(self.table)
        layout.addLayout(btn_layout)

        # اتصال‌ها
        self.search_btn.clicked.connect(self.search)
        self.name_edit.textChanged.connect(self.search)
        self.ncode_edit.textChanged.connect(self.search)
        self.dealnum_edit.textChanged.connect(self.search)
        self.open_btn.clicked.connect(self.open_selected)
        self.delete_btn.clicked.connect(self.delete_selected)
        self.save_changes_btn.clicked.connect(self.save_changes)

        self.search()

    # ---------------- جستجو ----------------
    def search(self):
        self.changed_rows.clear()

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        name = self.name_edit.text().strip()
        ncode = self.ncode_edit.text().strip()
        dealnum = self.dealnum_edit.text().strip()

        query = """
            SELECT buyer_json, seller_json, buyer_id, seller_id, contract_number,
                   file_path, is_payed, car_json, deal_json, checkpoint_image
            FROM contracts
            WHERE 1=1
        """
        params = []

        if name:
            query += " AND (buyer_json LIKE ? OR seller_json LIKE ?)"
            params.append(f"%{name}%")
            params.append(f"%{name}%")

        if ncode:
            query += " AND (buyer_id LIKE ? OR seller_id LIKE ?)"
            params.append(f"%{ncode}%")
            params.append(f"%{ncode}%")

        if dealnum:
            query += " AND contract_number LIKE ?"
            params.append(f"%{dealnum}%")

        cur.execute(query, params)
        rows = cur.fetchall()
        conn.close()

        self.table.setRowCount(len(rows))

        for row_idx, (buyer_json, seller_json, buyer_id, seller_id, contract_number,
                      file_path, is_payed, car_json, deal_json, checkpoint_image) in enumerate(rows):

            buyer = json.loads(buyer_json)
            seller = json.loads(seller_json)

            buyer_name = f"{buyer['name']} {buyer['lname']}"
            seller_name = f"{seller['name']} {seller['lname']}"

            # وضعیت پرداخت
            combo = QComboBox()
            combo.addItems(["پرداخت نشده", "پرداخت شده"])

            if is_payed is None:
                combo.setCurrentIndex(1)
                combo.setEnabled(False)
                color = QColor("#b6ffb3")
            else:
                combo.setCurrentIndex(1 if is_payed == 1 else 0)
                combo.currentIndexChanged.connect(
                    lambda _, cn=contract_number: self.on_pay_changed(cn)
                )
                color = QColor("#b6ffb3") if is_payed == 1 else QColor("#ffb3b3")

            self.table.setCellWidget(row_idx, 0, combo)

            # شماره قرارداد
            cn_item = QTableWidgetItem(str(contract_number))
            cn_item.setData(Qt.UserRole, file_path)
            cn_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row_idx, 1, cn_item)

            # فروشنده
            seller_item = QTableWidgetItem(seller_name)
            seller_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row_idx, 2, seller_item)

            # خریدار
            buyer_item = QTableWidgetItem(buyer_name)
            buyer_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row_idx, 3, buyer_item)

            # رنگ‌بندی
            for col in range(1, 4):
                item = self.table.item(row_idx, col)
                if item:
                    item.setBackground(color)

    # ---------------- تغییر وضعیت پرداخت ----------------
    def on_pay_changed(self, contract_number):
        rows = self.table.rowCount()
        for row in range(rows):
            cn_item = self.table.item(row, 1)
            if cn_item and cn_item.text() == str(contract_number):
                combo = self.table.cellWidget(row, 0)
                new_value = 1 if combo.currentIndex() == 1 else 0

                # پاک کردن مقدار قبلی
                if contract_number in self.changed_rows:
                    del self.changed_rows[contract_number]

                # ثبت مقدار جدید
                self.changed_rows[contract_number] = new_value

                # رنگ‌بندی
                color = QColor("#b6ffb3") if new_value == 1 else QColor("#ffb3b3")
                for col in range(1, 4):
                    item = self.table.item(row, col)
                    if item:
                        item.setBackground(color)
                break

    # ---------------- ذخیره تغییرات ----------------
    def save_changes(self):
        if not self.changed_rows:
            QMessageBox.information(self, "تغییری نیست", "هیچ وضعیتی تغییر داده نشده است.")
            return

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        for contract_number, new_is_payed in self.changed_rows.items():
            cur.execute(
                "UPDATE contracts SET is_payed=? WHERE contract_number=?",
                (new_is_payed, contract_number)
            )

            # خواندن داده‌ها برای ساخت Word
            cur.execute("""
                SELECT seller_json, buyer_json, car_json, deal_json,
                       file_path, checkpoint_image
                FROM contracts
                WHERE contract_number=?
            """, (contract_number,))
            row = cur.fetchone()
            if not row:
                continue

            seller_json, buyer_json, car_json, deal_json, file_path, checkpoint_image = row

            seller = json.loads(seller_json)
            buyer = json.loads(buyer_json)
            car = json.loads(car_json)
            deal = json.loads(deal_json)

            deal["is_payed"] = new_is_payed

            data = {
                "seller": seller,
                "buyer": buyer,
                "car_deal": car,
                "deal_info": deal
            }

            # ذخیره JSON موقت
            temp_json = os.path.join(BASE_DIR, "temp_update.json")
            with open(temp_json, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)

            # ساخت Word
            generator = ContractGenerator()
            output_dir = os.path.dirname(file_path)
            generator.generate(temp_json, checkpoint_image, output_dir)

        conn.commit()
        conn.close()

        self.changed_rows.clear()
        QMessageBox.information(self, "ذخیره شد", "تغییرات وضعیت پرداخت ذخیره و قراردادها دوباره ساخته شدند.")

    # ---------------- باز کردن ----------------
    def open_selected(self):
        row = self.table.currentRow()
        if row < 0:
            return

        cn_item = self.table.item(row, 1)
        if not cn_item:
            return

        contract_number = cn_item.text()

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT file_path FROM contracts WHERE contract_number=?", (contract_number,))
        result = cur.fetchone()
        conn.close()

        if result:
            file_path = result[0]
            if file_path:
                QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))

    # ---------------- حذف ----------------
    def delete_selected(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "خطا", "لطفاً یک ردیف را انتخاب کنید.")
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

        try:
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("DELETE FROM contracts WHERE contract_number=?", (contract_number,))
                conn.commit()

            QMessageBox.information(self, "حذف شد", "قرارداد با موفقیت حذف شد.")
            self.search()

        except Exception as e:
            QMessageBox.critical(self, "خطا", f"در حذف قرارداد مشکلی رخ داد:\n{str(e)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = SearchApp(None)
    w.show()
    sys.exit(app.exec())