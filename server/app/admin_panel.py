# server/app/admin_panel.py
#
# A small server-rendered web panel (single admin account, password from
# LICENSE_ADMIN_PASSWORD) for managing customers: create accounts, set/
# extend subscription days, enable/disable, toggle auto-backup, and browse/
# download uploaded backups for restore.

import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from . import auth, config
from .database import get_db
from .models import Customer, Backup

router = APIRouter(prefix="/admin")

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

SESSION_COOKIE = "admin_session"


def require_admin(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    payload = auth.verify_token(token) if token else None
    if not payload or not payload.get("admin"):
        raise HTTPException(303, headers={"Location": "/admin/login"})
    return True


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"error": None})


@router.post("/login")
def login_submit(request: Request, password: str = Form(...)):
    if password != config.ADMIN_PASSWORD:
        return templates.TemplateResponse(
            request, "login.html", {"error": "رمز اشتباه است"}, status_code=401
        )
    token = auth.sign_token({"admin": True}, config.ADMIN_SESSION_LIFETIME_SECONDS)
    resp = RedirectResponse("/admin", status_code=303)
    resp.set_cookie(SESSION_COOKIE, token, httponly=True, max_age=config.ADMIN_SESSION_LIFETIME_SECONDS)
    return resp


@router.get("/logout")
def logout():
    resp = RedirectResponse("/admin/login", status_code=303)
    resp.delete_cookie(SESSION_COOKIE)
    return resp


@router.get("", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db), _=Depends(require_admin)):
    customers = db.query(Customer).order_by(Customer.created_at.desc()).all()
    now = datetime.now(timezone.utc)

    def days_left(c: Customer):
        if not c.subscription_expires_at:
            return None
        expires = c.subscription_expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return (expires - now).days

    rows = [{"c": c, "days_left": days_left(c), "valid": c.is_subscription_valid()} for c in customers]
    return templates.TemplateResponse(request, "dashboard.html", {"rows": rows})


@router.post("/customers/new")
def create_customer(
    username: str = Form(...),
    password: str = Form(...),
    display_name: str = Form(""),
    days: int = Form(30),
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    username = username.strip()
    if not username or not password:
        raise HTTPException(400, "نام کاربری و رمز الزامی است")
    if db.query(Customer).filter(Customer.username == username).first():
        raise HTTPException(400, "این نام کاربری قبلاً ثبت شده است")

    customer = Customer(
        username=username,
        password_hash=auth.hash_password(password),
        display_name=display_name.strip() or username,
        is_active=True,
        subscription_expires_at=datetime.now(timezone.utc) + timedelta(days=days),
        auto_backup_enabled=False,
    )
    db.add(customer)
    db.commit()
    return RedirectResponse("/admin", status_code=303)


@router.post("/customers/{customer_id}/extend")
def extend_subscription(
    customer_id: int,
    days: int = Form(...),
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    customer = db.query(Customer).get(customer_id)
    if not customer:
        raise HTTPException(404, "مشتری یافت نشد")

    now = datetime.now(timezone.utc)
    base = customer.subscription_expires_at or now
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    if base < now:
        base = now
    customer.subscription_expires_at = base + timedelta(days=days)
    db.commit()
    return RedirectResponse("/admin", status_code=303)


@router.post("/customers/{customer_id}/toggle-active")
def toggle_active(customer_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    customer = db.query(Customer).get(customer_id)
    if not customer:
        raise HTTPException(404, "مشتری یافت نشد")
    customer.is_active = not customer.is_active
    db.commit()
    return RedirectResponse("/admin", status_code=303)


@router.post("/customers/{customer_id}/toggle-backup")
def toggle_backup(customer_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    customer = db.query(Customer).get(customer_id)
    if not customer:
        raise HTTPException(404, "مشتری یافت نشد")
    customer.auto_backup_enabled = not customer.auto_backup_enabled
    db.commit()
    return RedirectResponse("/admin", status_code=303)


@router.post("/customers/{customer_id}/delete")
def delete_customer(customer_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    customer = db.query(Customer).get(customer_id)
    if customer:
        db.delete(customer)
        db.commit()
    return RedirectResponse("/admin", status_code=303)


@router.get("/customers/{customer_id}/backups", response_class=HTMLResponse)
def list_backups(request: Request, customer_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    customer = db.query(Customer).get(customer_id)
    if not customer:
        raise HTTPException(404, "مشتری یافت نشد")
    backups = (
        db.query(Backup)
        .filter(Backup.customer_id == customer_id)
        .order_by(Backup.created_at.desc())
        .all()
    )
    return templates.TemplateResponse(
        request, "backups.html", {"customer": customer, "backups": backups}
    )


@router.get("/backups/{backup_id}/download")
def download_backup(backup_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    backup = db.query(Backup).get(backup_id)
    if not backup:
        raise HTTPException(404, "بک‌آپ یافت نشد")
    path = os.path.join(config.BACKUPS_DIR, str(backup.customer_id), backup.filename)
    if not os.path.exists(path):
        raise HTTPException(404, "فایل بک‌آپ روی سرور یافت نشد")
    return FileResponse(path, filename=backup.filename, media_type="application/zip")
