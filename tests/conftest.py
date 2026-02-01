import os
import pytest
from database import DatabaseManager

TEST_DB = "settings_test.db"

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    # حذف دیتابیس تست قبلی
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

    # ساخت دیتابیس جدید
    db = DatabaseManager(TEST_DB)

    # برگرداندن مسیر دیتابیس برای تست‌ها
    return TEST_DB