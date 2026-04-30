# word/generator.py
import win32com.client as win32
import os
import json
import shutil
import tempfile
import logging
import time
import threading
from persiantools.jdatetime import JalaliDate
import sys

logger = logging.getLogger(__name__)


def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(relative_path)


class ContractGeneratorError(Exception):
    pass


class ContractGenerator:
    _word_app = None
    _word_app_lock = threading.Lock()
    
    def __init__(self):
        self.word_template = resource_path("./assets/AG.docx")
        self._check_template_exists()

    @classmethod
    def get_word_app(cls):
        with cls._word_app_lock:
            if cls._word_app is not None:
                try:
                    _ = cls._word_app.Visible
                    return cls._word_app
                except:
                    cls._word_app = None
            
            try:
                cls._word_app = win32.Dispatch("Word.Application")
                cls._word_app.Visible = False
                cls._word_app.DisplayAlerts = False
                cls._word_app.ScreenUpdating = False
                logger.info("Word Application initialized and cached")
            except Exception as e:
                raise ContractGeneratorError(f"Microsoft Word not installed: {e}")
            
            return cls._word_app

    def _check_template_exists(self):
        if not os.path.exists(self.word_template):
            raise ContractGeneratorError(f"Template not found: {self.word_template}")

    def generate(self, json_path, checkpoint_image_path, output_dir):
        doc = None
        temp_dir = None
        
        try:
            start_time = time.time()
            
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            flat = self.flatten_data(data)

            buyer_ncode = flat.get("buyer_ncode", "unknown")
            seller_ncode = flat.get("seller_ncode", "unknown")
            contract_number = flat.get("deal_num", "unknown")
            file_name = f"{buyer_ncode} - {seller_ncode} - {contract_number}.docx"

            date_folder = flat.get("deal_date", "unknown").replace("/", "-")
            final_output_dir = os.path.join(output_dir, date_folder)
            os.makedirs(final_output_dir, exist_ok=True)
            final_output = os.path.join(final_output_dir, file_name)

            temp_dir = tempfile.mkdtemp(prefix="contract_gen_")
            temp_output = os.path.join(temp_dir, "temp_output.docx")

            word = self.get_word_app()
            doc = word.Documents.Open(os.path.abspath(self.word_template))

            # =========================================================
            # پردازش Shape ها (حفظ کامل قالب)
            # =========================================================
            for shape in doc.Shapes:
                if not shape.TextFrame.HasText:
                    continue
                    
                rng = shape.TextFrame.TextRange
                original_text = rng.Text
                
                if not original_text:
                    continue

                new_text = original_text
                
                # ۱) عکس کارشناسی (بدون حذف متن اطراف)
                if "checkpoint_img" in new_text:
                    if os.path.exists(checkpoint_image_path):
                        try:
                            shape.Fill.Visible = True
                            shape.Fill.UserPicture(checkpoint_image_path)
                            shape.Fill.Transparency = 0
                            shape.Fill.TextureTile = False
                            shape.LockAspectRatio = False
                        except Exception as img_error:
                            logger.warning(f"Failed to place image: {img_error}")
                    # فقط تگ checkpoint_img رو حذف کن
                    new_text = new_text.replace("checkpoint_img", "")
                    rng.Text = new_text
                    continue

                # ۲) مهر پرداخت (جایگزینی)
                if "paid_stamp" in new_text:
                    status = "پرداخت شد" if flat.get("is_payed") in [1, "1", True] else "پرداخت نشد"
                    new_text = new_text.replace("paid_stamp", status)
                    rng.Text = new_text
                    continue

                # ۳) جایگزینی سایر متغیرها
                changed = False
                for key, value in flat.items():
                    placeholder = key
                    if placeholder in new_text:
                        new_text = new_text.replace(placeholder, str(value))
                        changed = True
                
                if changed:
                    rng.Text = new_text

            # =========================================================
            # ذخیره فایل
            # =========================================================
            doc.SaveAs(temp_output)
            doc.Close()
            
            time.sleep(0.5)

            if os.path.exists(final_output):
                try:
                    os.remove(final_output)
                except:
                    pass

            shutil.copy2(temp_output, final_output)
            
            try:
                os.remove(temp_output)
            except:
                pass

            logger.info(f"Contract generated in {time.time() - start_time:.2f}s: {final_output}")
            return final_output

        except Exception as e:
            logger.error(f"Error in generate: {e}")
            raise ContractGeneratorError(f"خطا در تولید قرارداد: {str(e)}")
            
        finally:
            try:
                if doc is not None:
                    doc.Close(SaveChanges=False)
            except:
                pass
            
            try:
                if temp_dir and os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
            except:
                pass

    def flatten_data(self, data):
        flat = {}

        # Seller
        flat["seller_birth"] = data["seller"].get("birth", "")
        flat["seller_fname"] = f"{data['seller'].get('name', '')} {data['seller'].get('lname', '')}"
        flat["seller_ncode"] = data["seller"].get("national_code", "")
        flat["seller_shcode"] = data["seller"].get("national_shcode", "")
        flat["seller_from"] = data["seller"].get("from", "")
        flat["seller_phone"] = data["seller"].get("phone", "")
        flat["seller_adress"] = data["seller"].get("adress", "")
        flat["seller_father"] = data["seller"].get("father", "")

        # Buyer
        flat["buyer_birth"] = data["buyer"].get("birth", "")
        flat["buyer_fname"] = f"{data['buyer'].get('name', '')} {data['buyer'].get('lname', '')}"
        flat["buyer_ncode"] = data["buyer"].get("national_code", "")
        flat["buyer_shcode"] = data["buyer"].get("national_shcode", "")
        flat["buyer_from"] = data["buyer"].get("from", "")
        flat["buyer_phone"] = data["buyer"].get("phone", "")
        flat["buyer_adress"] = data["buyer"].get("address", "")
        flat["buyer_father"] = data["buyer"].get("father", "")

        # Car
        flat["car_type"] = data["car_deal"].get("type", "")
        flat["car_color"] = data["car_deal"].get("color", "")
        flat["car_system"] = data["car_deal"].get("system", "")
        flat["car_model"] = data["car_deal"].get("model", "")
        flat["body_id"] = data["car_deal"].get("body_id", "")
        flat["motor_id"] = data["car_deal"].get("motor_id", "")
        flat["car_kilometer"] = data["car_deal"].get("kilometer", "")
        flat["pelak"] = data["car_deal"].get("pelak", "")
        flat["car_info"] = data["car_deal"].get("car_info", "")

        # Deal Info
        flat["deal_time"] = data["deal_info"].get("deal_time", "")
        flat["day_respite"] = data["deal_info"].get("day_respite", "")
        flat["price_rial"] = data["deal_info"].get("price_rial", "")
        flat["price_toman"] = data["deal_info"].get("price_toman", "")
        flat["price_info"] = data["deal_info"].get("price_info", "")
        flat["description_text"] = data["deal_info"].get("description_text", "")
        flat["deal_date"] = JalaliDate.today().strftime("%Y/%m/%d")
        flat["deal_num"] = data["deal_info"].get("deal_num", "")
        
        is_payed = data["deal_info"].get("is_payed")
        flat["is_payed"] = 1 if is_payed in [1, "1", True] else 0

        return flat


def generate_contract(json_path, checkpoint_image_path, output_dir):
    """تابع کمکی برای تولید قرارداد"""
    generator = ContractGenerator()
    return generator.generate(json_path, checkpoint_image_path, output_dir)