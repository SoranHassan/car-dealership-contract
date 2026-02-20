import win32com.client as win32
import os
import json
import shutil
import tempfile
from persiantools.jdatetime import JalaliDate
import sys

def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(relative_path)

class ContractGenerator:

    def __init__(self):
        self.word_template = resource_path("./assets/AG.docx")

    def generate(self, json_path, checkpoint_image_path, output_dir):
        """
        json_path: مسیر فایل JSON داخل temp
        checkpoint_image_path: مسیر عکس کارشناسی
        output_dir: مسیر ذخیره فایل نهایی (مسیر انتخاب‌شده توسط کاربر)
        """

        # --- ۱) خواندن JSON ---
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # تبدیل ساختار nested به flat
        flat = self.flatten_data(data)

        # --- ۲) ساخت نام فایل خروجی ---
        buyer_ncode = flat.get("buyer_ncode", "unknown")
        seller_ncode = flat.get("seller_ncode", "unknown")
        contract_number = flat.get("deal_num", "unknown")

        file_name = f"{buyer_ncode} - {seller_ncode} - {contract_number}.docx"

                # --- ساخت پوشه بر اساس تاریخ شمسی ---
        date_folder = flat.get("deal_date", "unknown").replace("/", "-")
        output_dir = os.path.join(output_dir, date_folder)
        os.makedirs(output_dir, exist_ok=True)

        # مسیر نهایی فایل
        final_output = os.path.join(output_dir, file_name)

        # --- ۴) ساخت پوشه موقت ---
        temp_dir = tempfile.mkdtemp()
        temp_output = os.path.join(temp_dir, "temp_output.docx")

        # --- ۵) باز کردن Word ---
        word = win32.Dispatch("Word.Application")
        word.Visible = False
        doc = word.Documents.Open(os.path.abspath(self.word_template))

        # --- ۶) پردازش Shape ها ---
        for shape in doc.Shapes:
            if shape.TextFrame.HasText:
                rng = shape.TextFrame.TextRange
                text = rng.Text
                

                # --- جایگذاری عکس کارشناسی ---
                if "checkpoint_img" in text:
                    rng.Text = ""

                    if os.path.exists(checkpoint_image_path):
                        shape.Fill.Visible = True
                        shape.Fill.UserPicture(checkpoint_image_path)
                        shape.Fill.Transparency = 0
                        shape.Fill.TextureTile = False
                        shape.LockAspectRatio = False

                    continue

                if "paid_stamp" in text:
                    rng.Text = ""

                    # فقط اگر پرداخت شده باشد
                    print("IS PAYED VALUE:", flat.get("is_payed"))
                    if flat.get("is_payed") in [1, "1", True]:
                        stamp_path = os.path.abspath(resource_path("./assets/true.png"))
                        if os.path.exists(stamp_path):
                            shape.Fill.Visible = True
                            shape.Fill.UserPicture(stamp_path)
                            shape.Fill.Transparency = 0
                            shape.Fill.TextureTile = False
                            shape.LockAspectRatio = False

                    # چه پرداخت شده باشد چه نه، دیگر متن placeholder را نمی‌خواهیم
                    continue

                # --- جایگزینی متن‌ها ---
                for key, value in flat.items():
                    if key in text:
                        text = text.replace(key, str(value))

                rng.Text = text
                

        # --- ۷) ذخیره در temp ---
        doc.SaveAs(temp_output)
        doc.Close()
        word.Quit()

        # --- ۸) انتقال به مسیر نهایی ---
        if os.path.exists(final_output):
            try:
                os.remove(final_output)
            except:
                pass

        shutil.move(temp_output, final_output)

        return final_output

    def flatten_data(self, data):
        flat = {}

        # -------------------------
        #   SELLER (مطابق Word)
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
        #   BUYER (مطابق Word)
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
        #   CAR (مطابق Word)
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
        #   DEAL INFO (مطابق Word)
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
        flat["is_payed"] = data["deal_info"].get("is_payed", 0)

        return flat