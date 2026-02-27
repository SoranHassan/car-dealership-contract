# ui/sync_service.py
import os
import json
import threading
import time
import sqlite3
from datetime import datetime

import requests
from PySide6.QtWidgets import QFileDialog


DB_PATH = os.path.join(os.getcwd(), "settings.db")
SERVER_BASE_URL = "http://YOUR_SERVER_IP_OR_DOMAIN:8000"   # ← این را عوض کن
CONFIG_FILE = os.path.join(os.getcwd(), "sync_config.json")


class SyncService:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._stop_flag = False
        self._thread = None
        self._load_local_config()

    # ---------------------------------------------------------
    #  Load / Save Local Config
    # ---------------------------------------------------------
    def _load_local_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        else:
            self.config = {
                "contracts_root": None,
                "last_sync": None
            }
            self._save_local_config()

    def _save_local_config(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    # ---------------------------------------------------------
    #  Set Contracts Root Folder
    # ---------------------------------------------------------
    def set_contracts_root(self, path: str):
        self.config["contracts_root"] = path
        self._save_local_config()

    # ---------------------------------------------------------
    #  Initial Upload (First Run)
    # ---------------------------------------------------------
    def initial_upload_existing_contracts(self, ask_path_callback):
        """
        بار اول: از کاربر مسیر پوشه قراردادها را می‌گیرد و همهٔ فایل‌های موجود را آپلود می‌کند.
        """
        if not self.config.get("contracts_root"):
            root = ask_path_callback()
            if not root:
                return
            self.set_contracts_root(root)

        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("""
            SELECT contract_number, buyer_id, file_path, date_shamsi
            FROM contracts
        """)
        rows = cur.fetchall()
        conn.close()

        for contract_number, buyer_id, file_path, created_at in rows:
            abs_path = file_path
            if not os.path.isabs(abs_path):
                abs_path = os.path.join(self.config["contracts_root"], file_path)

            if not os.path.exists(abs_path):
                continue

            self._upload_single_contract(
                contract_number=contract_number,
                buyer_id=buyer_id,
                created_at=created_at,
                file_path=abs_path
            )

        self.config["last_sync"] = datetime.utcnow().isoformat()
        self._save_local_config()

    # ---------------------------------------------------------
    #  Upload Single Contract
    # ---------------------------------------------------------
    def _upload_single_contract(self, contract_number, buyer_id, created_at, file_path):
        try:
            url = f"{SERVER_BASE_URL}/api/contracts/upload"

            with open(file_path, "rb") as f:
                files = {
                    "file": (
                        os.path.basename(file_path),
                        f,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                }

                data = {
                    "contract_number": str(contract_number),
                    "buyer_id": str(buyer_id),
                    "created_at": created_at if created_at else datetime.utcnow().isoformat()
                }

                resp = requests.post(url, data=data, files=files, timeout=10)

                if resp.status_code == 200:
                    return True

        except Exception:
            pass

        return False

    # ---------------------------------------------------------
    #  Upload New Contract (Called After Save)
    # ---------------------------------------------------------
    def upload_new_contract(self, contract_number):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("""
            SELECT buyer_id, file_path, date_shamsi
            FROM contracts
            WHERE contract_number=?
        """, (contract_number,))
        row = cur.fetchone()
        conn.close()

        if not row:
            return

        buyer_id, file_path, created_at = row

        abs_path = file_path
        if not os.path.isabs(abs_path):
            abs_path = os.path.join(self.config.get("contracts_root") or "", file_path)

        if not os.path.exists(abs_path):
            self._add_to_queue(contract_number)
            return

        ok = self._upload_single_contract(
            contract_number=contract_number,
            buyer_id=buyer_id,
            created_at=created_at,
            file_path=abs_path
        )

        if not ok:
            self._add_to_queue(contract_number)

    # ---------------------------------------------------------
    #  Queue System (Offline Support)
    # ---------------------------------------------------------
    def _add_to_queue(self, contract_number):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS sync_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contract_number TEXT UNIQUE
            )
        """)

        cur.execute("INSERT OR IGNORE INTO sync_queue (contract_number) VALUES (?)", (contract_number,))
        conn.commit()
        conn.close()

    def _process_queue(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        cur.execute("SELECT contract_number FROM sync_queue")
        rows = cur.fetchall()

        for (contract_number,) in rows:
            conn2 = sqlite3.connect(self.db_path)
            cur2 = conn2.cursor()

            cur2.execute("""
                SELECT buyer_id, file_path, date_shamsi
                FROM contracts
                WHERE contract_number=?
            """, (contract_number,))
            row = cur2.fetchone()
            conn2.close()

            if not row:
                continue

            buyer_id, file_path, created_at = row

            abs_path = file_path
            if not os.path.isabs(abs_path):
                abs_path = os.path.join(self.config.get("contracts_root") or "", file_path)

            if not os.path.exists(abs_path):
                continue

            ok = self._upload_single_contract(
                contract_number=contract_number,
                buyer_id=buyer_id,
                created_at=created_at,
                file_path=abs_path
            )

            if ok:
                cur.execute("DELETE FROM sync_queue WHERE contract_number=?", (contract_number,))
                conn.commit()

        conn.close()

    # ---------------------------------------------------------
    #  Background Sync Thread
    # ---------------------------------------------------------
    def start_background_sync(self, interval_seconds=300):
        if self._thread and self._thread.is_alive():
            return

        def run():
            while not self._stop_flag:
                try:
                    self._process_queue()
                except Exception:
                    pass
                time.sleep(interval_seconds)

        self._stop_flag = False
        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()

    def stop_background_sync(self):
        self._stop_flag = True