# word/__init__.py
from .generator import ContractGenerator, ContractGeneratorError, generate_contract

__all__ = ['ContractGenerator', 'ContractGeneratorError', 'generate_contract']