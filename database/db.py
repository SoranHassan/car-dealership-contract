import sqlite3
import json
from datetime import datetime
from .logger import Logger


class DatabaseManager:
    def __init__(self, db_name="settings.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_tables()
        self.logger = Logger(self)

    def create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')

        self.cursor.execute('''
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
                checkpoint_image TEXT
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT,
                message TEXT,
                data_json TEXT,
                created_at TEXT
            )
        ''')

        self.conn.commit()

    def get_save_path(self):
        self.cursor.execute("SELECT value FROM settings WHERE key='save_path'")
        row = self.cursor.fetchone()
        return row[0] if row else None

    def set_save_path(self, path):
        self.cursor.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            ('save_path', path)
        )
        self.conn.commit()
        self.logger.log("set_save_path", "مسیر ذخیره تغییر کرد", {"path": path})