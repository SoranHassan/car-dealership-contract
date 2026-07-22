# server/app/config.py
#
# All configuration comes from environment variables so nothing sensitive
# (admin password, signing secret) ever lives in source control.

import os
import secrets

# Where the SQLite DB and uploaded backups live. On Railway/Render, point
# this at a mounted persistent volume (e.g. "/data") so it survives deploys.
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "data"))
os.makedirs(DATA_DIR, exist_ok=True)

DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{os.path.join(DATA_DIR, 'licensing.db')}")

BACKUPS_DIR = os.path.join(DATA_DIR, "backups")
os.makedirs(BACKUPS_DIR, exist_ok=True)

# Secret used to HMAC-sign client license tokens and admin-panel session
# cookies. MUST be set explicitly in production (Railway/Render env vars);
# a random one is generated for local/dev runs so it at least still works,
# but every server restart would invalidate existing tokens/sessions.
SECRET_KEY = os.environ.get("LICENSE_SERVER_SECRET")
if not SECRET_KEY:
    SECRET_KEY = secrets.token_hex(32)
    print(
        "WARNING: LICENSE_SERVER_SECRET not set — using a random secret for "
        "this process only. Set it explicitly in production or every "
        "restart invalidates all client tokens and admin sessions."
    )

# The password for the single admin account that manages customers via the
# web panel (https://your-server/admin). MUST be set in production.
ADMIN_PASSWORD = os.environ.get("LICENSE_ADMIN_PASSWORD", "change-me")

# How long a client license token stays valid without contacting the server
# again. This is the offline grace period: the desktop app can keep running
# on a cached token for up to this long, but must successfully re-validate
# with the server before it expires, or it locks itself.
TOKEN_LIFETIME_SECONDS = int(os.environ.get("TOKEN_LIFETIME_SECONDS", str(3 * 24 * 3600)))  # 3 days

# Admin panel session cookie lifetime.
ADMIN_SESSION_LIFETIME_SECONDS = 12 * 3600

MAX_BACKUP_SIZE_BYTES = int(os.environ.get("MAX_BACKUP_SIZE_BYTES", str(200 * 1024 * 1024)))  # 200 MB
