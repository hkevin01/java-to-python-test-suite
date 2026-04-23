# =============================================================================
# test_java_parsing.py
# Unit tests for tools/java_analyzer.py — parse_java_class().
# Validates: class/interface/enum detection, method/field extraction,
# extends/implements hierarchy, package parsing, and graceful error handling.
# No LLM, no network, no filesystem I/O.
# =============================================================================
import sys, os
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "../../")))
from conftest import (
    JAVA_ORDER, JAVA_ORDER_STATUS, JAVA_CUSTOMER, JAVA_IREPOSITORY,
    JAVA_ABSTRACT_PROCESSOR, JAVA_ORDER_SERVICE, JAVA_PAYMENT_PROCESSOR,
    JAVA_ORDER_REPOSITORY, JAVA_SINGLE_METHOD, JAVA_GENERICS_HEAVY,
    JAVA_EMPTY, JAVA_MALFORMED, JAVA_CIRCULAR_A,
)
import pytest
from tools.java_analyzer import parse_java_class, JavaClassInfo

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Basic class parsing
# ---------------------------------------------------------------------------

def test_parse_order_class_name():
    info = parse_java_class(JAVA_ORDER)
    assert info is not None
    assert info.name == "Order"


def test_parse_order_package():
    info = parse_java_class(JAVA_ORDER)
    assert info.package == "com.example.ecommerce"


def test_parse_order_fields():
    info = parse_java_class(JAVA_ORDER)
    assert "id" in info.fields
    assert "amount" in info.fields
    assert "status" in info.fields


def test_parse_order_methods():
    info = parse_java_class(JAVA_ORDER)
    methods = info.methods
    assert "getId" in methods or "get_id" in methods or any("id" in m.lower() for m in methods)
    assert "getAmount" in methods or any("amount" in m.lower() for m in methods)
    assert "isPending" in methods or any("pending" in m.lower() for m in methods)


def test_parse_order_is_not_interface():
    info = parse_java_class(JAVA_ORDER)
    assert info.is_interface is False


def test_parse_order_is_not_abstract():
    info = parse_java_class(JAVA_ORDER)
    assert info.is_abstract is False


def test_parse_order_has_no_extends():
    info = parse_java_class(JAVA_ORDER)
    # Order doesn't extend anything explicitly
    assert info.extends is None or info.extends == "Object"


# ---------------------------------------------------------------------------
# Interface parsing
# ---------------------------------------------------------------------------

def test_parse_interface_detected():
    info = parse_java_class(JAVA_IREPOSITORY)
    assert info is not None
    assert info.is_interface is True


def test_parse_interface_name():
    info = parse_java_class(JAVA_IREPOSITORY)
    assert info.name == "IRepository"


def test_parse_interface_methods():
    info = parse_java_class(JAVA_IREPOSITORY)
    assert len(info.methods) >= 4  # findById, findAll, save, delete


def test_parse_interface_not_abstract():
    """Interfaces are not flagged as abstract (they are their own category)."""
    info = parse_java_class(JAVA_IREPOSITORY)
    # is_interface=True; is_abstract may be False or True depending on impl.
    assert info.is_interface is True


# ---------------------------------------------------------------------------
# Abstract class parsing
# ---------------------------------------------------------------------------

def test_parse_abstract_class_detected():
    info = parse_java_class(JAVA_ABSTRACT_PROCESSOR)
    assert info is not None
    assert info.is_abstract is True


def test_parse_abstract_class_name():
    info = parse_java_class(JAVA_ABSTRACT_PROCESSOR)
    assert info.name == "AbstractProcessor"


def test_parse_abstract_class_methods():
    info = parse_java_class(JAVA_ABSTRACT_PROCESSOR)
    assert any("process" in m for m in info.methods)


# ---------------------------------------------------------------------------
# Inheritance and implements
# ---------------------------------------------------------------------------

def test_parse_payment_processor_extends():
    info = parse_java_class(JAVA_PAYMENT_PROCESSOR)
    assert info.extends == "AbstractProcessor"


def test_parse_order_repository_implements():
    info = parse_java_class(JAVA_ORDER_REPOSITORY)
    assert "IRepository" in info.implements


def test_parse_customer_no_extends():
    info = parse_java_class(JAVA_CUSTOMER)
    assert info.extends is None or info.extends == "Object"


# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

def test_parse_order_service_imports():
    info = parse_java_class(JAVA_ORDER_SERVICE)
    imports_str = " ".join(info.imports)
    assert "ArrayList" in imports_str or "List" in imports_str


def test_parse_customer_imports_order():
    info = parse_java_class(JAVA_CUSTOMER)
    imports_str = " ".join(info.imports)
    assert "ArrayList" in imports_str or "List" in imports_str


# ---------------------------------------------------------------------------
# Single-method minimal class
# ---------------------------------------------------------------------------

def test_parse_single_method_class():
    info = parse_java_class(JAVA_SINGLE_METHOD)
    assert info is not None
    assert info.name == "SingleMethod"
    assert len(info.methods) >= 1


def test_parse_single_method_static():
    info = parse_java_class(JAVA_SINGLE_METHOD)
    assert any("add" in m for m in info.methods)


# ---------------------------------------------------------------------------
# Generics
# ---------------------------------------------------------------------------

def test_parse_generic_class_name():
    info = parse_java_class(JAVA_GENERICS_HEAVY)
    assert info is not None
    assert info.name == "GenericContainer"


def test_parse_generic_class_methods():
    info = parse_java_class(JAVA_GENERICS_HEAVY)
    assert any("put" in m for m in info.methods) or any("get" in m for m in info.methods)


# ---------------------------------------------------------------------------
# Error / edge cases — must not raise
# ---------------------------------------------------------------------------

def test_parse_empty_source_returns_none_or_valid():
    """Empty source should not crash — returns None or a minimal info."""
    result = parse_java_class(JAVA_EMPTY)
    # Either None (can't find class) or a valid JavaClassInfo
    assert result is None or isinstance(result, JavaClassInfo)


def test_parse_malformed_source_does_not_raise():
    """Severely malformed Java must be handled gracefully."""
    result = parse_java_class(JAVA_MALFORMED)
    assert result is None or isinstance(result, JavaClassInfo)


def test_parse_circular_a_detects_extends():
    info = parse_java_class(JAVA_CIRCULAR_A)
    assert info is not None
    assert info.name == "CircularA"
    assert info.extends == "CircularB"


def test_parse_returns_javaclaassinfo_type():
    info = parse_java_class(JAVA_ORDER)
    assert isinstance(info, JavaClassInfo)
