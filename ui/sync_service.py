import os
import json
import threading
import time
import sqlite3
import logging
import hashlib
import hmac
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable, Dict, List, Tuple

import requests
from PySide6.QtWidgets import QFileDialog, QMessageBox

# تنظیم لاگر
logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.getcwd(), "settings.db")

# ==================== تنظیمات سرور ====================
# ⚠️ این مقادیر را قبل از استفاده تنظیم کنید
SERVER_CONFIG = {
    "base_url": "http://YOUR_SERVER_IP_OR_DOMAIN:8000",  # ← این را عوض کن
    "api_key": "",  # کلید API برای احراز هویت (از سرور دریافت کنید)
    "api_secret": "",  # رمز سرویس برای امضای درخواست‌ها
    "timeout": 30,  # زمان انتظار برای پاسخ سرور (ثانیه)
    "max_retries": 3,  # حداکثر تعداد تلاش مجدد
    "retry_delay": 5,  # فاصله بین تلاش‌ها (ثانیه)
    "sync_interval": 300,  # فاصله همگام‌سازی خودکار (ثانیه - 5 دقیقه)
}

CONFIG_FILE = os.path.join(os.getcwd(), "sync_config.json")


class SyncError(Exception):
    """خطای سفارشی برای همگام‌سازی"""
    pass


class SyncService:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._stop_flag = False
        self._thread = None
        self._is_syncing = False
        self._load_local_config()
        self._session = self._create_session()

    def _create_session(self) -> requests.Session:
        """ایجاد نشست HTTP با تنظیمات امنیتی"""
        session = requests.Session()
        
        # تنظیم هدرهای پیش‌فرض
        session.headers.update({
            "User-Agent": "AutoGarideh-Sync/1.0",
            "Content-Type": "application/json",
        })
        
        # اضافه کردن کلید API اگر存在 دارد
        if SERVER_CONFIG.get("api_key"):
            session.headers.update({
                "X-API-Key": SERVER_CONFIG["api_key"]
            })
        
        return session

    def _generate_signature(self, data: str) -> str:
        """تولید امضای HMAC برای امنیت درخواست‌ها"""
        if not SERVER_CONFIG.get("api_secret"):
            return ""
        
        secret = SERVER_CONFIG["api_secret"].encode()
        return hmac.new(secret, data.encode(), hashlib.sha256).hexdigest()

    # ---------------------------------------------------------
    #  Load / Save Local Config
    # ---------------------------------------------------------
    def _load_local_config(self):
        """بارگذاری تنظیمات محلی"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
            else:
                self.config = {
                    "contracts_root": None,
                    "last_sync": None,
                    "sync_enabled": True,
                    "server_url": SERVER_CONFIG["base_url"]
                }
                self._save_local_config()
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            self.config = {
                "contracts_root": None,
                "last_sync": None,
                "sync_enabled": True,
                "server_url": SERVER_CONFIG["base_url"]
            }

    def _save_local_config(self):
        """ذخیره تنظیمات محلی"""
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    # ---------------------------------------------------------
    #  Set Contracts Root Folder
    # ---------------------------------------------------------
    def set_contracts_root(self, path: str):
        """تنظیم پوشه ریشه قراردادها"""
        if path and os.path.exists(path):
            self.config["contracts_root"] = path
            self._save_local_config()
            logger.info(f"Contracts root set to: {path}")
            return True
        return False

    def get_contracts_root(self) -> Optional[str]:
        """دریافت پوشه ریشه قراردادها"""
        return self.config.get("contracts_root")

    def is_sync_enabled(self) -> bool:
        """بررسی فعال بودن همگام‌سازی"""
        return self.config.get("sync_enabled", True)

    def set_sync_enabled(self, enabled: bool):
        """فعال/غیرفعال کردن همگام‌سازی"""
        self.config["sync_enabled"] = enabled
        self._save_local_config()
        logger.info(f"Sync enabled: {enabled}")

    # ---------------------------------------------------------
    #  API Calls
    # ---------------------------------------------------------
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """
        ارسال درخواست به سرور با قابلیت retry
        """
        if not self.is_sync_enabled():
            logger.debug("Sync is disabled, skipping request")
            return None

        url = f"{self.config.get('server_url', SERVER_CONFIG['base_url'])}{endpoint}"
        
        # تنظیم timeout
        kwargs.setdefault('timeout', SERVER_CONFIG['timeout'])
        
        # اضافه کردن امضا
        if SERVER_CONFIG.get("api_secret"):
            timestamp = str(int(time.time()))
            signature_data = f"{method}{endpoint}{timestamp}"
            signature = self._generate_signature(signature_data)
            kwargs.setdefault('headers', {})
            kwargs['headers']['X-Timestamp'] = timestamp
            kwargs['headers']['X-Signature'] = signature

        retries = 0
        last_error = None
        
        while retries < SERVER_CONFIG['max_retries']:
            try:
                response = self._session.request(method, url, **kwargs)
                
                if response.status_code == 200:
                    return response.json() if response.text else {"success": True}
                elif response.status_code == 401:
                    logger.error("Authentication failed - invalid API key")
                    return None
                elif response.status_code >= 500:
                    # خطای سرور - دوباره تلاش کن
                    retries += 1
                    time.sleep(SERVER_CONFIG['retry_delay'])
                    continue
                else:
                    logger.warning(f"Request failed: {response.status_code} - {response.text}")
                    return None
                    
            except requests.exceptions.Timeout:
                last_error = "Request timeout"
                retries += 1
                time.sleep(SERVER_CONFIG['retry_delay'])
                
            except requests.exceptions.ConnectionError:
                last_error = "Connection error"
                retries += 1
                time.sleep(SERVER_CONFIG['retry_delay'])
                
            except Exception as e:
                logger.error(f"Request error: {e}")
                return None
        
        logger.error(f"Request failed after {retries} retries: {last_error}")
        return None

    def _upload_single_contract(
        self, 
        contract_number: int, 
        buyer_id: str, 
        created_at: str, 
        file_path: str
    ) -> bool:
        """
        آپلود یک قرارداد به سرور
        """
        if not os.path.exists(file_path):
            logger.warning(f"File not found: {file_path}")
            return False

        try:
            url = f"/api/contracts/upload"
            
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

                response = self._make_request(
                    "POST", 
                    url, 
                    data=data, 
                    files=files
                )

                if response:
                    logger.info(f"Contract {contract_number} uploaded successfully")
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to upload contract {contract_number}: {e}")
            
        return False

    def _check_server_health(self) -> bool:
        """بررسی سلامت سرور"""
        try:
            response = self._make_request("GET", "/api/health")
            return response is not None
        except Exception:
            return False

    # ---------------------------------------------------------
    #  Upload Operations
    # ---------------------------------------------------------
    def initial_upload_existing_contracts(self, ask_path_callback: Callable):
        """
        بار اول: از کاربر مسیر پوشه قراردادها را می‌گیرد و همهٔ فایل‌های موجود را آپلود می‌کند.
        """
        if not self._check_server_health():
            logger.warning("Server is not reachable - skipping initial upload")
            QMessageBox.warning(
                None, 
                "خطای همگام‌سازی", 
                "سرور در دسترس نیست. همگام‌سازی بعداً انجام خواهد شد."
            )
            return

        # گرفتن مسیر پوشه اگر تنظیم نشده
        if not self.config.get("contracts_root"):
            root = ask_path_callback()
            if not root:
                logger.info("User cancelled contracts root selection")
                return
            self.set_contracts_root(root)

        root_path = self.config.get("contracts_root")
        if not root_path or not os.path.exists(root_path):
            logger.error(f"Invalid contracts root: {root_path}")
            return

        # دریافت لیست قراردادها از دیتابیس
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            cur.execute("""
                SELECT contract_number, buyer_id, file_path, date_shamsi, created_at
                FROM contracts
                ORDER BY contract_number
            """)
            rows = cur.fetchall()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to get contracts from DB: {e}")
            return

        total = len(rows)
        uploaded = 0
        
        for idx, row in enumerate(rows):
            contract_number = row['contract_number']
            buyer_id = row['buyer_id']
            created_at = row['created_at'] or row['date_shamsi']
            file_path = row['file_path']

            # ساخت مسیر مطلق
            if not os.path.isabs(file_path):
                abs_path = os.path.join(root_path, file_path)
            else:
                abs_path = file_path

            if not os.path.exists(abs_path):
                logger.warning(f"Contract file not found: {abs_path}")
                continue

            if self._upload_single_contract(
                contract_number=contract_number,
                buyer_id=buyer_id,
                created_at=created_at,
                file_path=abs_path
            ):
                uploaded += 1
            
            # آپدیت پیشرفت (اختیاری)
            if (idx + 1) % 10 == 0:
                logger.info(f"Initial upload progress: {idx+1}/{total}")

        self.config["last_sync"] = datetime.utcnow().isoformat()
        self._save_local_config()
        
        logger.info(f"Initial upload completed: {uploaded}/{total} contracts uploaded")
        
        if uploaded > 0:
            QMessageBox.information(
                None,
                "همگام‌سازی اولیه",
                f"{uploaded} قرارداد با موفقیت همگام‌سازی شد."
            )

    def upload_new_contract(self, contract_number: int):
        """
        آپلود یک قرارداد جدید (بعد از ذخیره)
        """
        if not self.is_sync_enabled():
            return

        if not self._check_server_health():
            logger.debug("Server not available - adding to queue")
            self._add_to_queue(contract_number)
            return

        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            cur.execute("""
                SELECT buyer_id, file_path, date_shamsi, created_at
                FROM contracts
                WHERE contract_number=?
            """, (contract_number,))
            row = cur.fetchone()
            conn.close()

            if not row:
                logger.warning(f"Contract {contract_number} not found in DB")
                return

            buyer_id = row['buyer_id']
            file_path = row['file_path']
            created_at = row['created_at'] or row['date_shamsi']

            # ساخت مسیر مطلق
            root_path = self.config.get("contracts_root")
            if not os.path.isabs(file_path) and root_path:
                abs_path = os.path.join(root_path, file_path)
            else:
                abs_path = file_path

            if not os.path.exists(abs_path):
                logger.warning(f"Contract file not found: {abs_path} - adding to queue")
                self._add_to_queue(contract_number)
                return

            success = self._upload_single_contract(
                contract_number=contract_number,
                buyer_id=buyer_id,
                created_at=created_at,
                file_path=abs_path
            )

            if not success:
                logger.warning(f"Failed to upload contract {contract_number} - adding to queue")
                self._add_to_queue(contract_number)

        except Exception as e:
            logger.error(f"Error in upload_new_contract: {e}")
            self._add_to_queue(contract_number)

    # ---------------------------------------------------------
    #  Queue System (Offline Support)
    # ---------------------------------------------------------
    def _add_to_queue(self, contract_number: int):
        """اضافه کردن قرارداد به صف آفلاین"""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()

            cur.execute("""
                CREATE TABLE IF NOT EXISTS sync_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contract_number INTEGER UNIQUE,
                    added_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("INSERT OR IGNORE INTO sync_queue (contract_number) VALUES (?)", (contract_number,))
            conn.commit()
            conn.close()
            
            logger.info(f"Contract {contract_number} added to sync queue")
            
        except Exception as e:
            logger.error(f"Failed to add {contract_number} to queue: {e}")

    def _process_queue(self):
        """پردازش صف آفلاین"""
        if not self.is_sync_enabled():
            return

        if self._is_syncing:
            logger.debug("Sync already in progress, skipping")
            return

        self._is_syncing = True
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            # دریافت لیست صف
            cur.execute("SELECT contract_number FROM sync_queue ORDER BY added_at")
            queue_items = cur.fetchall()
            
            if not queue_items:
                return

            logger.info(f"Processing sync queue: {len(queue_items)} items")

            root_path = self.config.get("contracts_root")
            
            for item in queue_items:
                contract_number = item['contract_number']
                
                # دریافت اطلاعات قرارداد
                cur2 = conn.cursor()
                cur2.execute("""
                    SELECT buyer_id, file_path, date_shamsi, created_at
                    FROM contracts
                    WHERE contract_number=?
                """, (contract_number,))
                row = cur2.fetchone()
                
                if not row:
                    # قرارداد وجود ندارد - حذف از صف
                    cur.execute("DELETE FROM sync_queue WHERE contract_number=?", (contract_number,))
                    conn.commit()
                    continue

                buyer_id = row['buyer_id']
                file_path = row['file_path']
                created_at = row['created_at'] or row['date_shamsi']

                # ساخت مسیر مطلق
                if not os.path.isabs(file_path) and root_path:
                    abs_path = os.path.join(root_path, file_path)
                else:
                    abs_path = file_path

                if not os.path.exists(abs_path):
                    logger.warning(f"File not found for contract {contract_number}, skipping")
                    continue

                # تلاش برای آپلود
                if self._upload_single_contract(
                    contract_number=contract_number,
                    buyer_id=buyer_id,
                    created_at=created_at,
                    file_path=abs_path
                ):
                    # حذف از صف در صورت موفقیت
                    cur.execute("DELETE FROM sync_queue WHERE contract_number=?", (contract_number,))
                    conn.commit()
                    logger.info(f"Contract {contract_number} removed from sync queue")
                else:
                    logger.warning(f"Failed to upload contract {contract_number} from queue")

            conn.close()
            
        except Exception as e:
            logger.error(f"Error processing sync queue: {e}")
        finally:
            self._is_syncing = False

    # ---------------------------------------------------------
    #  Background Sync Thread
    # ---------------------------------------------------------
    def start_background_sync(self, interval_seconds: Optional[int] = None):
        """
        شروع همگام‌سازی خودکار در پس‌زمینه
        
        Parameters:
        -----------
        interval_seconds : int, optional
            فاصله بین همگام‌سازی‌ها (پیش‌فرض: 300 ثانیه = 5 دقیقه)
        """
        if self._thread and self._thread.is_alive():
            logger.info("Background sync already running")
            return

        if interval_seconds is None:
            interval_seconds = SERVER_CONFIG['sync_interval']

        def run():
            logger.info(f"Background sync started (interval: {interval_seconds}s)")
            
            while not self._stop_flag:
                try:
                    if self.is_sync_enabled():
                        self._process_queue()
                except Exception as e:
                    logger.error(f"Background sync error: {e}")
                
                # منتظر ماندن تا وقفه بعدی
                for _ in range(interval_seconds):
                    if self._stop_flag:
                        break
                    time.sleep(1)
            
            logger.info("Background sync stopped")

        self._stop_flag = False
        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()
        logger.info("Background sync thread started")

    def stop_background_sync(self):
        """توقف همگام‌سازی خودکار"""
        self._stop_flag = True
        if self._thread:
            self._thread.join(timeout=10)
        logger.info("Background sync stopped")

    def sync_now(self) -> int:
        """
        همگام‌سازی فوری (پردازش کل صف)
        
        Returns:
        --------
        int : تعداد آیتم‌های پردازش شده
        """
        logger.info("Manual sync triggered")
        
        if not self._check_server_health():
            logger.warning("Server not available for manual sync")
            return 0
            
        self._process_queue()
        
        # شمارش آیتم‌های باقی‌مانده در صف
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM sync_queue")
            count = cur.fetchone()[0]
            conn.close()
            return count
        except Exception:
            return 0

    def get_queue_size(self) -> int:
        """دریافت تعداد آیتم‌های موجود در صف"""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM sync_queue")
            count = cur.fetchone()[0]
            conn.close()
            return count
        except Exception:
            return 0

    def clear_queue(self):
        """پاک کردن صف (برای دیباگ)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("DELETE FROM sync_queue")
            conn.commit()
            conn.close()
            logger.info("Sync queue cleared")
        except Exception as e:
            logger.error(f"Failed to clear queue: {e}")