# tests/test_generator.py
import pytest
import os
import json
from unittest.mock import patch, MagicMock


class TestContractGenerator:
    
    def test_flatten_data(self, sample_contract_data):
        from word.generator import ContractGenerator
        
        generator = ContractGenerator()
        flat = generator.flatten_data(sample_contract_data)
        
        assert flat["seller_fname"] == "علی محمدی"
        assert flat["buyer_ncode"] == "0987654321"
        assert flat["car_type"] == "پراید"
        assert flat["deal_num"] == "10001"
    
    def test_flatten_data_has_all_fields(self, sample_contract_data):
        from word.generator import ContractGenerator
        
        generator = ContractGenerator()
        flat = generator.flatten_data(sample_contract_data)
        
        required = [
            "seller_fname", "seller_ncode", "buyer_fname", "buyer_ncode",
            "car_type", "car_color", "car_model", "body_id", "pelak",
            "deal_date", "deal_num", "is_payed"
        ]
        
        for field in required:
            assert field in flat
    
    def test_generate_contract(self, temp_dir, sample_json_file, sample_checkpoint_image):
        from word.generator import ContractGenerator
        
        generator = ContractGenerator()
        output = generator.generate(
            json_path=sample_json_file,
            checkpoint_image_path=sample_checkpoint_image,
            output_dir=temp_dir
        )
        
        assert output is not None
        assert os.path.exists(output)
        assert output.endswith(".docx")