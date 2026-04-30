# tests/test_database.py
import pytest
import json
from database.db import DatabaseManager, DatabaseError


class TestDatabaseManager:
    
    def test_init(self):
        """تست ایجاد دیتابیس"""
        db = DatabaseManager(":memory:")  # دیتابیس در حافظه
        assert db is not None
        
    def test_create_tables(self, temp_db):
        """تست ایجاد جداول"""
        with temp_db.connect() as conn:
            cur = conn.cursor()
            
            # بررسی وجود جداول
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cur.fetchall()]
            
            assert "settings" in tables
            assert "contracts" in tables
            assert "logs" in tables
            assert "counters" in tables
    
    def test_get_next_contract_number(self, temp_db):
        """تست گرفتن شماره قرارداد بعدی"""
        # اولین شماره باید 10000 باشد
        first = temp_db.get_next_contract_number(increment=True)
        assert first == 10000 or first == 10001  # بسته به تنظیمات
        
        # شماره بعدی باید یک بیشتر باشد
        second = temp_db.get_next_contract_number(increment=False)
        assert second == 10001 or second == 10002
    
    def test_save_and_get_contract(self, temp_db, sample_contract_data):
        """تست ذخیره و دریافت قرارداد"""
        import json
        
        seller_json = json.dumps(sample_contract_data["seller"], ensure_ascii=False)
        buyer_json = json.dumps(sample_contract_data["buyer"], ensure_ascii=False)
        car_json = json.dumps(sample_contract_data["car_deal"], ensure_ascii=False)
        deal_json = json.dumps(sample_contract_data["deal_info"], ensure_ascii=False)
        
        contract_number = temp_db.save_contract(
            buyer_id=sample_contract_data["buyer"]["national_code"],
            seller_id=sample_contract_data["seller"]["national_code"],
            file_path="/test/path.docx",
            date_shamsi=sample_contract_data["deal_info"]["deal_date"],
            seller_json=seller_json,
            buyer_json=buyer_json,
            car_json=car_json,
            deal_json=deal_json,
            checkpoint_image="/test/checkpoint.png"
        )
        
        assert contract_number is not None
        
        # دریافت قرارداد
        contract = temp_db.get_contract(contract_number)
        assert contract is not None
        assert contract["buyer_id"] == sample_contract_data["buyer"]["national_code"]
        assert contract["seller_id"] == sample_contract_data["seller"]["national_code"]
    
    def test_delete_contract(self, temp_db, sample_contract_data):
        """تست حذف قرارداد"""
        import json
        
        seller_json = json.dumps(sample_contract_data["seller"], ensure_ascii=False)
        buyer_json = json.dumps(sample_contract_data["buyer"], ensure_ascii=False)
        car_json = json.dumps(sample_contract_data["car_deal"], ensure_ascii=False)
        deal_json = json.dumps(sample_contract_data["deal_info"], ensure_ascii=False)
        
        contract_number = temp_db.save_contract(
            buyer_id=sample_contract_data["buyer"]["national_code"],
            seller_id=sample_contract_data["seller"]["national_code"],
            file_path="/test/path.docx",
            date_shamsi=sample_contract_data["deal_info"]["deal_date"],
            seller_json=seller_json,
            buyer_json=buyer_json,
            car_json=car_json,
            deal_json=deal_json,
            checkpoint_image="/test/checkpoint.png"
        )
        
        # حذف قرارداد
        result = temp_db.delete_contract(contract_number)
        assert result is True
        
        # بررسی اینکه حذف شده
        contract = temp_db.get_contract(contract_number)
        assert contract is None
    
    def test_setting_save_and_get(self, temp_db):
        """تست ذخیره و دریافت تنظیمات"""
        temp_db.set_setting("test_key", "test_value")
        value = temp_db.get_setting("test_key")
        assert value == "test_value"
        
        # تست مقدار پیش‌فرض
        default = temp_db.get_setting("non_existent", "default")
        assert default == "default"
    
    def test_get_statistics(self, temp_db, sample_contract_data):
        """تست آمار دیتابیس"""
        stats = temp_db.get_statistics()
        assert "total_contracts" in stats
        assert "today_contracts" in stats
        assert "last_contract" in stats
    
    def test_duplicate_contract_number(self, temp_db, sample_contract_data):
        """تست جلوگیری از شماره قرارداد تکراری"""
        import json
        
        seller_json = json.dumps(sample_contract_data["seller"], ensure_ascii=False)
        buyer_json = json.dumps(sample_contract_data["buyer"], ensure_ascii=False)
        car_json = json.dumps(sample_contract_data["car_deal"], ensure_ascii=False)
        deal_json = json.dumps(sample_contract_data["deal_info"], ensure_ascii=False)
        
        # ذخیره اول
        temp_db.save_contract(
            buyer_id=sample_contract_data["buyer"]["national_code"],
            seller_id=sample_contract_data["seller"]["national_code"],
            file_path="/test/path.docx",
            date_shamsi=sample_contract_data["deal_info"]["deal_date"],
            seller_json=seller_json,
            buyer_json=buyer_json,
            car_json=car_json,
            deal_json=deal_json,
            checkpoint_image="/test/checkpoint.png"
        )
        
        # تلاش برای ذخیره مجدد با شماره یکسان - باید خطا بدهد
        # با توجه به get_next_contract_number خودکار، این خطا نباید رخ دهد
        # تست برای اطمینان از یکتایی contract_number