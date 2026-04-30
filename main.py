# main.py
import sys
import os
import logging
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox, QSplashScreen
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtCore import Qt, QTimer

from ui.license_manager import license_check
from ui.app import App
from ui.sync_service import SyncService


# ==================== تنظیمات لاگ ====================
def setup_logging():
    """تنظیم سیستم لاگ‌گیری برنامه"""
    
    # ایجاد پوشه logs اگر وجود ندارد
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # نام فایل لاگ با تاریخ امروز
    log_file = log_dir / f"autogarideh_{datetime.now().strftime('%Y%m%d')}.log"
    
    # تنظیم فرمت لاگ
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # تنظیم لاگر اصلی
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler()  # همچنین در کنسول نمایش بده
        ]
    )
    
    # کاهش لاگ‌های اضافی کتابخانه‌ها
    logging.getLogger("PySide6").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info("=" * 50)
    logger.info("AutoGarideh application starting...")
    logger.info(f"Log file: {log_file}")
    
    return logger


# ==================== بررسی پایتون ====================
def check_python_version():
    """بررسی نسخه پایتون"""
    if sys.version_info < (3, 8):
        QMessageBox.critical(
            None,
            "خطای نسخه پایتون",
            "این برنامه به پایتون 3.8 یا بالاتر نیاز دارد."
        )
        return False
    return True


# ==================== ایجاد پوشه‌های مورد نیاز ====================
def create_required_directories():
    """ایجاد پوشه‌های مورد نیاز برنامه"""
    directories = [
        "temp",
        "contracts",
        "logs",
        "backups"
    ]
    
    for dir_name in directories:
        Path(dir_name).mkdir(exist_ok=True)
        print(f"Directory created/verified: {dir_name}")


# ==================== کلاس SplashScreen ====================
class SplashScreen(QSplashScreen):
    """صفحه آغازین برنامه"""
    
    def __init__(self):
        # ایجاد تصویر ساده برای splash screen
        pixmap = QPixmap(400, 200)
        pixmap.fill(Qt.white)
        
        super().__init__(pixmap)
        self.setWindowTitle("AutoGarideh")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        
        # اضافه کردن متن به splash screen
        from PySide6.QtWidgets import QLabel
        from PySide6.QtGui import QFont
        
        label = QLabel("AutoGarideh\n\nدر حال بارگذاری...", self)
        label.setAlignment(Qt.AlignCenter)
        label.setGeometry(0, 50, 400, 100)
        font = QFont("Arial", 14)
        font.setBold(True)
        label.setFont(font)
        label.setStyleSheet("color: #1B3C53;")


# ==================== تابع اصلی ====================
def main():
    """نقطه ورود اصلی برنامه"""
    
    # 1. بررسی نسخه پایتون
    if not check_python_version():
        sys.exit(1)
    
    # 2. ایجاد پوشه‌های مورد نیاز
    create_required_directories()
    
    # 3. تنظیم لاگ
    logger = setup_logging()
    
    # 4. ایجاد برنامه Qt
    app = QApplication(sys.argv)
    app.setApplicationName("AutoGarideh")
    app.setOrganizationName("AutoGarideh")
    app.setApplicationVersion("1.0.0")
    
    # تنظیم آیکون برنامه
    try:
        from ui.app import resource_path
        icon_path = resource_path("icon.ico")
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))
    except Exception as e:
        logger.warning(f"Could not set app icon: {e}")
    
    # 5. نمایش splash screen (اختیاری)
    splash = SplashScreen()
    splash.show()
    app.processEvents()
    
    # 6. بررسی لایسنس
    logger.info("Checking license...")
    if not license_check():
        logger.warning("License check failed - application exiting")
        splash.close()
        QMessageBox.critical(
            None,
            "خطای فعال‌سازی",
            "فعال‌سازی نرم‌افزار ناموفق بود.\nلطفاً با پشتیبانی تماس بگیرید."
        )
        sys.exit(1)
    
    logger.info("License check passed")
    
    # 7. راه‌اندازی سرویس همگام‌سازی
    logger.info("Initializing sync service...")
    sync_service = SyncService()
    
    # اگر قبلاً مسیر ذخیره وجود دارد، همگام‌سازی را شروع کن
    try:
        from database.db import DatabaseManager
        db = DatabaseManager()
        save_path = db.get_save_path()
        if save_path:
            sync_service.set_contracts_root(save_path)
            # شروع همگام‌سازی خودکار در پس‌زمینه
            sync_service.start_background_sync()
            logger.info(f"Sync service started with root: {save_path}")
    except Exception as e:
        logger.warning(f"Could not start sync service: {e}")
    
    # 8. ایجاد و نمایش پنجره اصلی
    logger.info("Creating main window...")
    window = App()
    
    # اضافه کردن sync_service به پنجره اصلی (برای دسترسی)
    window.sync_service = sync_service
    
    # 9. بستن splash و نمایش پنجره
    splash.finish(window)
    window.show()
    
    # 10. اگر قرارداد قبلی برای همگام‌سازی وجود دارد، در پس‌زمینه انجام شود
    if sync_service.get_queue_size() > 0:
        logger.info(f"Found {sync_service.get_queue_size()} items in sync queue")
        # با تأخیر شروع کن تا برنامه کامل بارگذاری شود
        QTimer.singleShot(5000, lambda: sync_service.sync_now())
    
    # 11. اجرا
    logger.info("Application started successfully")
    exit_code = app.exec()
    
    # 12. پاکسازی قبل از خروج
    logger.info("Application shutting down...")
    sync_service.stop_background_sync()
    
    # پاک کردن فایل‌های temp قدیمی
    try:
        import shutil
        temp_dir = Path("temp")
        if temp_dir.exists():
            # فقط فایل‌های 24 ساعت قبل را پاک کن
            for item in temp_dir.iterdir():
                if item.is_file():
                    file_age = datetime.now() - datetime.fromtimestamp(item.stat().st_mtime)
                    if file_age.days > 1:
                        item.unlink()
    except Exception as e:
        logger.warning(f"Temp cleanup on exit failed: {e}")
    
    logger.info("Application exited")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()