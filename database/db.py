import sqlite3
import os
import logging
from datetime import datetime
from contextlib import contextmanager
from .logger import Logger

# تنظیم لاگر
logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """خطای سفارشی دیتابیس"""
    pass


class DatabaseManager:
    def __init__(self, db_name="settings.db"):
        self.db_name = db_name
        self._ensure_db_directory()
        self._create_tables()
        self.logger = Logger(self)

    def _ensure_db_directory(self):
        """اطمینان از وجود پوشه دیتابیس"""
        try:
            db_dir = os.path.dirname(self.db_name)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create database directory: {e}")
            raise DatabaseError(f"خطا در ایجاد پوشه دیتابیس: {e}")

    @contextmanager
    def connect(self):
        """مدیریت context برای اتصال دیتابیس با commit/rollback خودکار"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_name, timeout=10)
            conn.row_factory = sqlite3.Row  # دسترسی به ستون‌ها با نام
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise DatabaseError(f"خطا در دیتابیس: {e}")
        finally:
            if conn:
                conn.close()

    def _create_tables(self):
        """ایجاد جداول مورد نیاز در دیتابیس"""
        try:
            with self.connect() as conn:
                cur = conn.cursor()

                # جدول تنظیمات
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS settings (
                        key TEXT PRIMARY KEY,
                        value TEXT,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # جدول قراردادها
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS contracts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        buyer_id TEXT,
                        seller_id TEXT,
                        file_path TEXT,
                        date_shamsi TEXT,
                        contract_number INTEGER UNIQUE,
                        seller_json TEXT,
                        buyer_json TEXT,
                        car_json TEXT,
                        deal_json TEXT,
                        checkpoint_image TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # جدول لاگ‌ها
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        action TEXT,
                        message TEXT,
                        data_json TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # جدول شمارنده برای شماره قرارداد
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS counters (
                        key TEXT PRIMARY KEY,
                        value INTEGER,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # اگر مقدار اولیه وجود ندارد، مقدار 10000 بگذار
                cur.execute("""
                    INSERT OR IGNORE INTO counters (key, value)
                    VALUES ('contract_number', 10000)
                """)

                # ایجاد ایندکس‌ها برای بهبود عملکرد
                cur.execute("CREATE INDEX IF NOT EXISTS idx_contracts_number ON contracts(contract_number)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_contracts_buyer_id ON contracts(buyer_id)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_contracts_seller_id ON contracts(seller_id)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_contracts_date ON contracts(date_shamsi)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_logs_created_at ON logs(created_at)")

                logger.info("Database tables created successfully")

        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise DatabaseError(f"خطا در ایجاد جداول دیتابیس: {e}")

    def get_next_contract_number(self, increment=True):
        """
        دریافت شماره قرارداد بعدی
        
        Parameters:
        -----------
        increment : bool
            اگر True باشد، شمارنده را افزایش می‌دهد
            اگر False باشد، فقط مقدار فعلی را برمی‌گرداند
            
        Returns:
        --------
        int : شماره قرارداد بعدی
        """
        try:
            with self.connect() as conn:
                cur = conn.cursor()
                
                if increment:
                    # افزایش شمارنده (atomic operation)
                    cur.execute("""
                        UPDATE counters 
                        SET value = value + 1 
                        WHERE key = 'contract_number'
                        RETURNING value
                    """)
                    row = cur.fetchone()
                    
                    if row and row['value']:
                        return row['value']
                    
                    # اگر RETURNING پشتیبانی نشد (SQLite قدیمی)
                    cur.execute("SELECT value FROM counters WHERE key='contract_number'")
                    row = cur.fetchone()
                    current = row['value'] if row else 10000
                    next_num = current + 1
                    cur.execute("UPDATE counters SET value=? WHERE key='contract_number'", (next_num,))
                    return next_num
                else:
                    # فقط مقدار فعلی را برگردان
                    cur.execute("SELECT value FROM counters WHERE key='contract_number'")
                    row = cur.fetchone()
                    return row['value'] if row else 10000
                    
        except Exception as e:
            logger.error(f"Failed to get next contract number: {e}")
            raise DatabaseError(f"خطا در دریافت شماره قرارداد: {e}")

    def save_contract(self, buyer_id, seller_id, file_path, date_shamsi,
                      seller_json, buyer_json, car_json, deal_json, checkpoint_image):
        """
        ذخیره قرارداد جدید در دیتابیس
        
        Returns:
        --------
        int : شماره قرارداد ذخیره شده
        """
        try:
            # اول شماره قرارداد را بگیر
            contract_number = self.get_next_contract_number(increment=True)
            
            with self.connect() as conn:
                cur = conn.cursor()
                
                cur.execute("""
                    INSERT INTO contracts (
                        buyer_id, seller_id, file_path, date_shamsi,
                        contract_number, seller_json, buyer_json,
                        car_json, deal_json, checkpoint_image
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    buyer_id, seller_id, file_path, date_shamsi,
                    contract_number, seller_json, buyer_json,
                    car_json, deal_json, checkpoint_image
                ))
                
                logger.info(f"Contract saved successfully: {contract_number}")
                return contract_number
                
        except sqlite3.IntegrityError as e:
            logger.error(f"Duplicate contract number: {e}")
            raise DatabaseError(f"شماره قرارداد تکراری است: {e}")
        except Exception as e:
            logger.error(f"Failed to save contract: {e}")
            raise DatabaseError(f"خطا در ذخیره قرارداد: {e}")

    def get_contract(self, contract_number):
        """
        دریافت اطلاعات یک قرارداد بر اساس شماره
        
        Returns:
        --------
        dict or None : اطلاعات قرارداد
        """
        try:
            with self.connect() as conn:
                cur = conn.cursor()
                cur.execute("SELECT * FROM contracts WHERE contract_number = ?", (contract_number,))
                row = cur.fetchone()
                
                if row:
                    return dict(row)
                return None
                
        except Exception as e:
            logger.error(f"Failed to get contract {contract_number}: {e}")
            raise DatabaseError(f"خطا در دریافت قرارداد: {e}")

    def get_all_contracts(self, limit=100, offset=0):
        """
        دریافت لیست قراردادها با صفحه‌بندی
        
        Returns:
        --------
        list : لیست قراردادها
        """
        try:
            with self.connect() as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT contract_number, buyer_id, seller_id, file_path, date_shamsi, created_at
                    FROM contracts 
                    ORDER BY contract_number DESC 
                    LIMIT ? OFFSET ?
                """, (limit, offset))
                
                return [dict(row) for row in cur.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to get contracts: {e}")
            raise DatabaseError(f"خطا در دریافت لیست قراردادها: {e}")

    def delete_contract(self, contract_number):
        """
        حذف قرارداد از دیتابیس
        
        Returns:
        --------
        bool : موفقیت آمیز بودن عملیات
        """
        try:
            with self.connect() as conn:
                cur = conn.cursor()
                cur.execute("DELETE FROM contracts WHERE contract_number = ?", (contract_number,))
                
                if cur.rowcount > 0:
                    logger.info(f"Contract {contract_number} deleted successfully")
                    return True
                else:
                    logger.warning(f"Contract {contract_number} not found for deletion")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to delete contract {contract_number}: {e}")
            raise DatabaseError(f"خطا در حذف قرارداد: {e}")

    def update_contract_file_path(self, contract_number, new_file_path):
        """
        به‌روزرسانی مسیر فایل قرارداد
        
        Returns:
        --------
        bool : موفقیت آمیز بودن عملیات
        """
        try:
            with self.connect() as conn:
                cur = conn.cursor()
                cur.execute("""
                    UPDATE contracts 
                    SET file_path = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE contract_number = ?
                """, (new_file_path, contract_number))
                
                success = cur.rowcount > 0
                if success:
                    logger.info(f"Contract {contract_number} file path updated")
                return success
                
        except Exception as e:
            logger.error(f"Failed to update contract {contract_number}: {e}")
            raise DatabaseError(f"خطا در به‌روزرسانی قرارداد: {e}")

    def get_setting(self, key, default=None):
        """
        دریافت یک تنظیم از دیتابیس
        
        Returns:
        --------
        str or default : مقدار تنظیم
        """
        try:
            with self.connect() as conn:
                cur = conn.cursor()
                cur.execute("SELECT value FROM settings WHERE key=?", (key,))
                row = cur.fetchone()
                return row['value'] if row else default
                
        except Exception as e:
            logger.error(f"Failed to get setting {key}: {e}")
            return default

    def set_setting(self, key, value):
        """
        ذخیره یا به‌روزرسانی یک تنظیم در دیتابیس
        """
        try:
            with self.connect() as conn:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO settings (key, value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(key) DO UPDATE SET 
                        value = excluded.value,
                        updated_at = CURRENT_TIMESTAMP
                """, (key, value))
                
                logger.info(f"Setting {key} saved")
                
        except Exception as e:
            logger.error(f"Failed to set setting {key}: {e}")
            raise DatabaseError(f"خطا در ذخیره تنظیمات: {e}")

    def get_save_path(self):
        """دریافت مسیر ذخیره قراردادها"""
        return self.get_setting('save_path')

    def set_save_path(self, path):
        """تنظیم مسیر ذخیره قراردادها"""
        self.set_setting('save_path', path)

    def get_statistics(self):
        """
        دریافت آمار کلی از دیتابیس
        
        Returns:
        --------
        dict : آمار قراردادها
        """
        try:
            with self.connect() as conn:
                cur = conn.cursor()
                
                # تعداد کل قراردادها
                cur.execute("SELECT COUNT(*) as total FROM contracts")
                total = cur.fetchone()['total']
                
                # تعداد قراردادهای امروز
                today = datetime.now().strftime("%Y-%m-%d")
                cur.execute("SELECT COUNT(*) as today FROM contracts WHERE date(created_at) = date(?)", (today,))
                today_count = cur.fetchone()['today']
                
                # آخرین قرارداد
                cur.execute("""
                    SELECT contract_number, created_at 
                    FROM contracts 
                    ORDER BY contract_number DESC 
                    LIMIT 1
                """)
                last = cur.fetchone()
                last_contract = dict(last) if last else None
                
                return {
                    'total_contracts': total,
                    'today_contracts': today_count,
                    'last_contract': last_contract
                }
                
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}

    def log(self, action, message, data_json=""):
        """ثبت لاگ (سازگاری با کلاس Logger)"""
        try:
            with self.connect() as conn:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO logs (action, message, data_json, created_at)
                    VALUES (?, ?, ?, ?)
                """, (action, message, data_json, datetime.now().isoformat()))
                
        except Exception as e:
            logger.error(f"Failed to log: {e}")