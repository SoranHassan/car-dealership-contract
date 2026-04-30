# ui/app.py
import json
import sys
import logging
import os
import time
from datetime import datetime
from PySide6.QtGui import QPixmap, QTextCursor
from PySide6.QtCore import QTimer, Qt, QTime, QThread, Signal
from PySide6.QtWidgets import QMessageBox, QFileDialog, QLabel, QVBoxLayout, QMainWindow, QLineEdit, QApplication, QPushButton
from ui.ui import Ui_MainWindow
from database.db import DatabaseManager
from editors.photo_editor import PhotoEditorDialog
from word.generator import ContractGenerator
from ui.search_window import SearchApp


# ==================== تنظیمات ====================
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


# ==================== Thread برای ذخیره غیرهمزمان ====================
class ArchiveThread(QThread):
    """ذخیره قرارداد در پس‌زمینه برای عدم قفل شدن UI"""
    finished = Signal(bool, str, str)  # success, message, file_path
    progress = Signal(str)  # وضعیت پیشرفت
    
    def __init__(self, db, data, checkpoint_image_path, save_dir):
        super().__init__()
        self.db = db
        self.data = data
        self.checkpoint_image_path = checkpoint_image_path
        self.save_dir = save_dir
    
    def run(self):
        try:
            self.progress.emit("📄 در حال ساخت JSON...")
            contract_number = self.data["deal_info"]["deal_num"]
            
            # ساخت JSON در پوشه temp
            json_path = os.path.join(TEMP_DIR, f"contract_{contract_number}.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            
            self.progress.emit("📝 در حال تولید قرارداد Word...")
            
            # ساخت Word
            generator = ContractGenerator()
            docx_path = generator.generate(
                json_path=json_path,
                checkpoint_image_path=self.checkpoint_image_path,
                output_dir=self.save_dir
            )
            
            self.progress.emit("💾 در حال ذخیره در دیتابیس...")
            
            # ذخیره در دیتابیس
            seller_json = json.dumps(self.data["seller"], ensure_ascii=False)
            buyer_json = json.dumps(self.data["buyer"], ensure_ascii=False)
            car_json = json.dumps(self.data["car_deal"], ensure_ascii=False)
            deal_json = json.dumps(self.data["deal_info"], ensure_ascii=False)
            
            with self.db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO contracts (
                        buyer_id, seller_id, file_path, date_shamsi,
                        contract_number, seller_json, buyer_json,
                        car_json, deal_json, checkpoint_image,
                        is_payed, price_info, description_text
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.data["buyer"]["national_code"],
                    self.data["seller"]["national_code"],
                    docx_path,
                    self.data["deal_info"]["deal_date"],
                    int(contract_number),
                    seller_json,
                    buyer_json,
                    car_json,
                    deal_json,
                    self.checkpoint_image_path,
                    self.data["deal_info"].get("is_payed"),
                    self.data["deal_info"].get("price_info"),
                    self.data["deal_info"].get("description_text", ""),
                ))
                conn.commit()
            
            # پاک کردن فایل JSON موقت
            try:
                if os.path.exists(json_path):
                    os.remove(json_path)
            except:
                pass
            
            self.finished.emit(True, f"قرارداد شماره {contract_number} با موفقیت بایگانی شد.", docx_path)
            
        except Exception as e:
            logging.error(f"Archive thread error: {e}")
            self.finished.emit(False, f"خطا: {str(e)}", "")


class App(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # ایجاد پوشه temp
        os.makedirs(TEMP_DIR, exist_ok=True)
        
        # دیتابیس
        self.db = DatabaseManager()
        self.check_first_run()
        
        # UI
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        # متغیرها
        self.checkpoint_image_path = None
        self.archive_thread = None
        self.MAX_CHARS = 350
        self.temp_files = []
        
        # تنظیم ComboBoxها
        self.ui.deal_time.setDisplayFormat("HH:mm")
        
        self.ui.is_payed.clear()
        self.ui.is_payed.addItem("انتخاب کنید", None)
        self.ui.is_payed.addItem("پرداخت شد", 1)
        self.ui.is_payed.addItem("پرداخت نشد", 0)

        self.ui.price_info.clear()
        self.ui.price_info.addItem("انتخاب کنید", None)
        self.ui.price_info.addItem("تمام نقدی", "تمام نقدی")
        self.ui.price_info.addItem("تمام چک", "تمام چک")
        self.ui.price_info.addItem("نقدی و چک", "نقدی و چک")
        
        # تایمر و زمان
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_datetime_fields)
        self.timer.start(1000)
        self.ui.deal_time.setTime(QTime.currentTime())
        self.update_today_label()
        
        # دکمه‌ها
        self.ui.search_btn.clicked.connect(self.open_search_window)
        self.ui.save_btn.clicked.connect(self.on_archive_btn_clicked)
        self.ui.save_dir_btn.clicked.connect(self.on_save_dir_btn_clicked)
        self.ui.checkpoint_img_btn.clicked.connect(self.on_checkpoint_img_clicked)
        self.ui.new_deal_btn.clicked.connect(self.on_new_deal_clicked)
        
        # دکمه update_db - اگر وجود دارد
        if hasattr(self.ui, 'update_db'):
            self.ui.update_db.clicked.connect(self.on_update_db_clicked)
        
        # مقداردهی اولیه
        self.setup_contract_number()
        self.fill_pelak_alpha()
        self.setup_description_counter()
        
        # لاگ
        logging.basicConfig(
            filename=os.path.join(BASE_DIR, 'app_log.log'),
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # بنر و لوگو
        self.setup_banner_and_logo()

# در ui/app.py - تابع __init__

    # دکمه مدیریت (مخفی)
        if hasattr(self.ui, 'admin_btn'):
            self.ui.admin_btn.clicked.connect(self.on_admin_clicked)
        else:
            # اگر در ui.py نیست، بساز
            self.admin_btn = QPushButton("🔒")
            self.admin_btn.setFixedSize(26, 26)
            self.admin_btn.setStyleSheet("background-color: #6C3483; border-radius: 5px;")
            self.admin_btn.setToolTip("پنل مدیریت (فقط ادمین)")
            self.admin_btn.clicked.connect(self.on_admin_clicked)
            # اضافه کردن کنار update_db
            self.ui.header_frame.layout().addWidget(self.admin_btn)

    def on_admin_clicked(self):
        """باز کردن پنل مدیریت"""
        try:
            from ui.admin_dialog import AdminDialog
            from ui.admin_window import AdminWindow
            
            dialog = AdminDialog(self)
            if dialog.exec():
                # رمز درست است - باز کردن پنجره مدیریت
                self.admin_window = AdminWindow(DB_PATH, self)
                self.admin_window.setWindowModality(Qt.ApplicationModal)  # مهم
                self.admin_window.show()
                self.admin_window.raise_()  # جلو آوردن پنجره
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطا: {str(e)}")

    def setup_banner_and_logo(self):
        """تنظیم بنر و لوگو"""
        # Banner
        self.frame = self.ui.footer_frame
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        layout = QVBoxLayout(self.frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.image_label)
        self.load_image(resource_path("./assets/images/banner.jpg"))
        
        # Logo
        self.logo_frame = self.ui.logo_frame
        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignCenter)
        layout = QVBoxLayout(self.logo_frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.logo_label)
        self.load_logo(resource_path("./assets/images/logo.png"))

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
        self.ui.today.setText(f"{weekday} {day} {month}")

    def update_datetime_fields(self):
        from PySide6.QtCore import QDate, QTime
        self.ui.deal_date.setDate(QDate.currentDate())
        self.ui.deal_time.setTime(QTime.currentTime())

    def check_first_run(self):
        save_path = self.db.get_save_path()
        if save_path:
            return save_path
        else:
            QMessageBox.information(None, "تنظیمات اولیه", "لطفاً مسیری را برای ذخیره قراردادها انتخاب کنید.")
            folder_path = QFileDialog.getExistingDirectory(None, "انتخاب پوشه ذخیره‌سازی")
            if not folder_path:
                folder_path = os.path.join(BASE_DIR, "contracts")
                os.makedirs(folder_path, exist_ok=True)
                logging.warning(f"Default path used: {folder_path}")
            else:
                logging.info(f"Initial path set: {folder_path}")
            self.db.set_save_path(folder_path)
            return folder_path
   
    def load_logo(self, logo_path):
        try:
            pixmap = QPixmap(logo_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.logo_label.setPixmap(scaled_pixmap)
                self.logo_label.setFixedSize(50, 50)
            else:
                self.logo_label.setText("خطا در بارگذاری لوگو")
        except Exception as e:
            self.logo_label.setText(f"خطا: {str(e)}")
  
    def load_image(self, image_path):
        try:
            pixmap = QPixmap(image_path)
            if not pixmap.isNull() and hasattr(self, 'frame'):
                pixmap = pixmap.scaled(
                    self.frame.width(), self.frame.height(),
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                self.image_label.setPixmap(pixmap)
        except Exception as e:
            self.image_label.setText(f"خطا: {str(e)}")
    
    def setup_contract_number(self):
        try:
            with self.db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT MAX(contract_number) FROM contracts")
                row = cur.fetchone()
            next_number = (row[0] + 1) if row and row[0] else 10000
            self.ui.deal_num.setText(str(next_number))
            logging.info(f"Next contract number: {next_number}")
        except Exception as e:
            logging.error(f"Error loading contract number: {e}")
            self.ui.deal_num.setText("خطا")

    def on_save_dir_btn_clicked(self):
        new_path = QFileDialog.getExistingDirectory(self, "انتخاب مسیر جدید ذخیره قراردادها")
        if new_path:
            self.db.set_save_path(new_path)
            QMessageBox.information(self, "موفقیت", "مسیر ذخیره‌سازی تغییر کرد.")

    def on_new_deal_clicked(self):
        """پاک کردن فرم برای قرارداد جدید"""
        for widget in self.findChildren(QLineEdit):
            widget.clear()
        self.ui.pelak_alpha.setCurrentIndex(0)
        self.ui.is_payed.setCurrentIndex(0)
        self.ui.price_info.setCurrentIndex(0)
        self.ui.description_text.clear()
        self.checkpoint_image_path = None
        self.setup_contract_number()
        QMessageBox.information(self, "قرارداد جدید", "فرم برای قرارداد جدید آماده شد.")
    
    def on_checkpoint_img_clicked(self):
        path, _ = QFileDialog.getOpenFileName(self, "انتخاب تصویر", "", "Images (*.png *.jpg *.jpeg)")
        if not path:
            return

        dialog = PhotoEditorDialog(self)
        dialog.load_image(path)

        if dialog.exec():
            final_img = dialog.get_final_image()
            # ذخیره در پوشه temp
            temp_img_path = os.path.join(TEMP_DIR, f"checkpoint_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            final_img.save(temp_img_path)
            self.checkpoint_image_path = temp_img_path
            self.temp_files.append(temp_img_path)
            QMessageBox.information(self, "موفق", "تصویر کارشناسی ذخیره شد.")

    def setup_description_counter(self):
        self.ui.description_text.textChanged.connect(self.update_description_counter)
        self.update_description_counter()

    def update_description_counter(self):
        text = self.ui.description_text.toPlainText()
        if len(text) > self.MAX_CHARS:
            self.ui.description_text.blockSignals(True)
            self.ui.description_text.setPlainText(text[:self.MAX_CHARS])
            self.ui.description_text.blockSignals(False)
            cursor = self.ui.description_text.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.ui.description_text.setTextCursor(cursor)
            text = text[:self.MAX_CHARS]
        self.ui.character_counter.setText(f"{len(text)} / {self.MAX_CHARS}")

    def validate_all_fields(self, data):
        """بررسی کامل فیلدهای ضروری"""
        errors = []
        
        if not data["seller"].get("name", "").strip():
            errors.append("نام فروشنده نباید خالی باشد")
        if not data["seller"].get("lname", "").strip():
            errors.append("نام خانوادگی فروشنده نباید خالی باشد")
        if not data["seller"].get("national_code", "").strip():
            errors.append("کد ملی فروشنده نباید خالی باشد")
        if not data["buyer"].get("name", "").strip():
            errors.append("نام خریدار نباید خالی باشد")
        if not data["buyer"].get("lname", "").strip():
            errors.append("نام خانوادگی خریدار نباید خالی باشد")
        if not data["buyer"].get("national_code", "").strip():
            errors.append("کد ملی خریدار نباید خالی باشد")
        if not data["car_deal"].get("type", "").strip():
            errors.append("نوع خودرو نباید خالی باشد")
        if not data["car_deal"].get("body_id", "").strip():
            errors.append("شماره شاسی نباید خالی باشد")
            
        return errors

    def get_data(self):
        """جمع‌آوری داده‌ها از فرم"""
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
                "price_info": self.ui.price_info.currentText(),
                "is_payed": self.ui.is_payed.currentData(),
                "description_text": self.ui.description_text.toPlainText(),
                "deal_num": self.ui.deal_num.text()
            }
        }
        return data

    def on_archive_btn_clicked(self):
        """ذخیره قرارداد - غیرهمزمان"""
        try:
            # ۱) جمع‌آوری داده‌ها
            data = self.get_data()
            
            # ۲) اعتبارسنجی
            errors = self.validate_all_fields(data)
            if errors:
                QMessageBox.warning(self, "خطا", "\n".join(errors))
                return
            
            contract_number = data["deal_info"]["deal_num"]
            
            # ۳) بررسی عکس کارشناسی
            if not self.checkpoint_image_path or not os.path.exists(self.checkpoint_image_path):
                QMessageBox.warning(self, "خطا", "تصویر کارشناسی انتخاب نشده است.")
                return
            
            if data["deal_info"]["is_payed"] is None:
                QMessageBox.warning(self, "خطا", "لطفاً وضعیت پرداخت را انتخاب کنید.")
                return
            
            if data["deal_info"]["price_info"] == "انتخاب کنید":
                QMessageBox.warning(self, "خطا", "لطفاً نوع پرداخت را انتخاب کنید.")
                return
            
            # ۴) غیرفعال کردن دکمه ذخیره
            self.ui.save_btn.setEnabled(False)
            self.ui.save_btn.setText("در حال ذخیره...")
            
            # ۵) شروع thread برای ذخیره
            save_dir = self.db.get_save_path()
            self.archive_thread = ArchiveThread(self.db, data, self.checkpoint_image_path, save_dir)
            self.archive_thread.progress.connect(self.on_archive_progress)
            self.archive_thread.finished.connect(self.on_archive_finished)
            self.archive_thread.start()
            
        except Exception as e:
            logging.error(f"Archive error: {e}")
            QMessageBox.critical(self, "خطا", f"خطا: {str(e)}")
            self.ui.save_btn.setEnabled(True)
            self.ui.save_btn.setText("بایگانی")

    def on_archive_progress(self, message):
        """آپدیت وضعیت پیشرفت"""
        self.ui.save_btn.setText(message)

    def on_archive_finished(self, success, message, file_path):
        """پایان ذخیره‌سازی"""
        self.ui.save_btn.setEnabled(True)
        self.ui.save_btn.setText("بایگانی")
        
        if success:
            # ========== پاک کردن کش دیتابیس ==========
            self.db._clear_cache()
            
            # ========== بستن و باز کردن مجدد پنجره جستجو (اگه باز باشه) ==========
            if hasattr(self, 'search_window') and self.search_window and self.search_window.isVisible():
                self.search_window.show_all_contracts()  # رفرش لیست
            
            # پاک کردن temp
            try:
                for f in self.temp_files:
                    if os.path.exists(f):
                        os.remove(f)
                self.temp_files.clear()
                self.checkpoint_image_path = None
            except:
                pass
            
            # آپدیت شماره قرارداد
            self.setup_contract_number()
            QMessageBox.information(self, "موفقیت", message)
        else:
            QMessageBox.critical(self, "خطا", message)
            
    def open_search_window(self):
        if not hasattr(self, "search_window") or self.search_window is None:
            self.search_window = SearchApp(self.db)
        self.search_window.show()
        self.search_window.raise_()
        self.search_window.search_async()

    def on_update_db_clicked(self):
        """بروزرسانی دیتابیس - اضافه کردن ستون‌های جدید"""
        try:
            import sqlite3
            
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            
            # گرفتن ستون‌های موجود
            cur.execute("PRAGMA table_info(contracts)")
            columns = [col[1] for col in cur.fetchall()]
            
            added = []
            
            # اضافه کردن ستون created_at (بدون DEFAULT)
            if "created_at" not in columns:
                cur.execute("ALTER TABLE contracts ADD COLUMN created_at TIMESTAMP")
                added.append("created_at")
            
            # اضافه کردن ستون is_payed
            if "is_payed" not in columns:
                cur.execute("ALTER TABLE contracts ADD COLUMN is_payed INTEGER DEFAULT NULL")
                added.append("is_payed")
            
            # اضافه کردن ستون price_info
            if "price_info" not in columns:
                cur.execute("ALTER TABLE contracts ADD COLUMN price_info TEXT DEFAULT NULL")
                added.append("price_info")
            
            # اضافه کردن ستون description_text
            if "description_text" not in columns:
                cur.execute("ALTER TABLE contracts ADD COLUMN description_text TEXT DEFAULT NULL")
                added.append("description_text")
            
            # به‌روزرسانی created_at برای رکوردهای قدیمی (با استفاده از date_shamsi)
            if "created_at" in added:
                try:
                    cur.execute("UPDATE contracts SET created_at = datetime('now') WHERE created_at IS NULL")
                except:
                    # اگر تاریخ شمسی دارید میتونید از اون استفاده کنید
                    pass
            
            conn.commit()
            conn.close()
            
            if added:
                QMessageBox.information(
                    self,
                    "بروزرسانی دیتابیس",
                    f"ستون‌های زیر با موفقیت اضافه شدند:\n{', '.join(added)}\n\nمقدار همه رکوردهای قدیمی NULL است."
                )
            else:
                QMessageBox.information(
                    self,
                    "بروزرسانی دیتابیس",
                    "دیتابیس قبلاً بروز است. هیچ ستون جدیدی اضافه نشد."
                )
            
            # رفرش شماره قرارداد
            self.setup_contract_number()
            
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطا در بروزرسانی دیتابیس:\n{str(e)}")
      
    def closeEvent(self, event):
        """پاک کردن منابع هنگام بستن"""
        # منتظر ماندن برای اتمام thread
        if self.archive_thread and self.archive_thread.isRunning():
            self.archive_thread.quit()
            self.archive_thread.wait(2000)
        
        # پاک کردن فایل‌های temp قدیمی
        try:
            for f in self.temp_files:
                if os.path.exists(f):
                    os.remove(f)
            # پاک کردن فایل‌های temp قدیمی (بیشتر از 24 ساعت)
            for filename in os.listdir(TEMP_DIR):
                file_path = os.path.join(TEMP_DIR, filename)
                if os.path.isfile(file_path):
                    file_age = time.time() - os.path.getmtime(file_path)
                    if file_age > 86400:  # 24 ساعت
                        os.remove(file_path)
        except:
            pass
        
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(app.exec())