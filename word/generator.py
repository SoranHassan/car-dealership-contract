import win32com.client as win32
import os
import json
import shutil
import tempfile
import logging
from persiantools.jdatetime import JalaliDate
import sys

# تنظیم لاگر
logger = logging.getLogger(__name__)


def resource_path(relative_path):
    """دریافت مسیر فایل در حالت 개발 و بسته exe"""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(relative_path)


class ContractGeneratorError(Exception):
    """خطای سفارشی برای مشکلات تولید قرارداد"""
    pass


class ContractGenerator:
    """تولید کننده قرارداد Word از روی قالب و داده‌های JSON"""

    def __init__(self):
        self.word_template = resource_path("./assets/AG.docx")
        self._word_app = None
        self._check_word_installed()

    def _check_word_installed(self):
        """بررسی نصب بودن Microsoft Word"""
        try:
            word = win32.Dispatch("Word.Application")
            word.Quit()
            return True
        except Exception as e:
            raise ContractGeneratorError(
                "Microsoft Word بر روی سیستم نصب نیست. "
                "لطفاً ابتدا Microsoft Word را نصب کنید."
            ) from e

    def _check_template_exists(self):
        """بررسی وجود فایل قالب"""
        if not os.path.exists(self.word_template):
            raise ContractGeneratorError(
                f"فایل قالب قرارداد یافت نشد: {self.word_template}"
            )

    def generate(self, json_path, checkpoint_image_path, output_dir):
        """
        تولید فایل Word قرارداد
        
        Parameters:
        -----------
        json_path : str
            مسیر فایل JSON حاوی اطلاعات قرارداد
        checkpoint_image_path : str
            مسیر عکس کارشناسی
        output_dir : str
            مسیر پوشه خروجی برای ذخیره فایل نهایی
            
        Returns:
        --------
        str : مسیر فایل نهایی تولید شده
        
        Raises:
        -------
        ContractGeneratorError : در صورت بروز خطا در فرآیند تولید
        """
        doc = None
        temp_dir = None
        
        try:
            # بررسی وجود فایل قالب
            self._check_template_exists()
            
            # ۱) خواندن JSON
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # تبدیل ساختار nested به flat
            flat = self.flatten_data(data)

            # ۲) ساخت نام فایل خروجی
            buyer_ncode = flat.get("buyer_ncode", "unknown")
            seller_ncode = flat.get("seller_ncode", "unknown")
            contract_number = flat.get("deal_num", "unknown")

            file_name = f"{buyer_ncode} - {seller_ncode} - {contract_number}.docx"

            # ۳) ساخت پوشه بر اساس تاریخ شمسی
            date_folder = flat.get("deal_date", "unknown").replace("/", "-")
            final_output_dir = os.path.join(output_dir, date_folder)
            os.makedirs(final_output_dir, exist_ok=True)

            # مسیر نهایی فایل
            final_output = os.path.join(final_output_dir, file_name)

            # ۴) ساخت پوشه موقت
            temp_dir = tempfile.mkdtemp(prefix="contract_gen_")
            temp_output = os.path.join(temp_dir, "temp_output.docx")

            # ۵) باز کردن Word با مدیریت خطا
            logger.info(f"Opening Word and loading template: {self.word_template}")
            self._word_app = win32.Dispatch("Word.Application")
            self._word_app.Visible = False
            self._word_app.DisplayAlerts = False  # غیرفعال کردن هشدارهای Word
            
            doc = self._word_app.Documents.Open(os.path.abspath(self.word_template))

            # ۶) پردازش Shape ها (جایگذاری متن و عکس)
            processed_shapes = 0
            for shape in doc.Shapes:
                if not shape.TextFrame.HasText:
                    continue
                    
                rng = shape.TextFrame.TextRange
                text = rng.Text
                
                if not text:
                    continue

                # جایگذاری عکس کارشناسی
                if "checkpoint_img" in text:
                    rng.Text = ""
                    if os.path.exists(checkpoint_image_path):
                        try:
                            shape.Fill.Visible = True
                            shape.Fill.UserPicture(checkpoint_image_path)
                            shape.Fill.Transparency = 0
                            shape.Fill.TextureTile = False
                            shape.LockAspectRatio = False
                            logger.info(f"Checkpoint image placed: {checkpoint_image_path}")
                        except Exception as img_error:
                            logger.warning(f"Failed to place image: {img_error}")
                    else:
                        logger.warning(f"Checkpoint image not found: {checkpoint_image_path}")
                    processed_shapes += 1
                    continue

                # جایگزینی متن‌ها
                original_text = text
                for key, value in flat.items():
                    if key in text:
                        text = text.replace(key, str(value))
                
                if text != original_text:
                    rng.Text = text
                    processed_shapes += 1

            logger.info(f"Processed {processed_shapes} shapes in template")

            # ۷) ذخیره در temp
            doc.SaveAs(temp_output)
            logger.info(f"Temp file saved: {temp_output}")

            # ۸) انتقال به مسیر نهایی
            if os.path.exists(final_output):
                # ایجاد بکاپ از فایل قبلی اگر وجود داشته باشد
                backup_path = final_output + ".backup"
                try:
                    if os.path.exists(backup_path):
                        os.remove(backup_path)
                    shutil.move(final_output, backup_path)
                    logger.info(f"Existing file backed up: {backup_path}")
                except Exception as backup_error:
                    logger.warning(f"Could not create backup: {backup_error}")
                    # اگر بکاپ نشد، فایل قبلی را حذف کن
                    os.remove(final_output)

            # کپی فایل به مقصد نهایی
            shutil.copy2(temp_output, final_output)
            logger.info(f"Final file saved: {final_output}")

            return final_output

        except win32.com_error as com_error:
            logger.error(f"Word COM error: {com_error}")
            raise ContractGeneratorError(
                f"خطا در ارتباط با Microsoft Word: {str(com_error)}"
            ) from com_error
            
        except Exception as e:
            logger.error(f"Unexpected error in generate: {e}")
            raise ContractGeneratorError(
                f"خطا در تولید قرارداد: {str(e)}"
            ) from e
            
        finally:
            # ۹) بستن سند و خروج از Word (حتماً اجرا می‌شود)
            try:
                if doc is not None:
                    doc.Close(SaveChanges=False)
                    logger.debug("Document closed")
            except Exception as e:
                logger.warning(f"Error closing document: {e}")
                
            try:
                if self._word_app is not None:
                    self._word_app.Quit()
                    logger.debug("Word application closed")
            except Exception as e:
                logger.warning(f"Error quitting Word: {e}")
                
            # ۱۰) پاک کردن پوشه موقت
            try:
                if temp_dir and os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                    logger.debug(f"Temp directory removed: {temp_dir}")
            except Exception as e:
                logger.warning(f"Could not remove temp directory {temp_dir}: {e}")

    def flatten_data(self, data):
        """تبدیل داده‌های JSON تو در تو به یک دیکشنری تخت"""
        flat = {}

        # -------------------------
        #   SELLER (فروشنده)
        # -------------------------
        flat["seller_birth"] = data["seller"]["birth"]
        flat["seller_fname"] = f"{data['seller']['name']} {data['seller']['lname']}"
        flat["seller_ncode"] = data["seller"]["national_code"]
        flat["seller_shcode"] = data["seller"]["national_shcode"]
        flat["seller_from"] = data["seller"]["from"]
        flat["seller_phone"] = data["seller"]["phone"]
        flat["seller_adress"] = data["seller"]["adress"]
        flat["seller_father"] = data["seller"]["father"]

        # -------------------------
        #   BUYER (خریدار)
        # -------------------------
        flat["buyer_birth"] = data["buyer"]["birth"]
        flat["buyer_fname"] = f"{data['buyer']['name']} {data['buyer']['lname']}"
        flat["buyer_ncode"] = data["buyer"]["national_code"]
        flat["buyer_shcode"] = data["buyer"]["national_shcode"]
        flat["buyer_from"] = data["buyer"]["from"]
        flat["buyer_phone"] = data["buyer"]["phone"]
        flat["buyer_adress"] = data["buyer"]["address"]
        flat["buyer_father"] = data["buyer"]["father"]

        # -------------------------
        #   CAR (خودرو)
        # -------------------------
        flat["car_type"] = data["car_deal"]["type"]
        flat["car_color"] = data["car_deal"]["color"]
        flat["car_system"] = data["car_deal"]["system"]
        flat["car_model"] = data["car_deal"]["model"]
        flat["body_id"] = data["car_deal"]["body_id"]
        flat["motor_id"] = data["car_deal"]["motor_id"]
        flat["car_kilometer"] = data["car_deal"]["kilometer"]
        flat["pelak"] = data["car_deal"]["pelak"]
        flat["car_info"] = data["car_deal"]["car_info"]

        # -------------------------
        #   DEAL INFO (اطلاعات معامله)
        # -------------------------
        flat["deal_time"] = data["deal_info"]["deal_time"]
        flat["day_respite"] = data["deal_info"]["day_respite"]
        flat["price_rial"] = data["deal_info"]["price_rial"]
        flat["price_toman"] = data["deal_info"]["price_toman"]
        flat["price_info"] = data["deal_info"]["price_info"]

        # تاریخ شمسی واقعی با persiantools
        flat["deal_date"] = JalaliDate.today().strftime("%Y/%m/%d")

        # شماره قرارداد
        flat["deal_num"] = data["deal_info"].get("deal_num", "")

        return flat


# تابع کمکی برای استفاده آسان
def generate_contract(json_path, checkpoint_image_path, output_dir):
    """
    تابع کمکی برای تولید قرارداد
    
    Returns:
    --------
    str : مسیر فایل تولید شده
    
    Raises:
    -------
    ContractGeneratorError : اگر خطایی رخ دهد
    """
    generator = ContractGenerator()
    return generator.generate(json_path, checkpoint_image_path, output_dir)