# tests/test_search.py
import pytest
import json
import os
import sqlite3
from database.db import DatabaseManager


class TestSearchApp:
    """تست‌های مربوط به جستجوی قراردادها"""
    
    def test_search_by_name(self, temp_db, sample_contract_data):
        """تست جستجو بر اساس نام"""
        import json
        
        # ذخیره قرارداد تست
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
        
        # جستجو با نام فروشنده
        with temp_db.connect() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM contracts 
                WHERE seller_json LIKE ?
            """, (f"%{sample_contract_data['seller']['name']}%",))
            results = cur.fetchall()
            
            assert len(results) >= 1
    
    def test_search_by_contract_number(self, temp_db, sample_contract_data):
        """تست جستجو بر اساس شماره قرارداد"""
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
        
        # جستجو با شماره قرارداد
        with temp_db.connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM contracts WHERE contract_number = ?", (contract_number,))
            result = cur.fetchone()
            
            assert result is not None
            assert result["contract_number"] == contract_number
    
    def test_search_by_national_code(self, temp_db, sample_contract_data):
        """تست جستجو بر اساس کد ملی"""
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
        
        # جستجو با کد ملی خریدار
        with temp_db.connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM contracts WHERE buyer_id = ?", 
                       (sample_contract_data["buyer"]["national_code"],))
            results = cur.fetchall()
            
            assert len(results) >= 1
            assert results[0]["buyer_id"] == sample_contract_data["buyer"]["national_code"]
    
    def test_search_no_results(self, temp_db):
        """تست جستجو با نتیجه خالی"""
        with temp_db.connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM contracts WHERE buyer_id = ?", ("9999999999",))
            results = cur.fetchall()
            
            assert len(results) == 0