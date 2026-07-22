# server/app/api.py
#
# REST API consumed by the desktop app (AutoGarideh) — login, periodic
# license/subscription status checks, and optional backup uploads.

import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Header, UploadFile, File
from sqlalchemy.orm import Session

from . import auth, config
from .database import get_db
from .models import Customer, Backup

router = APIRouter(prefix="/api")


def _customer_status_payload(customer: Customer) -> dict:
    return {
        "username": customer.username,
        "display_name": customer.display_name,
        "is_active": customer.is_active,
        "subscription_valid": customer.is_subscription_valid(),
        "subscription_expires_at": (
            customer.subscription_expires_at.isoformat() if customer.subscription_expires_at else None
        ),
        "auto_backup_enabled": customer.auto_backup_enabled,
    }


@router.post("/auth/login")
def login(credentials: dict, db: Session = Depends(get_db)):
    username = (credentials.get("username") or "").strip()
    password = credentials.get("password") or ""
    if not username or not password:
        raise HTTPException(400, "نام کاربری و رمز عبور الزامی است")

    customer = db.query(Customer).filter(Customer.username == username).first()
    if not customer or not auth.verify_password(password, customer.password_hash):
        raise HTTPException(401, "نام کاربری یا رمز عبور اشتباه است")

    if not customer.is_subscription_valid():
        raise HTTPException(
            403,
            "اشتراک این حساب غیرفعال یا منقضی شده است. لطفاً با پشتیبانی تماس بگیرید.",
        )

    token = auth.sign_token(
        {"sub": customer.username, "customer_id": customer.id},
        config.TOKEN_LIFETIME_SECONDS,
    )
    return {"token": token, **_customer_status_payload(customer)}


def _authenticate(authorization: str, db: Session) -> Customer:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "توکن یافت نشد")
    token = authorization.removeprefix("Bearer ").strip()
    payload = auth.verify_token(token)
    if not payload:
        raise HTTPException(401, "توکن نامعتبر یا منقضی شده است")
    customer = db.query(Customer).get(payload.get("customer_id"))
    if not customer:
        raise HTTPException(401, "حساب کاربری یافت نشد")
    return customer


@router.get("/license/status")
def license_status(authorization: str = Header(None), db: Session = Depends(get_db)):
    customer = _authenticate(authorization, db)
    if not customer.is_subscription_valid():
        raise HTTPException(403, "اشتراک این حساب غیرفعال یا منقضی شده است.")
    return _customer_status_payload(customer)


@router.post("/backup/upload")
def upload_backup(
    authorization: str = Header(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    customer = _authenticate(authorization, db)
    if not customer.is_subscription_valid():
        raise HTTPException(403, "اشتراک این حساب غیرفعال یا منقضی شده است.")
    if not customer.auto_backup_enabled:
        raise HTTPException(403, "بک‌آپ خودکار برای این حساب فعال نیست.")

    customer_dir = os.path.join(config.BACKUPS_DIR, str(customer.id))
    os.makedirs(customer_dir, exist_ok=True)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_name = f"{stamp}_{uuid.uuid4().hex[:8]}.zip"
    dest_path = os.path.join(customer_dir, safe_name)

    size = 0
    with open(dest_path, "wb") as out:
        while True:
            chunk = file.file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > config.MAX_BACKUP_SIZE_BYTES:
                out.close()
                os.remove(dest_path)
                raise HTTPException(413, "حجم فایل بک‌آپ بیش از حد مجاز است.")
            out.write(chunk)

    backup = Backup(customer_id=customer.id, filename=safe_name, size_bytes=size)
    db.add(backup)
    db.commit()

    return {"ok": True, "backup_id": backup.id, "size_bytes": size}
