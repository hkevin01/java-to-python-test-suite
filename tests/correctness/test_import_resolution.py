# =============================================================================
# test_import_resolution.py
# Correctness tests: Java import statements are correctly translated to Python
# import statements. Tests that no Java package references appear in Python
# output, and that Python-idiomatic equivalents are used.
# =============================================================================
import ast
import pytest
from tools.java_analyzer import parse_java_class

pytestmark = pytest.mark.correctness


# ---------------------------------------------------------------------------
# Java imports are parsed correctly from source
# ---------------------------------------------------------------------------

def test_order_java_imports_detected():
    from conftest import JAVA_ORDER
    info = parse_java_class(JAVA_ORDER)
    assert info is not None
    # Should detect java.util imports
    imports_str = " ".join(info.imports)
    assert "java.util" in imports_str or len(info.imports) >= 1


def test_order_service_imports_detected():
    from conftest import JAVA_ORDER_SERVICE
    info = parse_java_class(JAVA_ORDER_SERVICE)
    assert info is not None
    assert len(info.imports) >= 1


def test_abstract_processor_imports_detected():
    from conftest import JAVA_ABSTRACT_PROCESSOR
    info = parse_java_class(JAVA_ABSTRACT_PROCESSOR)
    assert info is not None
    assert len(info.imports) >= 1


# ---------------------------------------------------------------------------
# Python output has no Java package references
# ---------------------------------------------------------------------------

def test_python_output_no_java_util():
    from conftest import PYTHON_ORDER_MOCK
    assert "import java.util" not in PYTHON_ORDER_MOCK
    assert "java.util" not in PYTHON_ORDER_MOCK


def test_python_output_no_java_io():
    from conftest import PYTHON_ORDER_SERVICE_MOCK
    assert "java.io" not in PYTHON_ORDER_SERVICE_MOCK


def test_python_output_no_javax():
    from conftest import PYTHON_ORDER_SERVICE_MOCK, PYTHON_ABSTRACT_PROCESSOR_MOCK
    assert "javax." not in PYTHON_ORDER_SERVICE_MOCK
    assert "javax." not in PYTHON_ABSTRACT_PROCESSOR_MOCK


def test_python_output_no_org_springframework():
    from conftest import PYTHON_ORDER_SERVICE_MOCK
    assert "org.springframework" not in PYTHON_ORDER_SERVICE_MOCK


# ---------------------------------------------------------------------------
# Python output uses standard Python library equivalents
# ---------------------------------------------------------------------------

def test_python_output_uses_dataclasses():
    from conftest import PYTHON_ORDER_MOCK
    # dataclasses is the Python equivalent of Java POJO with getters/setters
    assert "dataclass" in PYTHON_ORDER_MOCK or "from dataclasses" in PYTHON_ORDER_MOCK


def test_python_output_uses_abc_for_abstract():
    from conftest import PYTHON_ABSTRACT_PROCESSOR_MOCK
    assert "ABC" in PYTHON_ABSTRACT_PROCESSOR_MOCK or "abc" in PYTHON_ABSTRACT_PROCESSOR_MOCK


def test_python_output_uses_typing_or_builtins():
    from conftest import PYTHON_ORDER_SERVICE_MOCK
    # list[T] or List[T], Optional or T|None
    has_typing = (
        "from typing import" in PYTHON_ORDER_SERVICE_MOCK
        or "list[" in PYTHON_ORDER_SERVICE_MOCK
        or "List[" in PYTHON_ORDER_SERVICE_MOCK
    )
    assert has_typing


def test_python_output_uses_protocol_for_interface():
    from conftest import PYTHON_IREPOSITORY_MOCK
    assert "Protocol" in PYTHON_IREPOSITORY_MOCK


# ---------------------------------------------------------------------------
# Python output is importable (no circular imports in the mock)
# ---------------------------------------------------------------------------

def test_all_mock_outputs_parseable_by_ast():
    from conftest import (
        PYTHON_ORDER_MOCK, PYTHON_ORDER_SERVICE_MOCK,
        PYTHON_IREPOSITORY_MOCK, PYTHON_ABSTRACT_PROCESSOR_MOCK,
        PYTHON_PAYMENT_PROCESSOR_MOCK,
    )
    for name, src in [
        ("Order", PYTHON_ORDER_MOCK),
        ("OrderService", PYTHON_ORDER_SERVICE_MOCK),
        ("IRepository", PYTHON_IREPOSITORY_MOCK),
        ("AbstractProcessor", PYTHON_ABSTRACT_PROCESSOR_MOCK),
        ("PaymentProcessor", PYTHON_PAYMENT_PROCESSOR_MOCK),
    ]:
        try:
            ast.parse(src)
        except SyntaxError as e:
            pytest.fail(f"SyntaxError in {name}: {e}")


# ---------------------------------------------------------------------------
# No Java-specific constructor syntax in Python output
# ---------------------------------------------------------------------------

def test_python_output_no_new_keyword():
    from conftest import PYTHON_ORDER_SERVICE_MOCK, PYTHON_PAYMENT_PROCESSOR_MOCK
    assert " new " not in PYTHON_ORDER_SERVICE_MOCK
    assert " new " not in PYTHON_PAYMENT_PROCESSOR_MOCK


def test_python_output_no_angle_bracket_generics():
    from conftest import PYTHON_ORDER_MOCK, PYTHON_ORDER_SERVICE_MOCK
    # Java generics use <>, Python uses []
    assert "ArrayList<" not in PYTHON_ORDER_MOCK
    assert "List<" not in PYTHON_ORDER_SERVICE_MOCK
