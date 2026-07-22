# ui/license_client.py
#
# Remote, per-customer subscription enforcement — separate from (and in
# addition to) the existing one-time hardware-activation-code system in
# license_manager.py. This talks to the licensing server (server/) so a
# customer's access can be granted/revoked/day-counted from the web admin
# panel, and cannot be bypassed by editing local files: the server's
# is_active/subscription_expires_at is the only source of truth, and the
# client is required to successfully re-check with it periodically.
#
# ⚠️ Set LICENSE_SERVER_URL before shipping a build to a customer. Leave it
# empty ("") to disable remote subscription enforcement entirely — the app
# then behaves exactly as it did before this feature existed (useful during
# development, or for installs that don't use the subscription system).
LICENSE_SERVER_URL = ""  # e.g. "https://autogarideh-license.up.railway.app"

# How long the app can keep running on a cached, previously-successful
# server check before it MUST reach the server again. This is the offline
# grace window — long enough to tolerate a bad internet day, short enough
# that revoking a customer on the server actually takes effect soon after.
OFFLINE_GRACE_HOURS = 72

import io
import os
import json
import zipfile
import logging
from datetime import datetime, timezone, timedelta

import requests

logger = logging.getLogger(__name__)

CACHE_SETTING_KEY = "license_cache"


class LicenseClient:
    def __init__(self, db):
        self.db = db  # database.db.DatabaseManager — reused for local cache storage

    # ------------------------------------------------------------------ #
    def is_enabled(self) -> bool:
        return bool(LICENSE_SERVER_URL)

    def _load_cache(self) -> dict:
        raw = self.db.get_setting(CACHE_SETTING_KEY)
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except (ValueError, TypeError):
            return {}

    def _save_cache(self, cache: dict):
        self.db.set_setting(CACHE_SETTING_KEY, json.dumps(cache, ensure_ascii=False))

    # ------------------------------------------------------------------ #
    def login(self, username: str, password: str) -> tuple[bool, str]:
        """Authenticate with the server and cache the result. Returns
        (success, message)."""
        try:
            resp = requests.post(
                f"{LICENSE_SERVER_URL}/api/auth/login",
                json={"username": username, "password": password},
                timeout=15,
            )
        except requests.RequestException as e:
            return False, f"اتصال به سرور برقرار نشد: {e}"

        if resp.status_code != 200:
            try:
                message = resp.json().get("detail", "ورود ناموفق بود")
            except ValueError:
                message = "ورود ناموفق بود"
            return False, message

        data = resp.json()
        cache = {
            "token": data["token"],
            "username": data["username"],
            "last_online_check": datetime.now(timezone.utc).isoformat(),
            "subscription_expires_at": data.get("subscription_expires_at"),
            "auto_backup_enabled": data.get("auto_backup_enabled", False),
        }
        self._save_cache(cache)
        return True, "ورود موفق"

    # ------------------------------------------------------------------ #
    def check_license(self) -> tuple[bool, str]:
        """Returns (is_valid, message). Tries the server first; falls back
        to the cached result if the server is unreachable, but only within
        the offline grace window."""
        if not self.is_enabled():
            return True, ""

        cache = self._load_cache()
        token = cache.get("token")

        if token:
            try:
                resp = requests.get(
                    f"{LICENSE_SERVER_URL}/api/license/status",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    cache["last_online_check"] = datetime.now(timezone.utc).isoformat()
                    cache["subscription_expires_at"] = data.get("subscription_expires_at")
                    cache["auto_backup_enabled"] = data.get("auto_backup_enabled", False)
                    self._save_cache(cache)
                    return True, ""
                # Server explicitly says no (expired/deactivated/bad token):
                # this always wins over any local cache.
                try:
                    message = resp.json().get("detail", "اشتراک نامعتبر است")
                except ValueError:
                    message = "اشتراک نامعتبر است"
                return False, message
            except requests.RequestException:
                pass  # fall through to offline grace-period check below

        # Server unreachable (or no token cached yet) — use the offline
        # grace period if we have a previous successful check to fall back on.
        last_check = cache.get("last_online_check")
        if not last_check:
            return False, (
                "برای فعال‌سازی نیاز به اتصال اینترنت دارید. "
                "لطفاً به اینترنت متصل شوید و دوباره وارد شوید."
            )

        try:
            last_check_dt = datetime.fromisoformat(last_check)
        except ValueError:
            return False, "اطلاعات اشتراک نامعتبر است. لطفاً دوباره وارد شوید."

        grace_deadline = last_check_dt + timedelta(hours=OFFLINE_GRACE_HOURS)
        if datetime.now(timezone.utc) <= grace_deadline:
            return True, ""

        return False, (
            "امکان تأیید اشتراک با سرور وجود ندارد و مهلت استفاده آفلاین به پایان رسیده است. "
            "لطفاً به اینترنت متصل شوید."
        )

    def logout(self):
        self.db.set_setting(CACHE_SETTING_KEY, "")

    def cached_username(self) -> str:
        return self._load_cache().get("username", "")

    # ------------------------------------------------------------------ #
    def should_backup(self) -> bool:
        return bool(self._load_cache().get("auto_backup_enabled"))

    def upload_backup(self, db_path: str, contracts_dir: str | None) -> tuple[bool, str]:
        """Zip the settings database and the contracts folder and upload
        them to the licensing server. Only actually sends anything if the
        server has auto-backup enabled for this customer (checked again
        server-side too, so a stale local flag can't force an upload)."""
        if not self.is_enabled():
            return False, "سرور اشتراک تنظیم نشده است"

        cache = self._load_cache()
        token = cache.get("token")
        if not token:
            return False, "ابتدا وارد حساب اشتراک شوید"

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            if db_path and os.path.exists(db_path):
                zf.write(db_path, arcname=os.path.basename(db_path))
            if contracts_dir and os.path.isdir(contracts_dir):
                for root, _dirs, files in os.walk(contracts_dir):
                    for name in files:
                        full_path = os.path.join(root, name)
                        arcname = os.path.join(
                            "contracts", os.path.relpath(full_path, contracts_dir)
                        )
                        zf.write(full_path, arcname=arcname)
        buffer.seek(0)

        try:
            resp = requests.post(
                f"{LICENSE_SERVER_URL}/api/backup/upload",
                headers={"Authorization": f"Bearer {token}"},
                files={"file": ("backup.zip", buffer, "application/zip")},
                timeout=120,
            )
        except requests.RequestException as e:
            return False, f"آپلود بک‌آپ ناموفق بود: {e}"

        if resp.status_code != 200:
            try:
                message = resp.json().get("detail", "آپلود بک‌آپ ناموفق بود")
            except ValueError:
                message = "آپلود بک‌آپ ناموفق بود"
            return False, message

        return True, "بک‌آپ با موفقیت ارسال شد"
