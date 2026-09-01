"""Unit tests for AST Validation and Indentation Normalizer."""

import pytest
from semantic_engine.core.csi import CanonicalSymbolId
from semantic_engine.mutation.normalizer import NormalizationError, SymbolBodyNormalizer


def test_normalizer_method_zero_indent_input():
    csi = CanonicalSymbolId.parse("csi://pkg/services/OrderService.create_order")
    # Raw 0-indent input from LLM
    raw_code = """def create_order(self, user_id: str) -> Order:
    print("creating order")
    return Order(user_id=user_id)
"""
    normalized = SymbolBodyNormalizer.normalize_callable_body(raw_code, target_csi=csi, is_method=True)
    lines = normalized.splitlines()

    # Must be indented with 4 spaces for class method
    assert lines[0] == "    def create_order(self, user_id: str) -> Order:"
    assert lines[1] == '        print("creating order")'
    assert lines[2] == "        return Order(user_id=user_id)"


def test_normalizer_method_already_indented_input():
    csi = CanonicalSymbolId.parse("csi://pkg/services/OrderService.create_order")
    # Input already indented with 8 spaces or irregular tabs
    raw_code = """        def create_order(self, user_id: str) -> Order:
            return Order(user_id=user_id)
"""
    normalized = SymbolBodyNormalizer.normalize_callable_body(raw_code, target_csi=csi, is_method=True)
    lines = normalized.splitlines()

    # Normalized down to standard 4-space method indentation
    assert lines[0] == "    def create_order(self, user_id: str) -> Order:"
    assert lines[1] == "        return Order(user_id=user_id)"


def test_normalizer_top_level_function():
    csi = CanonicalSymbolId.parse("csi://pkg/utils/generate_id")
    raw_code = """    def generate_id(prefix: str = "id") -> str:
        return f"{prefix}_123"
"""
    normalized = SymbolBodyNormalizer.normalize_callable_body(raw_code, target_csi=csi, is_method=False)
    lines = normalized.splitlines()

    # Top-level functions have 0 leading spaces
    assert lines[0] == 'def generate_id(prefix: str = "id") -> str:'
    assert lines[1] == '    return f"{prefix}_123"'


def test_normalizer_rejects_syntax_error():
    csi = CanonicalSymbolId.parse("csi://pkg/utils/calc")
    invalid_code = "def calc(x): return x +++ ("

    with pytest.raises(NormalizationError) as exc_info:
        SymbolBodyNormalizer.normalize_callable_body(invalid_code, target_csi=csi)
    assert "Syntax error" in str(exc_info.value)


def test_normalizer_rejects_function_name_mismatch():
    csi = CanonicalSymbolId.parse("csi://pkg/services/OrderService.create_order")
    # Snippet mistakenly defines calculate_tax instead of create_order
    mismatched_code = """def calculate_tax(amount: float) -> float:
    return amount * 0.1
"""
    with pytest.raises(NormalizationError) as exc_info:
        SymbolBodyNormalizer.normalize_callable_body(mismatched_code, target_csi=csi, is_method=True)
    assert "Function name mismatch" in str(exc_info.value)
    assert "calculate_tax" in str(exc_info.value)

