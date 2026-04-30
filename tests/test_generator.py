# tests/test_generator.py - نسخه اصلاح شده
import pytest
import sys
from unittest.mock import patch, MagicMock


class TestContractGenerator:
    
    @pytest.fixture
    def sample_contract_data(self):
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
                "adress": "تهران"
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
                "address": "شیراز"
            },
            "car_deal": {
                "type": "پراید",
                "color": "سفید",
                "system": "دنده‌ای",
                "model": "۱۳۹۸",
                "body_id": "ABC123",
                "motor_id": "XYZ987",
                "kilometer": "120000",
                "pelak": "۱۲۳ - ب - ۴۵۶",
                "car_info": "بدون مشکل"
            },
            "deal_info": {
                "deal_date": "1402/01/15",
                "deal_time": "14:30",
                "day_respite": "۷",
                "price_rial": "۵۰۰٬۰۰۰٬۰۰۰",
                "price_toman": "۵۰٬۰۰۰٬۰۰۰",
                "price_info": "نقدی",
                "deal_num": "10001"
            }
        }
    
    def test_flatten_data(self, sample_contract_data):
        """تست تبدیل داده تو در تو به تخت"""
        from word.generator import ContractGenerator
        
        generator = ContractGenerator()
        # جلوگیری از چک کردن Word
        generator._check_word_installed = lambda: True
        
        flat = generator.flatten_data(sample_contract_data)
        
        assert flat["seller_fname"] == f"{sample_contract_data['seller']['name']} {sample_contract_data['seller']['lname']}"
        assert flat["buyer_ncode"] == sample_contract_data["buyer"]["national_code"]
        assert flat["car_type"] == sample_contract_data["car_deal"]["type"]
        assert flat["deal_date"] is not None
    
    def test_flatten_data_all_fields(self, sample_contract_data):
        """تست وجود همه فیلدهای مورد نیاز"""
        from word.generator import ContractGenerator
        
        generator = ContractGenerator()
        generator._check_word_installed = lambda: True
        
        flat = generator.flatten_data(sample_contract_data)
        
        required_fields = [
            "seller_birth", "seller_fname", "seller_ncode", "seller_father",
            "buyer_birth", "buyer_fname", "buyer_ncode", "buyer_father",
            "car_type", "car_color", "car_model", "body_id", "motor_id"
        ]
        
        for field in required_fields:
            assert field in flat, f"Missing field: {field}"
    
    @pytest.mark.skip(reason="این تست نیاز به Microsoft Word نصب شده دارد")
    def test_check_word_installed(self):
        """تست بررسی نصب Word - Skip در محیط CI"""
        from word.generator import ContractGenerator
        generator = ContractGenerator()
        result = generator._check_word_installed()
        assert result is True