# tests/test_database.py
import pytest
import json
from database.db import DatabaseManager, DatabaseError


class TestDatabaseManager:
    
    def test_init(self):
        db = DatabaseManager(":memory:")
        assert db is not None
    
    def test_create_tables(self, temp_db):
        with temp_db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cur.fetchall()]
            
            assert "settings" in tables
            assert "contracts" in tables
            assert "logs" in tables
    
    def test_get_next_contract_number(self, temp_db):
        first = temp_db.get_next_contract_number()
        assert first >= 10000
        
        second = temp_db.get_next_contract_number()
        assert second == first + 1
    
    def test_save_and_get_contract(self, temp_db, sample_contract_data):
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
            checkpoint_image="/test/checkpoint.png",
            is_payed=0,
            price_info="نقدی",
            description_text="تست"
        )
        
        assert contract_number is not None
        
        contract = temp_db.get_contract_by_number(contract_number)
        assert contract is not None
        assert contract["buyer_id"] == sample_contract_data["buyer"]["national_code"]
    
    def test_delete_contract(self, temp_db, sample_contract_data):
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
            checkpoint_image="/test/checkpoint.png",
            is_payed=0,
            price_info="نقدی",
            description_text="تست"
        )
        
        result = temp_db.delete_contract(contract_number)
        assert result is True
        
        contract = temp_db.get_contract_by_number(contract_number)
        assert contract is None
    
    def test_update_payment(self, temp_db, sample_contract_data):
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
            checkpoint_image="/test/checkpoint.png",
            is_payed=0,
            price_info="نقدی",
            description_text="تست"
        )
        
        result = temp_db.update_contract_payment(contract_number, 1)
        assert result is True
        
        contract = temp_db.get_contract_by_number(contract_number)
        assert contract["is_payed"] == 1
    
    def test_search_contracts(self, temp_db, sample_contract_data):
        import json
        
        seller_json = json.dumps(sample_contract_data["seller"], ensure_ascii=False)
        buyer_json = json.dumps(sample_contract_data["buyer"], ensure_ascii=False)
        car_json = json.dumps(sample_contract_data["car_deal"], ensure_ascii=False)
        deal_json = json.dumps(sample_contract_data["deal_info"], ensure_ascii=False)
        
        temp_db.save_contract(
            buyer_id=sample_contract_data["buyer"]["national_code"],
            seller_id=sample_contract_data["seller"]["national_code"],
            file_path="/test/path.docx",
            date_shamsi=sample_contract_data["deal_info"]["deal_date"],
            seller_json=seller_json,
            buyer_json=buyer_json,
            car_json=car_json,
            deal_json=deal_json,
            checkpoint_image="/test/checkpoint.png",
            is_payed=0,
            price_info="نقدی",
            description_text="تست"
        )
        
        results = temp_db.search_contracts(name="علی")
        assert len(results) >= 1
        
        results = temp_db.search_contracts(ncode="1234567890")
        assert len(results) >= 1