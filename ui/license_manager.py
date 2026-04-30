import subprocess
import os
import sys
import hashlib
import uuid as uuid_lib
from pathlib import Path
from PySide6.QtWidgets import QMessageBox, QApplication
from PySide6.QtCore import QStandardPaths

# کلید اصلی - در نسخه نهایی باید obfuscate شود
# برای امنیت بیشتر، این کلید را در فایل جداگانه یا با هش ذخیره کنید
MASTER_KEY_HASH = hashlib.sha256("@Soran9978".encode()).hexdigest()


def get_system_uuid():
    """
    دریافت شناسه یکتای سیستم
    
    روش‌های مختلف برای ویندوزهای مختلف:
    1. WMIC (ویندوزهای قدیمی)
    2. PowerShell (ویندوز 10 و 11)
    3. Fallback: ترکیبی از اطلاعات سیستم
    """
    
    # روش اول: WMIC
    try:
        result = subprocess.run(
            ["wmic", "csproduct", "get", "uuid"],
            capture_output=True,
            text=True,
            timeout=5,
            shell=True
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            if len(lines) >= 2:
                uuid_val = lines[1].strip()
                if uuid_val and uuid_val != "UUID":
                    return uuid_val
    except Exception as e:
        print(f"WMIC method failed: {e}")
    
    # روش دوم: PowerShell
    try:
        result = subprocess.run(
            ["powershell", "-Command", "Get-WmiObject -Class Win32_ComputerSystemProduct | Select-Object -ExpandProperty UUID"],
            capture_output=True,
            text=True,
            timeout=5,
            shell=True
        )
        if result.returncode == 0 and result.stdout.strip():
            uuid_val = result.stdout.strip()
            if uuid_val:
                return uuid_val
    except Exception as e:
        print(f"PowerShell method failed: {e}")
    
    # روش سوم: Fallback - ترکیبی از اطلاعات سیستم
    try:
        # ترکیب نام کامپیوتر + مدل مادربرد + MAC address
        computer_name = os.environ.get("COMPUTERNAME", "")
        
        # گرفتن مدل مادربرد
        result = subprocess.run(
            ["wmic", "baseboard", "get", "product"],
            capture_output=True,
            text=True,
            timeout=3,
            shell=True
        )
        motherboard = ""
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            if len(lines) >= 2:
                motherboard = lines[1].strip()
        
        # گرفتن MAC address اولین شبکه
        import uuid as uuid_lib
        mac = uuid_lib.getnode()
        mac_str = ':'.join(('%012X' % mac)[i:i+2] for i in range(0, 12, 2))
        
        # ترکیب و تبدیل به هش
        combined = f"{computer_name}_{motherboard}_{mac_str}"
        fallback_uuid = hashlib.md5(combined.encode()).hexdigest().upper()
        
        # فرمت UUID مانند: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
        fallback_uuid = f"{fallback_uuid[:8]}-{fallback_uuid[8:12]}-{fallback_uuid[12:16]}-{fallback_uuid[16:20]}-{fallback_uuid[20:32]}"
        
        return fallback_uuid
        
    except Exception as e:
        print(f"Fallback method failed: {e}")
        return None


def get_license_path():
    """
    دریافت مسیر ذخیره فایل لایسنس
    استفاده از AppData به جای ProgramData (نیاز به ادمین ندارد)
    """
    if getattr(sys, 'frozen', False):
        # اگر برنامه exe است
        app_data = os.environ.get("APPDATA", "")
        if app_data:
            license_dir = os.path.join(app_data, "AutoGarideh")
        else:
            # fallback به دایرکتوری برنامه
            license_dir = os.path.dirname(sys.executable)
    else:
        # اگر در حال توسعه است
        license_dir = os.path.join(os.path.expanduser("~"), ".autogarideh")
    
    os.makedirs(license_dir, exist_ok=True)
    return os.path.join(license_dir, "license.key")


def save_license(uuid_str):
    """ذخیره لایسنس در فایل (با رمزنگاری ساده)"""
    try:
        license_path = get_license_path()
        
        # ذخیره با رمزنگاری ساده (XOR با کلید ساده)
        # این فقط برای جلوگیری از تغییر دستی فایل است
        key = b"AUTOGARIDEH_SECRET_KEY_2024"
        data = uuid_str.encode()
        encrypted = bytes([data[i] ^ key[i % len(key)] for i in range(len(data))])
        
        # ذخیره به صورت base64 برای خوانایی بهتر
        import base64
        encrypted_b64 = base64.b64encode(encrypted).decode()
        
        with open(license_path, "w") as f:
            f.write(encrypted_b64)
        
        return True
    except Exception as e:
        print(f"Error saving license: {e}")
        return False


def check_license():
    """بررسی اعتبار لایسنس"""
    try:
        license_path = get_license_path()
        
        if not os.path.exists(license_path):
            return False
        
        with open(license_path, "r") as f:
            encrypted_b64 = f.read().strip()
        
        if not encrypted_b64:
            return False
        
        # رمزگشایی
        import base64
        encrypted = base64.b64decode(encrypted_b64)
        
        key = b"AUTOGARIDEH_SECRET_KEY_2024"
        decrypted_bytes = bytes([encrypted[i] ^ key[i % len(key)] for i in range(len(encrypted))])
        saved_uuid = decrypted_bytes.decode()
        
        current_uuid = get_system_uuid()
        
        return saved_uuid == current_uuid
        
    except Exception as e:
        print(f"Error checking license: {e}")
        return False


def show_error_dialog(message):
    """نمایش پیام خطا"""
    try:
        app = QApplication.instance()
        if app:
            QMessageBox.critical(None, "خطای فعال‌سازی", message)
        else:
            print(f"ERROR: {message}")
    except Exception:
        print(f"ERROR: {message}")


def show_info_dialog(message):
    """نمایش پیام اطلاعات"""
    try:
        app = QApplication.instance()
        if app:
            QMessageBox.information(None, "فعال‌سازی", message)
    except Exception:
        print(f"INFO: {message}")


def license_check():
    """
    بررسی و فعال‌سازی لایسنس
    
    Returns:
    --------
    bool : True اگر لایسنس معتبر باشد، False در غیر این صورت
    """
    
    # بررسی لایسنس موجود
    if check_license():
        return True
    
    # اگر لایسنس وجود ندارد، از کاربر بخواه
    try:
        from .license_dialog import LicenseDialog
        
        # حداکثر 3 بار تلاش
        max_attempts = 3
        for attempt in range(max_attempts):
            dialog = LicenseDialog()
            
            # تنظیم پیام راهنما بر اساس تعداد تلاش
            if attempt > 0:
                remaining = max_attempts - attempt
                dialog.set_extra_message(
                    f"\n⚠️ رمز اشتباه است!\n"
                    f"تعداد دفعات باقی‌مانده: {remaining}"
                )
            
            if dialog.exec() != 1:  # کاربر انصراف داد
                if attempt == 0:
                    show_error_dialog("برای استفاده از نرم‌افزار باید فعال‌سازی انجام شود.")
                return False
            
            key = dialog.get_key()
            
            # بررسی کلید با هش
            key_hash = hashlib.sha256(key.encode()).hexdigest()
            
            if key_hash == MASTER_KEY_HASH:
                # کلید صحیح است
                uuid_val = get_system_uuid()
                if uuid_val:
                    if save_license(uuid_val):
                        show_info_dialog("✅ نرم‌افزار با موفقیت فعال شد.")
                        return True
                    else:
                        show_error_dialog("خطا در ذخیره لایسنس.\nلطفاً با پشتیبانی تماس بگیرید.")
                        return False
                else:
                    show_error_dialog("خطا در شناسایی سیستم.\nلطفاً با پشتیبانی تماس بگیرید.")
                    return False
            else:
                # کلید اشتباه است
                continue
        
        # ۳ بار تلاش ناموفق
        show_error_dialog(
            "❌ تعداد دفعات مجاز فعال‌سازی به پایان رسید.\n"
            "لطفاً با پشتیبانی تماس بگیرید."
        )
        return False
        
    except Exception as e:
        print(f"License check error: {e}")
        show_error_dialog(f"خطا در فرآیند فعال‌سازی:\n{str(e)}")
        return False


def reset_license():
    """
    ریست کردن لایسنس (برای دیباگ یا پشتیبانی)
    این تابع باید با密码 محافظت شود
    """
    try:
        license_path = get_license_path()
        if os.path.exists(license_path):
            os.remove(license_path)
            return True
    except Exception:
        pass
    return False


def is_license_valid():
    """بررسی سریع اعتبار لایسنس بدون نمایش دیالوگ"""
    return check_license()