# database/logger.py
import json
import logging
from datetime import datetime
from typing import Optional, Any, Dict

# تنظیم لاگر اصلی برنامه
main_logger = logging.getLogger(__name__)


class Logger:
    """
    کلاس لاگ‌گیری برای ثبت رویدادها در دیتابیس
    """
    
    def __init__(self, db):
        self.db = db
        self._enabled = True
    
    def set_enabled(self, enabled: bool):
        """فعال/غیرفعال کردن لاگ‌گیری"""
        self._enabled = enabled
    
    def log(self, action: str, message: str = "", data: Optional[Dict[str, Any]] = None):
        """
        ثبت لاگ در دیتابیس
        
        Parameters:
        -----------
        action : str
            نوع عملیات (مثل: archive_start, image_load, error)
        message : str
            پیام توضیحی
        data : dict, optional
            داده‌های اضافی برای ذخیره به صورت JSON
        """
        if not self._enabled:
            return
            
        try:
            # ایجاد timestamp
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # تبدیل data به JSON
            data_json = None
            if data:
                try:
                    data_json = json.dumps(data, ensure_ascii=False)
                except Exception as json_err:
                    main_logger.warning(f"Failed to serialize log data: {json_err}")
                    data_json = json.dumps({"error": str(json_err)})
            
            # ذخیره در دیتابیس
            with self.db.connect() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO logs (action, message, data_json, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (action, message, data_json, created_at)
                )
                conn.commit()
                
        except Exception as e:
            # در صورت خطا در لاگ، فقط لاگ کنسول
            main_logger.error(f"Failed to log to database: {e}")
            main_logger.info(f"Log failed - action: {action}, message: {message}")
    
    def log_error(self, action: str, error: Exception, context: Optional[Dict] = None):
        """
        ثبت خطا به صورت لاگ
        
        Parameters:
        -----------
        action : str
            عملیاتی که خطا در آن رخ داده
        error : Exception
            شیء خطا
        context : dict, optional
            اطلاعات اضافی برای دیباگ
        """
        data = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context or {}
        }
        self.log(f"error_{action}", str(error), data)
        main_logger.error(f"Error in {action}: {error}", exc_info=True)
    
    def log_info(self, action: str, message: str = "", data: Optional[Dict] = None):
        """ثبت لاگ اطلاع‌رسانی"""
        self.log(action, message, data)
        main_logger.info(f"{action}: {message}")
    
    def log_warning(self, action: str, message: str = "", data: Optional[Dict] = None):
        """ثبت لاگ هشدار"""
        self.log(f"warning_{action}", message, data)
        main_logger.warning(f"{action}: {message}")
    
    def get_logs(self, limit: int = 100, action_filter: Optional[str] = None):
        """
        دریافت لاگ‌های ذخیره شده
        
        Returns:
        --------
        list : لیست لاگ‌ها
        """
        try:
            with self.db.connect() as conn:
                cur = conn.cursor()
                
                if action_filter:
                    cur.execute("""
                        SELECT * FROM logs 
                        WHERE action LIKE ? 
                        ORDER BY created_at DESC 
                        LIMIT ?
                    """, (f"%{action_filter}%", limit))
                else:
                    cur.execute("""
                        SELECT * FROM logs 
                        ORDER BY created_at DESC 
                        LIMIT ?
                    """, (limit,))
                
                rows = cur.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            main_logger.error(f"Failed to get logs: {e}")
            return []
    
    def clear_old_logs(self, days: int = 30):
        """
        پاک کردن لاگ‌های قدیمی‌تر از تعداد روز مشخص
        
        Returns:
        --------
        int : تعداد لاگ‌های حذف شده
        """
        try:
            with self.db.connect() as conn:
                cur = conn.cursor()
                cur.execute("""
                    DELETE FROM logs 
                    WHERE julianday('now') - julianday(created_at) > ?
                """, (days,))
                deleted = cur.rowcount
                conn.commit()
                main_logger.info(f"Cleared {deleted} old logs (older than {days} days)")
                return deleted
        except Exception as e:
            main_logger.error(f"Failed to clear old logs: {e}")
            return 0