import sqlite3
import os
from datetime import datetime
from .logger import Logger

class DatabaseManager:
    def __init__(self, db_name="settings.db"):
        self.db_name = db_name
        self._ensure_db_directory()
        self._create_tables()
        self.logger = Logger(self)
      
    def _ensure_db_directory(self):
        db_dir = os.path.dirname(self.db_name)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

    def connect(self):
        return sqlite3.connect(self.db_name)
 
    def _create_tables(self):
        with self.connect() as conn:
            cur = conn.cursor()

            cur.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT)""")


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
                    is_payed INTEGER)""")

            cur.execute("""
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT,
                    message TEXT,
                    data_json TEXT,
                    created_at TEXT)""")

            # جدول شمارنده برای شماره قرارداد
            cur.execute("""
                CREATE TABLE IF NOT EXISTS counters (
                    key TEXT PRIMARY KEY,
                    value INTEGER)""")

            # اگر مقدار اولیه وجود ندارد، مقدار 10000 بگذار
            cur.execute("""
                INSERT OR IGNORE INTO counters (key, value)
                VALUES ('contract_number', 10000)""")

            conn.commit()

    def get_next_contract_number(self):
        with self.connect() as conn:
            cur = conn.cursor()

            cur.execute("SELECT value FROM counters WHERE key='contract_number'")
            row = cur.fetchone()
            current = row[0]

            next_num = current + 1

            cur.execute("UPDATE counters SET value=? WHERE key='contract_number'", (next_num,))
            conn.commit()

            return next_num

    def save_contract(self, buyer_id, seller_id, file_path, date_shamsi,
                      seller_json, buyer_json, car_json, deal_json, checkpoint_image, is_payed):

        contract_number = self.get_next_contract_number()

        with self.connect() as conn:
            cur = conn.cursor()

            cur.execute("""
                INSERT INTO contracts (
                    buyer_id, seller_id, file_path, date_shamsi,
                    contract_number, seller_json, buyer_json,
                    car_json, deal_json, checkpoint_image, is_payed
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                buyer_id, seller_id, file_path, date_shamsi,
                contract_number, seller_json, buyer_json,
                car_json, deal_json, checkpoint_image, is_payed
            ))

            conn.commit()

        return contract_number

    def get_setting(self, key):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT value FROM settings WHERE key=?", (key,))
            row = cur.fetchone()
            return row[0] if row else None

    def set_setting(self, key, value):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
            """, (key, value))
            conn.commit()

    def log(self, action, message, data_json=""):

        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO logs (action, message, data_json, created_at)
                VALUES (?, ?, ?, ?)
            """, (action, message, data_json, datetime.now().isoformat()))
            conn.commit()

    def get_save_path(self):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT value FROM settings WHERE key='save_path'")
            row = cur.fetchone()
            return row[0] if row else None

    def set_save_path(self, path):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO settings (key, value)
                VALUES ('save_path', ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
            """, (path,))
            conn.commit()