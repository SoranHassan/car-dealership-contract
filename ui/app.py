import json
import sys, logging, os
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtCore import QTimer, Qt, QTime
from PySide6.QtWidgets import QMessageBox, QFileDialog, QLabel, QVBoxLayout, QMainWindow, QLineEdit, QApplication
from ui import Ui_MainWindow
from database.db import DatabaseManager
from editors.photo_editor import PhotoEditorDialog
from word import ContractGenerator  # فرض: تابع اصلی ساخت ورد
from ui import Ui_MainWindow



class App(QMainWindow):
    
    def __init__(self):
        super().__init__()

        self.db = DatabaseManager()
        self.check_first_run()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

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
        
        self.load_image("./assets/banner.jpg")  

        # ------------- Logo 
        self.logo_frame = self.ui.logo_frame
        
        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignCenter)      

        layout = QVBoxLayout(self.logo_frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.logo_label)
        
        self.load_logo("./assets/logo.png") 

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

            pixmap = QPixmap(logo_path)
            
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    110, 110,  
                    Qt.KeepAspectRatio,  
                    Qt.SmoothTransformation)
                
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
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                pixmap = pixmap.scaled(
                    self.frame.width(),
                    self.frame.height(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation)
                self.image_label.setPixmap(pixmap)
                self.image_label.setText("")  
            else:
                self.image_label.setText("خطا در بارگذاری عکس")
                self.image_label.setStyleSheet("color: red;")
        except Exception as e:
            self.image_label.setText(f"خطا: {str(e)}")
   
    def setup_contract_number(self):
        try:
            self.db.cursor.execute("SELECT MAX(contract_number) FROM contracts")
            row = self.db.cursor.fetchone()
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
        self.clear_all_fields()

        if hasattr(self, "checkpoint_image_path"):
            del self.checkpoint_image_path

    def get_data(self):

        pelak_part1 = f"{self.ui.pelak_two.text()}-{self.ui.pelak_three.text()}"
        pelak_part2 = f"{self.ui.pelak_alpha.currentText()}-{self.ui.pelak_iran.text()}"

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
                "pelak": [pelak_part1, pelak_part2],
                "car_info": self.ui.car_info.text()
            },
            "deal_info": {
                "deal_date": "",
                "deal_time": self.ui.deal_time.text(),
                "day_respite": self.ui.day_respite.text(),
                "price_rial": self.ui.price_rial.text(),
                "price_toman": self.ui.price_toman.text(),
                "price_info": self.ui.price_info.text()
            }
        }

        # 🔥 اضافه کردن نام کامل فروشنده و خریدار
        data["seller"]["fname"] = f"{data['seller']['name']} {data['seller']['lname']}"
        data["buyer"]["fname"] = f"{data['buyer']['name']} {data['buyer']['lname']}"

        return data
            
    def on_archive_btn_clicked(self):

        try:
            # شروع فرآیند
            self.db.logger.log("archive_start", "", {})

            # ۱) جمع‌آوری داده‌ها
            data = self.get_data()
            data["deal_info"]["deal_date"] = self.ui.deal_date.text()
            data["deal_info"]["deal_num"] = self.ui.deal_num.text()

            contract_number = data["deal_info"]["deal_num"]

            # ۲) ساخت temp
            root_dir = os.getcwd()
            temp_dir = os.path.join(root_dir, "temp")
            os.makedirs(temp_dir, exist_ok=True)

            # ۳) ذخیره JSON در temp
            json_path = os.path.join(temp_dir, f"contract_{contract_number}.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            self.db.logger.log(
                "archive_json_saved",
                "",
                {"json_path": json_path}
            )

            # ۴) بررسی عکس کارشناسی
            checkpoint_path = os.path.join(root_dir, "checkpoint_final.png")
            if not os.path.exists(checkpoint_path):
                self.db.logger.log(
                    "archive_error",
                    "checkpoint_not_found",
                    {}
                )
                QMessageBox.warning(self, "خطا", "تصویر کارشناسی یافت نشد.")
                return

            self.db.logger.log(
                "archive_checkpoint_found",
                "",
                {"checkpoint_path": checkpoint_path}
            )

            # ۵) ساخت فایل Word با ContractGenerator
            save_dir = self.db.get_save_path()
            generator = ContractGenerator()

            docx_path = generator.generate(
                json_path=json_path,
                checkpoint_image_path=checkpoint_path,
                output_dir=save_dir
            )

            self.db.logger.log(
                "archive_word_generated",
                "",
                {"docx_path": docx_path}
            )

            # ۶) ذخیره در دیتابیس
            seller_json = json.dumps(data["seller"], ensure_ascii=False)
            buyer_json = json.dumps(data["buyer"], ensure_ascii=False)
            car_json = json.dumps(data["car_deal"], ensure_ascii=False)
            deal_json = json.dumps(data["deal_info"], ensure_ascii=False)

            self.db.cursor.execute(
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
                    checkpoint_image
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                ),
            )
            self.db.conn.commit()

            self.db.logger.log(
                "archive_db_saved",
                "",
                {"contract_number": contract_number}
            )

            # ۷) پیام موفقیت
            QMessageBox.information(
                self,
                "بایگانی موفق",
                "قرارداد با موفقیت بایگانی شد."
            )

            self.db.logger.log(
                "archive_success",
                "",
                {"contract_number": contract_number}
            )

        except Exception as e:
            self.db.logger.log(
                "archive_exception",
                str(e),
                {}
            )
            QMessageBox.critical(
                self,
                "خطا",
                f"در فرآیند بایگانی خطایی رخ داد:\n{str(e)}"
            )

    def open_search_window(self):
        from .search import SearchApp
        self.search_window = SearchApp()
        self.search_window.show()