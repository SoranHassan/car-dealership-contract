import json
import sys
import logging
import os
import sqlite3
import tempfile
import shutil
from PySide6.QtGui import QPixmap, QIcon, QDesktopServices
from PySide6.QtCore import QTimer, Qt, QTime, QUrl
from PySide6.QtWidgets import QPushButton, QMessageBox, QFileDialog, QLabel, QHBoxLayout, QVBoxLayout, QMainWindow, QWidget, QLineEdit, QApplication, QTableWidget, QTableWidgetItem
from .ui import Ui_MainWindow
from database.db import DatabaseManager
from editors.photo_editor import PhotoEditorDialog
from word import ContractGenerator
from ui.sync_service import SyncService
from datetime import datetime


def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(relative_path)


if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(__file__))

DB_PATH = os.path.join(BASE_DIR, "settings.db")
TEMP_DIR = os.path.join(BASE_DIR, "temp")


class SearchApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("جستجوی قراردادها")
        self.setMinimumWidth(750)

        self.setStyleSheet("""
            QWidget {
                font-family: Aria, Pelak;
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

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("نام یا نام خانوادگی")

        self.ncode_edit = QLineEdit()
        self.ncode_edit.setPlaceholderText("کد ملی")

        self.dealnum_edit = QLineEdit()
        self.dealnum_edit.setPlaceholderText("شماره قرارداد")

        self.search_btn = QPushButton("جستجو")
        self.search_btn.setStyleSheet("background-color: #1C4D8D; color: white;")
        self.open_btn = QPushButton("باز کردن قرارداد")
        self.delete_btn = QPushButton("حذف")
        self.delete_btn.setStyleSheet("background-color: #C3110C; color: white;")

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["خریدار", "فروشنده", "شماره قرارداد"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setDefaultSectionSize(220)
        self.table.verticalHeader().setDefaultSectionSize(34)

        top_layout = QHBoxLayout()
        top_layout.addWidget(self.name_edit)
        top_layout.addWidget(self.ncode_edit)
        top_layout.addWidget(self.dealnum_edit)
        top_layout.addWidget(self.search_btn)

        layout = QVBoxLayout(self)
        layout.addLayout(top_layout)
        layout.addWidget(self.table)
        layout.addWidget(self.open_btn)
        layout.addWidget(self.delete_btn)

        self.search_btn.clicked.connect(self.search)
        self.name_edit.textChanged.connect(self.search)
        self.ncode_edit.textChanged.connect(self.search)
        self.dealnum_edit.textChanged.connect(self.search)
        self.open_btn.clicked.connect(self.open_selected)
        self.delete_btn.clicked.connect(self.delete_selected)

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
            buyer = json.loads(buyer_json)
            seller = json.loads(seller_json)
            buyer_name = f"{buyer['name']} {buyer['lname']}"
            seller_name = f"{seller['name']} {seller['lname']}"

            self.table.setItem(row_idx, 0, QTableWidgetItem(buyer_name))
            self.table.setItem(row_idx, 1, QTableWidgetItem(seller_name))
            self.table.setItem(row_idx, 2, QTableWidgetItem(str(contract_number)))

    def open_selected(self):
        row = self.table.currentRow()
        if row < 0:
            return

        contract_number = self.table.item(row, 2).text()

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT file_path FROM contracts WHERE contract_number = ?", (contract_number,))
        result = cur.fetchone()
        conn.close()

        if result and result[0]:
            QDesktopServices.openUrl(QUrl.fromLocalFile(result[0]))

    def delete_selected(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "خطا", "لطفاً یک ردیف را انتخاب کنید.")
            return

        contract_number = self.table.item(row, 2).text()

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


class App(QMainWindow):
    
    def __init__(self):
        super().__init__()
        
        # ========== مرحله 1: دیتابیس ==========
        self.db = DatabaseManager()
        self.check_first_run()
        
        # ========== مرحله 2: راه‌اندازی UI ==========
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        # ========== مرحله 3: متغیرهای اولیه ==========
        self.checkpoint_image_path = None
        self.temp_files = []
        self.is_exchange = False       
        self.car1_data = None          
        self.car2_data = None
        
        # ========== مرحله 4: سرویس همگام‌سازی ==========
        self.sync_service = SyncService()
        
        # ========== مرحله 5: تایمر و زمان ==========
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_datetime_fields)
        self.timer.start(1000)
        self.ui.deal_time.setTime(QTime.currentTime())
        self.update_today_label()
        
        # ========== مرحله 6: دکمه‌ها ==========
        self.ui.search_btn.clicked.connect(self.open_search_window)
        self.ui.save_btn.clicked.connect(self.on_archive_btn_clicked)
        self.ui.save_dir_btn.clicked.connect(self.on_save_dir_btn_clicked)
        self.ui.checkpoint_img_btn.clicked.connect(self.on_checkpoint_img_clicked)
        self.ui.new_deal_btn.clicked.connect(self.on_new_deal_clicked)
        
        # ========== مرحله 7: مقداردهی اولیه فرم ==========
        self.setup_contract_number()
        self.fill_pelak_alpha()
        
        # ========== مرحله 8: لاگ ==========
        logging.basicConfig(
            filename='app_log.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # ========== مرحله 9: بنر و لوگو ==========
        self.frame = self.ui.footer_frame
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        layout = QVBoxLayout(self.frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.image_label)
        self.load_image("./assets/images/banner.jpg")
        
        self.logo_frame = self.ui.logo_frame
        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignCenter)
        layout = QVBoxLayout(self.logo_frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.logo_label)
        self.load_logo("./assets/images/logo.png")
        
        # ========== مرحله 10: پوشه temp ==========
        os.makedirs(TEMP_DIR, exist_ok=True)
    def fill_pelak_alpha(self):
        letters = ['ب', 'ج', 'د', 'س', 'ص', 'ط', 'ق', 'ل', 'م', 'ن', 'و', 'ه', 'ی']
        self.ui.pelak_alpha.clear()
        self.ui.pelak_alpha.addItems(letters)

    def update_today_label(self):
        from persiantools.jdatetime import JalaliDate
        today = JalaliDate.today()
        weekday = today.strftime("%A", locale="fa")
        month = today.strftime("%B", locale="fa")
        day = today.day
        text = f"{weekday} {day} {month}"
        self.ui.today.setText(text)

    def update_datetime_fields(self):
        from PySide6.QtCore import QDate, QTime
        self.ui.deal_date.setDate(QDate.currentDate())
        self.ui.deal_time.setTime(QTime.currentTime())

    def check_first_run(self):
        save_path = self.db.get_save_path()
        if save_path:
            folder_path = save_path
        else:
            QMessageBox.information(None, "تنظیمات اولیه", "لطفاً مسیری را برای ذخیره قراردادها انتخاب کنید.")
            folder_path = QFileDialog.getExistingDirectory(None, "انتخاب پوشه ذخیره‌سازی")
            if not folder_path:
                folder_path = os.path.join(os.getcwd(), "contracts")
                os.makedirs(folder_path, exist_ok=True)
                logging.warning(f"User cancelled folder selection. Default path used: {folder_path}")
            else:
                logging.info(f"Initial path set by user: {folder_path}")
            self.db.set_save_path(folder_path)
        return folder_path
   
    def load_logo(self, logo_path):
        try:
            logo_path = resource_path(logo_path)
            pixmap = QPixmap(logo_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(110, 110, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.logo_label.setPixmap(scaled_pixmap)
                self.logo_label.setText("")
                self.logo_label.setFixedSize(110, 110)
                self.logo_label.setScaledContents(True)
            else:
                self.logo_label.setText("خطا در بارگذاری لوگو")
                self.logo_label.setStyleSheet("color: red;")
        except Exception as e:
            self.logo_label.setText(f"خطا: {str(e)}")
  
    def load_image(self, image_path):
        try:
            image_path = resource_path(image_path)
            pixmap = QPixmap(image_path)
            if not pixmap.isNull() and self.frame:
                pixmap = pixmap.scaled(
                    self.frame.width(),
                    self.frame.height(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.image_label.setPixmap(pixmap)
                self.image_label.setText("")
            else:
                self.image_label.setText("خطا در بارگذاری عکس")
                self.image_label.setStyleSheet("color: red;")
        except Exception as e:
            self.image_label.setText(f"خطا: {str(e)}")
    
    def setup_contract_number(self):
        try:
            with self.db.connect() as conn:
                cur = conn.cursor()
                cur.execute("SELECT MAX(contract_number) FROM contracts")
                row = cur.fetchone()
            if row and row[0]:
                next_number = row[0] + 1
            else:
                next_number = 10000
            self.current_contract_number = next_number
            self.ui.deal_num.setText(str(next_number))
            logging.info(f"Next contract number loaded: {next_number}")
        except Exception as e:
            logging.error(f"Error loading contract number: {str(e)}")
            self.ui.deal_num.setText("خطا")

    def on_save_dir_btn_clicked(self):
        new_path = QFileDialog.getExistingDirectory(self, "انتخاب مسیر جدید ذخیره قراردادها")
        if new_path:
            self.db.set_save_path(new_path)
            QMessageBox.information(self, "موفقیت", "مسیر ذخیره‌سازی با موفقیت تغییر کرد.")
        else:
            QMessageBox.warning(self, "لغو شد", "مسیر جدید انتخاب نشد.")

    def on_new_deal_clicked(self):
        """پاک کردن کامل فرم برای قرارداد جدید"""
        # پاک کردن تمام QLineEdit ها
        for widget in self.findChildren(QLineEdit):
            widget.clear()
        # ریست کردن کامبوباکس
        self.ui.pelak_alpha.setCurrentIndex(0)
        # ریست کردن عکس کارشناسی
        self.checkpoint_image_path = None
        # تنظیم شماره قرارداد جدید
        self.setup_contract_number()
        # پاک کردن فایل‌های temp قدیمی
        self.cleanup_temp_files()
        QMessageBox.information(self, "قرارداد جدید", "فرم برای قرارداد جدید آماده شد.")
    
    def on_checkpoint_img_clicked(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "انتخاب تصویر",
            "",
            "Images (*.png *.jpg *.jpeg)"
        )
        if not path:
            return

        dialog = PhotoEditorDialog(self)
        dialog.load_image(path)

        if dialog.exec():
            final_img = dialog.get_final_image()
            # ذخیره در پوشه temp به جای روت پروژه
            temp_img_path = os.path.join(TEMP_DIR, f"checkpoint_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            final_img.save(temp_img_path)
            self.checkpoint_image_path = temp_img_path
            self.temp_files.append(temp_img_path)
            QMessageBox.information(self, "موفق", "تصویر کارشناسی با موفقیت ذخیره شد.")

    def cleanup_temp_files(self):
        """پاک کردن تمام فایل‌های موقت"""
        for file_path in self.temp_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                logging.warning(f"Could not delete temp file {file_path}: {e}")
        self.temp_files = []
        # پاک کردن پوشه temp از فایل‌های قدیمی (بیشتر از 24 ساعت)
        try:
            now = datetime.now()
            for filename in os.listdir(TEMP_DIR):
                file_path = os.path.join(TEMP_DIR, filename)
                if os.path.isfile(file_path):
                    file_age = now - datetime.fromtimestamp(os.path.getmtime(file_path))
                    if file_age.days > 1:
                        os.remove(file_path)
        except Exception as e:
            logging.warning(f"Temp cleanup error: {e}")

    def validate_all_fields(self, data):
        """بررسی کامل همه فیلدهای ضروری"""
        errors = []
        
        # فروشنده
        if not data["seller"].get("name", "").strip():
            errors.append("نام فروشنده نباید خالی باشد")
        if not data["seller"].get("lname", "").strip():
            errors.append("نام خانوادگی فروشنده نباید خالی باشد")
        if not data["seller"].get("national_code", "").strip():
            errors.append("کد ملی فروشنده نباید خالی باشد")
        if not data["seller"].get("phone", "").strip():
            errors.append("تلفن فروشنده نباید خالی باشد")
            
        # خریدار
        if not data["buyer"].get("name", "").strip():
            errors.append("نام خریدار نباید خالی باشد")
        if not data["buyer"].get("lname", "").strip():
            errors.append("نام خانوادگی خریدار نباید خالی باشد")
        if not data["buyer"].get("national_code", "").strip():
            errors.append("کد ملی خریدار نباید خالی باشد")
        if not data["buyer"].get("phone", "").strip():
            errors.append("تلفن خریدار نباید خالی باشد")
            
        # خودرو
        if not data["car_deal"].get("type", "").strip():
            errors.append("نوع خودرو نباید خالی باشد")
        if not data["car_deal"].get("body_id", "").strip():
            errors.append("شماره شاسی نباید خالی باشد")
            
        # معامله
        if not data["deal_info"].get("price_rial", "").strip():
            errors.append("مبلغ (ریال) نباید خالی باشد")
            
        return errors

    def get_data(self):
        RLM = "\u200F"
        LRM = "\u200E"

        pelak_full = (
            f"{LRM}{self.ui.pelak_two.text()}{RLM}"
            f"{self.ui.pelak_alpha.currentText()}{RLM}"
            f"{LRM}{self.ui.pelak_three.text()}{RLM}ایران{LRM}{self.ui.pelak_iran.text()}"
        )
                
        data = {
            "seller": {
                "name": self.ui.seller_name.text(),
                "lname": self.ui.seller_lname.text(),
                "father": self.ui.seller_father.text(),
                "birth": self.ui.seller_birth.text(),
                "national_code": self.ui.seller_ncode.text(),
                "national_shcode": self.ui.seller_shcode.text(),
                "from": self.ui.seller_from.text(),
                "phone": self.ui.seller_phone.text(),
                "adress": self.ui.seller_adress.text()
            },
            "buyer": {
                "name": self.ui.buyer_name.text(),
                "lname": self.ui.buyer_lname.text(),
                "father": self.ui.buyer_father.text(),
                "birth": self.ui.buyer_birth.text(),
                "national_code": self.ui.buyer_ncode.text(),
                "national_shcode": self.ui.buyer_shcode.text(),
                "from": self.ui.buyer_from.text(),
                "phone": self.ui.buyer_phone.text(),
                "address": self.ui.buyer_adress.text()
            },
            "car_deal": {
                "type": self.ui.car_type.text(),
                "color": self.ui.car_color.text(),
                "system": self.ui.car_system.text(),
                "model": self.ui.car_model.text(),
                "body_id": self.ui.car_body_id.text(),
                "motor_id": self.ui.car_motor_id.text(),
                "kilometer": self.ui.car_kilometer.text(),
                "pelak": pelak_full,
                "car_info": self.ui.car_info.text()
            },
            "deal_info": {
                "deal_date": self.ui.deal_date.text(),
                "deal_time": self.ui.deal_time.text(),
                "day_respite": self.ui.day_respite.text(),
                "price_rial": self.ui.price_rial.text(),
                "price_toman": self.ui.price_toman.text(),
                "price_info": self.ui.price_info.text(),
                "deal_num": self.ui.deal_num.text()
            }
        }

        return data

    def on_archive_btn_clicked(self):
        try:
            self.db.logger.log("archive_start", "", {})
            
            # ۱) جمع‌آوری داده‌ها
            data = self.get_data()
            
            # ۲) اعتبارسنجی کامل
            errors = self.validate_all_fields(data)
            if errors:
                QMessageBox.warning(self, "خطا", "\n".join(errors))
                return
            
            # ✅ تعریف contract_number در اینجا
            contract_number = int(self.ui.deal_num.text())  # از UI بگیر
            
            # ۳) بررسی عکس کارشناسی
            if not self.checkpoint_image_path or not os.path.exists(self.checkpoint_image_path):
                QMessageBox.warning(self, "خطا", "تصویر کارشناسی انتخاب نشده یا وجود ندارد.")
                return
            
            # ۴) ساخت JSON در پوشه temp
            json_path = os.path.join(TEMP_DIR, f"contract_{contract_number}.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.temp_files.append(json_path)
            self.db.logger.log("archive_json_saved", "", {"json_path": json_path})
            
            # ۵) ساخت Word
            save_dir = self.db.get_save_path()
            generator = ContractGenerator()
            
            docx_path = generator.generate(
                json_path=json_path,
                checkpoint_image_path=self.checkpoint_image_path,
                output_dir=save_dir
            )
            
            # ۶) ذخیره در دیتابیس
            seller_json = json.dumps(data["seller"], ensure_ascii=False)
            buyer_json = json.dumps(data["buyer"], ensure_ascii=False)
            car_json = json.dumps(data["car_deal"], ensure_ascii=False)
            deal_json = json.dumps(data["deal_info"], ensure_ascii=False)
            
            with self.db.connect() as conn:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO contracts (
                        buyer_id, seller_id, file_path, date_shamsi,
                        contract_number, seller_json, buyer_json,
                        car_json, deal_json, checkpoint_image
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    data["buyer"]["national_code"],
                    data["seller"]["national_code"],
                    docx_path,
                    data["deal_info"]["deal_date"],
                    contract_number,
                    seller_json,
                    buyer_json,
                    car_json,
                    deal_json,
                    self.checkpoint_image_path,
                ))
                conn.commit()
            
            # ۷) همگام‌سازی با سرور
            if hasattr(self, 'sync_service') and self.sync_service:
                self.sync_service.upload_new_contract(contract_number)
            
            # ۸) پاک کردن فایل‌های temp
            self.cleanup_temp_files()
            
            # ۹) ریست مسیر عکس کارشناسی
            self.checkpoint_image_path = None
            
            # ۱۰) آپدیت شماره قرارداد بعدی
            self.setup_contract_number()
            
            # ۱۱) حذف فایل JSON موقت
            try:
                if os.path.exists(json_path):
                    os.remove(json_path)
            except:
                pass
            
            QMessageBox.information(self, "بایگانی موفق", f"قرارداد شماره {contract_number} با موفقیت بایگانی شد.")
            
        except Exception as e:
            logging.error(f"Archive error: {str(e)}")
            QMessageBox.critical(self, "خطا", f"در فرآیند بایگانی خطایی رخ داد:\n{str(e)}")
        except Exception as e:
            logging.error(f"Archive error: {str(e)}")
            QMessageBox.critical(self, "خطا", f"در فرآیند بایگانی خطایی رخ داد:\n{str(e)}")
    def open_search_window(self):
        self.search_window = SearchApp()
        self.search_window.show()
    
    def closeEvent(self, event):
        """پاک کردن فایل‌های temp هنگام بستن برنامه"""
        self.cleanup_temp_files()
        event.accept()


