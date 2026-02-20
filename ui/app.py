import json
import sys, logging, os, sqlite3
from PySide6.QtGui import QPixmap, QIcon, QDesktopServices
from PySide6.QtCore import QTimer, Qt, QTime, QUrl
from PySide6.QtWidgets import QComboBox, QPushButton, QMessageBox, QFileDialog, QLabel,QHBoxLayout, QVBoxLayout, QMainWindow,QWidget, QLineEdit, QApplication, QTableWidget, QTableWidgetItem
from ui import Ui_MainWindow
from database.db import DatabaseManager
from editors.photo_editor import PhotoEditorDialog
from word import ContractGenerator  
from ui import Ui_MainWindow



def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(relative_path)


if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(__file__))

DB_PATH = os.path.join(BASE_DIR, "settings.db")

class SearchApp(QWidget):
    def __init__(self, db):
        super().__init__()
        self.setWindowTitle("جستجوی قراردادها")
        self.setMinimumWidth(750)

        # استایل کلی
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

        # فیلدهای ورودی
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("نام یا نام خانوادگی")

        self.ncode_edit = QLineEdit()
        self.ncode_edit.setPlaceholderText("کد ملی")

        self.dealnum_edit = QLineEdit()
        self.dealnum_edit.setPlaceholderText("شماره قرارداد")

        self.payed_filter = QComboBox()
        self.payed_filter.addItem("همه", None)
        self.payed_filter.addItem("پرداخت شده", 1)
        self.payed_filter.addItem("پرداخت نشده", 0)

        # دکمه‌ها
        self.search_btn = QPushButton("جستجو")
        self.search_btn.setStyleSheet("""
                background-color: #1C4D8D;
                color: white;
                           """)
        self.open_btn = QPushButton("باز کردن قرارداد")
        self.delete_btn = QPushButton("حذف")
        self.delete_btn.setStyleSheet("""
                background-color: #C3110C;
                color: white;
                           """)

        # جدول
        self.table = QTableWidget()
        self.table.itemChanged.connect(self.on_item_changed)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["خریدار", "فروشنده", "شماره قرارداد", "پرداخت"])

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
        top_layout.addWidget(self.payed_filter)

        layout = QVBoxLayout(self)
        layout.addLayout(top_layout)
        layout.addWidget(self.table)
        layout.addWidget(self.open_btn)
        layout.addWidget(self.delete_btn)

        # اتصال‌ها
        self.search_btn.clicked.connect(self.search)
        self.name_edit.textChanged.connect(self.search)
        self.ncode_edit.textChanged.connect(self.search)
        self.dealnum_edit.textChanged.connect(self.search)
        self.open_btn.clicked.connect(self.open_selected)
        self.delete_btn.clicked.connect(self.delete_selected)
        self.payed_filter.currentIndexChanged.connect(self.search)

        # اولین بار همه را نمایش بده
        self.search()

    def search(self):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        name = self.name_edit.text().strip()
        ncode = self.ncode_edit.text().strip()
        dealnum = self.dealnum_edit.text().strip()
        payed_value = self.payed_filter.currentData()

        query = """
            SELECT buyer_json, seller_json, buyer_id, contract_number, file_path, is_payed
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

        if payed_value is not None:
            query += " AND is_payed = ?"
            params.append(payed_value)

        cur.execute(query, params)
        rows = cur.fetchall()
        conn.close()


        self.table.blockSignals(True)   # ← باید اینجا باشد

        self.table.setRowCount(len(rows))

        for row_idx, (buyer_json, seller_json, buyer_id, contract_number, file_path, is_payed) in enumerate(rows):

            if is_payed is None:
                is_payed = 0

            # تبدیل JSON به dict
            buyer = json.loads(buyer_json)
            seller = json.loads(seller_json)

            buyer_name = f"{buyer['name']} {buyer['lname']}"
            seller_name = f"{seller['name']} {seller['lname']}"

            # نمایش فقط نام‌ها و شماره قرارداد
            self.table.setItem(row_idx, 0, QTableWidgetItem(buyer_name))
            self.table.setItem(row_idx, 1, QTableWidgetItem(seller_name))
            self.table.setItem(row_idx, 2, QTableWidgetItem(str(contract_number)))

            checkbox = QTableWidgetItem()
            checkbox.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)

            if is_payed == 1:
                checkbox.setCheckState(Qt.Checked)
            else:
                checkbox.setCheckState(Qt.Unchecked)

            self.table.setItem(row_idx, 3, checkbox)

            from PySide6.QtGui import QColor
            if is_payed == 1:
                color = QColor(200, 255, 200)  # سبز روشن
            else:
                color = QColor(255, 200, 200)  # قرمز روشن

            for col in range(3):
                self.table.item(row_idx, col).setBackground(color)

        self.table.blockSignals(False)  # ← اینجا درست است

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
            with sqlite3.connect("settings.db") as conn:
                cur = conn.cursor()
                cur.execute("DELETE FROM contracts WHERE contract_number=?", (contract_number,))
                conn.commit()

            QMessageBox.information(self, "حذف شد", "قرارداد با موفقیت حذف شد.")

            self.search()  # رفرش جدول

        except Exception as e:
            QMessageBox.critical(self, "خطا", f"در حذف قرارداد مشکلی رخ داد:\n{str(e)}")

    def on_item_changed(self, item):
        # فقط ستون چک‌باکس
        if item.column() != 3:
            return

        row = item.row()
        contract_number = self.table.item(row, 2).text()

        new_value = 1 if item.checkState() == Qt.Checked else 0

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("UPDATE contracts SET is_payed=? WHERE contract_number=?", (new_value, contract_number))
        conn.commit()
        self.update_contract_word(contract_number)
        conn.close()

        # رنگ ردیف را آپدیت کن
        from PySide6.QtGui import QColor
        color = QColor(200, 255, 200) if new_value == 1 else QColor(255, 200, 200)

        for col in range(3):
            self.table.item(row, col).setBackground(color)   

    def update_contract_word(self, contract_number):
        # ۱) گرفتن اطلاعات قرارداد از دیتابیس
        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT seller_json, buyer_json, car_json, deal_json, checkpoint_image, file_path FROM contracts WHERE contract_number = ?", (contract_number,))
            row = cur.fetchone()

        if not row:
            return

        seller_json, buyer_json, car_json, deal_json, checkpoint_path, old_docx_path = row

        # ۲) ساخت JSON کامل
        data = {
            "seller": json.loads(seller_json),
            "buyer": json.loads(buyer_json),
            "car_deal": json.loads(car_json),
            "deal_info": json.loads(deal_json)
        }

        # ۳) ذخیره JSON در temp
        temp_json = os.path.join(os.getcwd(), "temp", f"contract_{contract_number}.json")
        os.makedirs(os.path.dirname(temp_json), exist_ok=True)

        with open(temp_json, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # ۴) ساخت Word جدید
        generator = ContractGenerator()
        save_dir = os.path.dirname(old_docx_path)

        new_docx = generator.generate(
            json_path=temp_json,
            checkpoint_image_path=checkpoint_path,
            output_dir=save_dir
        )

        # ۵) آپدیت مسیر فایل در دیتابیس (اگر لازم باشد)
        with self.db.connect() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE contracts SET file_path = ? WHERE contract_number = ?", (new_docx, contract_number))
            conn.commit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = SearchApp()
    w.show()
    sys.exit(app.exec())


class App(QMainWindow):

    def __init__(self):
        super().__init__()
        
        self.db = DatabaseManager()
        self.check_first_run()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.ui.deal_time.setDisplayFormat("HH:mm")

        self.ui.is_payed.clear()
        self.ui.is_payed.addItem("انتخاب کنید", None)
        self.ui.is_payed.addItem("پرداخت شده", 1)
        self.ui.is_payed.addItem("پرداخت نشده", 0)

        self.is_exchange = False       
        self.car1_data = None          
        self.car2_data = None          

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_datetime_fields)
        self.timer.start(1000)  
        self.ui.deal_time.setTime(QTime.currentTime())
        self.update_today_label()
        self.ui.search_btn.clicked.connect(self.open_search_window)
        self.ui.save_btn.clicked.connect(self.on_archive_btn_clicked)
        self.ui.save_dir_btn.clicked.connect(self.on_save_dir_btn_clicked)
        self.ui.checkpoint_img_btn.clicked.connect(self.on_checkpoint_img_clicked)
        self.ui.new_deal_btn.clicked.connect(self.on_new_deal_clicked)
        self.ui.update_db.clicked.connect(self.on_update_db_clicked)
        self.setup_contract_number()
        self.fill_pelak_alpha()


        logging.basicConfig(
            filename='app_log.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s')

        self.frame = self.ui.footer_frame
        
        # ------------- Banner 
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        
        layout = QVBoxLayout(self.frame)
        layout.setContentsMargins(0, 0, 0, 0)  # حذف حاشیه‌ها
        layout.addWidget(self.image_label)
        
        self.load_image("./assets/images/banner.jpg")  

        # ------------- Logo 
        self.logo_frame = self.ui.logo_frame
        
        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignCenter)      

        layout = QVBoxLayout(self.logo_frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.logo_label)
        
        self.load_logo("./assets/images/logo.png") 

    def on_update_db_clicked(self):
        try:
            conn = sqlite3.connect("settings.db")
            cur = conn.cursor()

            # بررسی وجود ستون
            cur.execute("PRAGMA table_info(contracts)")
            columns = [col[1] for col in cur.fetchall()]

            if "is_payed" not in columns:
                cur.execute("ALTER TABLE contracts ADD COLUMN is_payed INTEGER DEFAULT 0")
                conn.commit()

                QMessageBox.information(
                    self,
                    "بروزرسانی انجام شد",
                    "دیتابیس با موفقیت بروزرسانی شد"
                )
            else:
                QMessageBox.information(
                    self,
                    "بروزرسانی انجام شد",
                    "تنظیمات از قبل وجود دارد"
                )

            conn.close()

        except Exception as e:
            QMessageBox.critical(
                self,
                "خطا",
                f"در بروزرسانی دیتابیس مشکلی رخ داد:\n{str(e)}"
            )

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

        # اگر مسیر قبلاً ذخیره شده باشد → همان را استفاده کن
        if save_path:
                folder_path = save_path

        else:
                # مسیر ذخیره وجود ندارد → از کاربر بپرس
                QMessageBox.information(None, "تنظیمات اولیه", "لطفاً مسیری را برای ذخیره قراردادها انتخاب کنید.")
                folder_path = QFileDialog.getExistingDirectory(None, "انتخاب پوشه ذخیره‌سازی")

                # اگر کاربر مسیر انتخاب نکرد
                if not folder_path:
                        folder_path = os.path.join(os.getcwd(), "contracts")
                        os.makedirs(folder_path, exist_ok=True)
                        logging.warning(f"User cancelled folder selection. Default path used: {folder_path}")
                else:
                        logging.info(f"Initial path set by user: {folder_path}")

                # ذخیره مسیر در دیتابیس
                self.db.set_save_path(folder_path)

        return folder_path
   
    def load_logo(self, logo_path):
        try:
            logo_path = resource_path(logo_path)   # ← مهم

            pixmap = QPixmap(logo_path)
            
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    76, 76,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.logo_label.setPixmap(scaled_pixmap)
                self.logo_label.setText("")
                self.logo_label.setFixedSize(76, 76)
                self.logo_label.setScaledContents(True)
            else:
                self.logo_label.setText("خطا در بارگذاری لوگو")
                self.logo_label.setStyleSheet("color: red;")

        except Exception as e:
            self.logo_label.setText(f"خطا: {str(e)}")
  
    def load_image(self, image_path):
        try:
            image_path = resource_path(image_path)   # ← مهم

            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
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

        for widget in self.findChildren(QLineEdit):
            widget.clear()

        self.ui.pelak_alpha.setCurrentIndex(0)

        self.setup_contract_number()

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
            final_img.save("checkpoint_final.png")
 
    def clear_all_fields(self):
        # پاک کردن تمام QLineEdit ها
        for widget in self.findChildren(QLineEdit):
            widget.clear()

        # ریست پلاک
        self.ui.pelak_alpha.setCurrentIndex(0)

        # حذف عکس کارشناسی اگر وجود دارد
        if hasattr(self, "checkpoint_image_path"):
            del self.checkpoint_image_path

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
                "deal_date": "",
                "deal_time": self.ui.deal_time.text(),
                "day_respite": self.ui.day_respite.text(),
                "price_rial": self.ui.price_rial.text(),
                "price_toman": self.ui.price_toman.text(),
                "price_info": self.ui.price_info.text(),
                "is_payed": self.ui.is_payed.currentData()
            }
        }

        # نام کامل
        data["seller"]["fname"] = f"{data['seller']['name']} {data['seller']['lname']}"
        data["buyer"]["fname"] = f"{data['buyer']['name']} {data['buyer']['lname']}"

        return data

    def validate_person_fields(self, buyer, seller):
        errors = []

        # Seller
        if not seller.get("name", "").strip():
            errors.append("نام فروشنده نباید خالی باشد")
        if not seller.get("lname", "").strip():
            errors.append("نام خانوادگی فروشنده نباید خالی باشد")
        if not seller.get("national_code", "").strip():
            errors.append("کد ملی فروشنده نباید خالی باشد")

        # Buyer
        if not buyer.get("name", "").strip():
            errors.append("نام خریدار نباید خالی باشد")
        if not buyer.get("lname", "").strip():
            errors.append("نام خانوادگی خریدار نباید خالی باشد")
        if not buyer.get("national_code", "").strip():
            errors.append("کد ملی خریدار نباید خالی باشد")

        return errors

    def on_archive_btn_clicked(self):

        try:
            self.db.logger.log("archive_start", "", {})

            # ۱) جمع‌آوری داده‌ها
            data = self.get_data()
            data["deal_info"]["deal_date"] = self.ui.deal_date.text()
            data["deal_info"]["deal_num"] = self.ui.deal_num.text()

            contract_number = data["deal_info"]["deal_num"]

            # 🔥 ۲) Validation — اینجا باید باشد
            errors = self.validate_person_fields(data["buyer"], data["seller"])
            if errors:
                QMessageBox.warning(self, "خطا", "\n".join(errors))
                return

            # ۳) ساخت temp
            root_dir = os.getcwd()
            temp_dir = os.path.join(root_dir, "temp")
            os.makedirs(temp_dir, exist_ok=True)

            # ذخیره JSON
            json_path = os.path.join(temp_dir, f"contract_{contract_number}.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            self.db.logger.log("archive_json_saved", "", {"json_path": json_path})

            # ۴) بررسی عکس کارشناسی
            checkpoint_path = os.path.join(root_dir, "checkpoint_final.png")
            if not os.path.exists(checkpoint_path):
                QMessageBox.warning(self, "خطا", "تصویر کارشناسی یافت نشد.")
                return
            
            if data["deal_info"]["is_payed"] is None:
                QMessageBox.warning(self, "خطا", "لطفاً وضعیت پرداخت را انتخاب کنید.")
                return

            # ۵) ساخت Word
            save_dir = self.db.get_save_path()
            generator = ContractGenerator()

            docx_path = generator.generate(
                json_path=json_path,
                checkpoint_image_path=checkpoint_path,
                output_dir=save_dir
            )

            # ۶) ذخیره در دیتابیس
            seller_json = json.dumps(data["seller"], ensure_ascii=False)
            buyer_json = json.dumps(data["buyer"], ensure_ascii=False)
            car_json = json.dumps(data["car_deal"], ensure_ascii=False)
            deal_json = json.dumps(data["deal_info"], ensure_ascii=False)

            with self.db.connect() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO contracts (
                        buyer_id,
                        seller_id,
                        file_path,
                        date_shamsi,
                        contract_number,
                        seller_json,
                        buyer_json,
                        car_json,
                        deal_json,
                        checkpoint_image,
                        is_payed
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        data["buyer"]["national_code"],
                        data["seller"]["national_code"],
                        docx_path,
                        data["deal_info"]["deal_date"],
                        int(contract_number),
                        seller_json,
                        buyer_json,
                        car_json,
                        deal_json,
                        checkpoint_path,
                        data["deal_info"]["is_payed"]
                    ),
                )
                conn.commit()

            self.setup_contract_number()
            QMessageBox.information(self, "بایگانی موفق", "قرارداد با موفقیت بایگانی شد.")


        except Exception as e:
            QMessageBox.critical(self, "خطا", f"در فرآیند بایگانی خطایی رخ داد:\n{str(e)}")
          
    def open_search_window(self):
        self.search_window = SearchApp(self.db)
        self.search_window.show()

        