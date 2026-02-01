import os
from word.generator import ContractGenerator
import sys


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

def test_contract_generation():
    gen = ContractGenerator()
    output = gen.generate()

    assert os.path.exists(output)

def test_generator_requires_inputs():
    gen = ContractGenerator()

    try:
        gen.generate()
        assert False, "متد generate نباید بدون ورودی اجرا شود"
    except TypeError:
        assert True