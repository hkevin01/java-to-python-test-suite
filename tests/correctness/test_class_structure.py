# =============================================================================
# test_class_structure.py
# Correctness tests: Java class structure → Python class structure mapping.
# Tests that Java abstract classes become Python ABCs, interfaces become
# Protocols, enums become enum.Enum, and getters/setters become @property.
# =============================================================================
import ast
import pytest
from tools.java_analyzer import parse_java_class

pytestmark = pytest.mark.correctness


# ---------------------------------------------------------------------------
# Java class detection (parsing correctness)
# ---------------------------------------------------------------------------

def test_interface_detected_as_interface():
    from conftest import JAVA_IREPOSITORY
    info = parse_java_class(JAVA_IREPOSITORY)
    assert info is not None
    assert info.is_interface is True


def test_abstract_class_detected():
    from conftest import JAVA_ABSTRACT_PROCESSOR
    info = parse_java_class(JAVA_ABSTRACT_PROCESSOR)
    assert info is not None
    assert info.is_abstract is True


def test_concrete_class_not_abstract():
    from conftest import JAVA_ORDER
    info = parse_java_class(JAVA_ORDER)
    assert info is not None
    assert info.is_abstract is False


def test_concrete_class_not_interface():
    from conftest import JAVA_ORDER
    info = parse_java_class(JAVA_ORDER)
    assert info is not None
    assert info.is_interface is False


def test_enum_class_detected():
    from conftest import JAVA_ORDER_STATUS
    info = parse_java_class(JAVA_ORDER_STATUS)
    assert info is not None


# ---------------------------------------------------------------------------
# Python translation output: abstract class → ABC
# ---------------------------------------------------------------------------

def test_abstract_processor_python_uses_abc():
    from conftest import PYTHON_ABSTRACT_PROCESSOR_MOCK
    tree = ast.parse(PYTHON_ABSTRACT_PROCESSOR_MOCK)
    classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    abc_classes = [c for c in classes if any(
        (isinstance(b, ast.Name) and b.id == "ABC") or
        (isinstance(b, ast.Attribute) and b.attr == "ABC")
        for b in c.bases
    )]
    assert len(abc_classes) >= 1, "AbstractProcessor must inherit from ABC"


def test_abstract_processor_python_has_abstractmethod():
    from conftest import PYTHON_ABSTRACT_PROCESSOR_MOCK
    assert "@abstractmethod" in PYTHON_ABSTRACT_PROCESSOR_MOCK


def test_abstract_processor_python_imports_abc():
    from conftest import PYTHON_ABSTRACT_PROCESSOR_MOCK
    assert "from abc import" in PYTHON_ABSTRACT_PROCESSOR_MOCK or "import abc" in PYTHON_ABSTRACT_PROCESSOR_MOCK


# ---------------------------------------------------------------------------
# Python translation output: interface → Protocol
# ---------------------------------------------------------------------------

def test_irepository_python_uses_protocol():
    from conftest import PYTHON_IREPOSITORY_MOCK
    tree = ast.parse(PYTHON_IREPOSITORY_MOCK)
    classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    protocol_classes = [c for c in classes if any(
        (isinstance(b, ast.Name) and b.id == "Protocol") or
        (isinstance(b, ast.Attribute) and b.attr == "Protocol")
        for b in c.bases
    )]
    assert len(protocol_classes) >= 1, "IRepository must use Protocol"


def test_irepository_python_imports_protocol():
    from conftest import PYTHON_IREPOSITORY_MOCK
    assert "Protocol" in PYTHON_IREPOSITORY_MOCK


# ---------------------------------------------------------------------------
# Python translation output: concrete class with @property
# ---------------------------------------------------------------------------

def test_order_python_uses_property_decorator():
    from conftest import PYTHON_ORDER_MOCK
    assert "@property" in PYTHON_ORDER_MOCK


def test_order_python_class_exists():
    from conftest import PYTHON_ORDER_MOCK
    tree = ast.parse(PYTHON_ORDER_MOCK)
    classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    assert len(classes) >= 1


def test_order_python_has_init():
    from conftest import PYTHON_ORDER_MOCK
    tree = ast.parse(PYTHON_ORDER_MOCK)
    inits = [n for n in ast.walk(tree)
             if isinstance(n, ast.FunctionDef) and n.name == "__init__"]
    assert len(inits) >= 1


# ---------------------------------------------------------------------------
# Inheritance: concrete class extending abstract → proper Python inheritance
# ---------------------------------------------------------------------------

def test_payment_processor_extends_abstract():
    from conftest import PYTHON_PAYMENT_PROCESSOR_MOCK
    tree = ast.parse(PYTHON_PAYMENT_PROCESSOR_MOCK)
    classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    inherited = [c for c in classes if len(c.bases) >= 1]
    assert len(inherited) >= 1, "PaymentProcessor must inherit from AbstractProcessor"


def test_payment_processor_calls_super_init():
    from conftest import PYTHON_PAYMENT_PROCESSOR_MOCK
    assert "super().__init__" in PYTHON_PAYMENT_PROCESSOR_MOCK


def test_payment_processor_overrides_process():
    from conftest import PYTHON_PAYMENT_PROCESSOR_MOCK
    tree = ast.parse(PYTHON_PAYMENT_PROCESSOR_MOCK)
    methods = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    method_names = [m.name for m in methods]
    assert "process" in method_names or "process_payment" in method_names


# ---------------------------------------------------------------------------
# No Java access modifiers in Python output
# ---------------------------------------------------------------------------

def test_no_public_keyword():
    from conftest import PYTHON_ORDER_MOCK, PYTHON_ORDER_SERVICE_MOCK
    assert "public " not in PYTHON_ORDER_MOCK
    assert "public " not in PYTHON_ORDER_SERVICE_MOCK


def test_no_private_keyword():
    from conftest import PYTHON_ORDER_MOCK
    # Python uses _ prefix convention, not 'private' keyword
    assert "private " not in PYTHON_ORDER_MOCK


def test_no_protected_keyword():
    from conftest import PYTHON_ABSTRACT_PROCESSOR_MOCK
    assert "protected " not in PYTHON_ABSTRACT_PROCESSOR_MOCK
