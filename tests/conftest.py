# tests/conftest.py
import os
import sys
import json
import tempfile
import pytest
from pathlib import Path
from datetime import datetime

# اضافه کردن مسیر پروژه
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import DatabaseManager


@pytest.fixture
def temp_db():
    """ایجاد دیتابیس موقت برای تست"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    db = DatabaseManager(db_path)
    yield db
    
    try:
        os.unlink(db_path)
    except:
        pass


@pytest.fixture
def temp_dir():
    """ایجاد پوشه موقت"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_contract_data():
    """داده نمونه قرارداد"""
    return {
        "seller": {
            "name": "علی",
            "lname": "محمدی",
            "father": "حسین",
            "birth": "1365/01/01",
            "national_code": "1234567890",
            "national_shcode": "12345",
            "from": "تهران",
            "phone": "09123456789",
            "adress": "تهران، خیابان آزادی"
        },
        "buyer": {
            "name": "رضا",
            "lname": "کریمی",
            "father": "احمد",
            "birth": "1370/02/02",
            "national_code": "0987654321",
            "national_shcode": "54321",
            "from": "شیراز",
            "phone": "09234567890",
            "address": "شیراز، خیابان سعدی"
        },
        "car_deal": {
            "type": "پراید",
            "color": "سفید",
            "system": "دنده‌ای",
            "model": "1398",
            "body_id": "ABC123456789",
            "motor_id": "XYZ987654321",
            "kilometer": "120000",
            "pelak": "۱۲۳ - ب - ۴۵۶ - ایران ۷۸",
            "car_info": "بدون مشکل"
        },
        "deal_info": {
            "deal_date": "1402/01/15",
            "deal_time": "14:30",
            "day_respite": "7",
            "price_rial": "500,000,000",
            "price_toman": "50,000,000",
            "price_info": "نقدی",
            "description_text": "توضیحات تست",
            "deal_num": "10001",
            "is_payed": 0
        }
    }