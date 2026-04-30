# database/db.py
import sqlite3
import os
import threading
import time
import json
from datetime import datetime
from contextlib import contextmanager
from .logger import Logger


class DatabaseError(Exception):
    """خطای سفارشی دیتابیس"""
    pass


class DatabaseManager:
    def __init__(self, db_name="settings.db"):
        self.db_name = db_name
        self._local = threading.local()
        self._search_cache = {}
        self._cache_ttl = 300
        self._ensure_db_directory()
        self._create_tables()
        self.logger = Logger(self)

    def _ensure_db_directory(self):
        db_dir = os.path.dirname(self.db_name)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

    @contextmanager
    def get_connection(self):
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_name, check_same_thread=False, timeout=10)
            self._local.conn.row_factory = sqlite3.Row
        
        try:
            yield self._local.conn
            self._local.conn.commit()
        except Exception as e:
            self._local.conn.rollback()
            raise e

    def connect(self):
        return self.get_connection()

    def _create_tables(self):
        with self.get_connection() as conn:
            cur = conn.cursor()

            # ---------------- Settings ----------------
            cur.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)

            # ---------------- Contracts ----------------
            # در قسمت ایجاد جدول contracts، ستون created_at رو بدون DEFAULT تعریف کن:
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
                    created_at TIMESTAMP
                )
            """)

            # اضافه کردن ستون‌های جدید اگر وجود ندارند
            cur.execute("PRAGMA table_info(contracts)")
            columns = [col[1] for col in cur.fetchall()]
            
            if "is_payed" not in columns:
                cur.execute("ALTER TABLE contracts ADD COLUMN is_payed INTEGER DEFAULT NULL")
            if "price_info" not in columns:
                cur.execute("ALTER TABLE contracts ADD COLUMN price_info TEXT DEFAULT NULL")
            if "description_text" not in columns:
                cur.execute("ALTER TABLE contracts ADD COLUMN description_text TEXT DEFAULT NULL")

            # ایجاد ایندکس‌ها
            cur.execute("CREATE INDEX IF NOT EXISTS idx_contract_number ON contracts(contract_number)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_buyer_id ON contracts(buyer_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_seller_id ON contracts(seller_id)")

            # ---------------- Logs ----------------
            cur.execute("""
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT,
                    message TEXT,
                    data_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # ---------------- Counters ----------------
            cur.execute("""
                CREATE TABLE IF NOT EXISTS counters (
                    key TEXT PRIMARY KEY,
                    value INTEGER,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                INSERT OR IGNORE INTO counters (key, value)
                VALUES ('contract_number', 10000)
            """)

            # ---------------- Sync Queue ----------------
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sync_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contract_number INTEGER UNIQUE,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()

    def get_next_contract_number(self):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT value FROM counters WHERE key='contract_number'")
            row = cur.fetchone()
            current = row['value'] if row else 10000
            next_num = current + 1
            cur.execute("UPDATE counters SET value=? WHERE key='contract_number'", (next_num,))
            conn.commit()
            return next_num

    def save_contract(self, buyer_id, seller_id, file_path, date_shamsi,
                    seller_json, buyer_json, car_json, deal_json,
                    checkpoint_image, is_payed, price_info, description_text):

        contract_number = self.get_next_contract_number()

        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO contracts (
                    buyer_id, seller_id, file_path, date_shamsi,
                    contract_number, seller_json, buyer_json,
                    car_json, deal_json, checkpoint_image,
                    is_payed, price_info, description_text
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                buyer_id, seller_id, file_path, date_shamsi,
                contract_number, seller_json, buyer_json,
                car_json, deal_json, checkpoint_image,
                is_payed, price_info, description_text
            ))
            conn.commit()

        # ========== پاک کردن کامل کش ==========
        self._clear_cache()
        
        return contract_number
   
    def search_contracts(self, name="", ncode="", dealnum=""):
        cache_key = f"{name}_{ncode}_{dealnum}"
        
        # اگه جستجوی "همه چیز" هست (name, ncode, dealnum همشون خالی)
        is_full_search = (name == "" and ncode == "" and dealnum == "")
        
        # برای جستجوی کامل، همیشه از دیتابیس بخون (کش نکن)
        if not is_full_search and cache_key in self._search_cache:
            cached_time = self._search_cache[cache_key].get('time', 0)
            if time.time() - cached_time < self._cache_ttl:
                return self._search_cache[cache_key].get('data', [])
        
        with self.get_connection() as conn:
            cur = conn.cursor()
            
            query = """
                SELECT buyer_json, seller_json, buyer_id, seller_id, contract_number,
                    file_path, is_payed, price_info, description_text,
                    COALESCE(created_at, date_shamsi, '') as created_at
                FROM contracts
                WHERE 1=1
            """
            params = []

            if name:
                query += " AND (buyer_json LIKE ? OR seller_json LIKE ?)"
                params.append(f"%{name}%")
                params.append(f"%{name}%")

            if ncode:
                query += " AND (buyer_id LIKE ? OR seller_id LIKE ?)"
                params.append(f"%{ncode}%")
                params.append(f"%{ncode}%")

            if dealnum:
                query += " AND contract_number LIKE ?"
                params.append(f"%{dealnum}%")
            
            query += " ORDER BY contract_number DESC LIMIT 500"
            
            cur.execute(query, params)
            results = [dict(row) for row in cur.fetchall()]
            
            # فقط جستجوهای فیلتردار رو کش کن (نه جستجوی کامل)
            if not is_full_search:
                self._search_cache[cache_key] = {'data': results, 'time': time.time()}
            
            return results

    def update_contract_payment(self, contract_number, is_payed):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE contracts 
                SET is_payed = ?
                WHERE contract_number = ?
            """, (is_payed, contract_number))
            conn.commit()
        self._clear_cache()
        return cur.rowcount > 0

    def get_contract_by_number(self, contract_number):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM contracts WHERE contract_number = ?", (contract_number,))
            row = cur.fetchone()
            return dict(row) if row else None

    def delete_contract(self, contract_number):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM contracts WHERE contract_number = ?", (contract_number,))
            conn.commit()
            self._clear_cache()
            return cur.rowcount > 0

    def _clear_cache(self):
        self._search_cache.clear()

    def get_setting(self, key, default=None):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT value FROM settings WHERE key=?", (key,))
            row = cur.fetchone()
            return row['value'] if row else default

    def set_setting(self, key, value):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
            """, (key, value))
            conn.commit()

    def log(self, action, message, data_json=""):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO logs (action, message, data_json, created_at)
                VALUES (?, ?, ?, ?)
            """, (action, message, data_json, datetime.now().isoformat()))
            conn.commit()

    def get_save_path(self):
        return self.get_setting('save_path')

    def set_save_path(self, path):
        self.set_setting('save_path', path)

    def get_statistics(self):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) as total FROM contracts")
            total = cur.fetchone()['total']
            cur.execute("SELECT COUNT(*) as today FROM contracts WHERE date(created_at) = date('now')")
            today = cur.fetchone()['today']
            return {"total_contracts": total, "today_contracts": today}