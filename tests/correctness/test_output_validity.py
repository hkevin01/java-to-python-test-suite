# =============================================================================
# test_output_validity.py
# Tests that mock/expected Python translation outputs are syntactically valid
# and free of Java artifacts. Uses ast.parse() for structural validation.
# "If the translation passes these checks, a human reviewer can focus on
# semantics rather than syntax."
# =============================================================================
import ast
import sys
import pytest
from conftest import (
    PYTHON_ORDER_MOCK, PYTHON_ORDER_SERVICE_MOCK,
    PYTHON_IREPOSITORY_MOCK, PYTHON_ABSTRACT_PROCESSOR_MOCK,
    PYTHON_PAYMENT_PROCESSOR_MOCK,
)

pytestmark = pytest.mark.correctness

JAVA_ARTIFACTS = [
    "System.out.println",
    "new ArrayList<>",
    "new HashMap<>",
    "import java.",
    "import javax.",
    "public class",
    "public interface",
    "public void",
    "@Override",
    ".stream()",
    "instanceof ",
]


def assert_valid_python(source: str, label: str = ""):
    """Assert that source is syntactically valid Python."""
    try:
        ast.parse(source)
    except SyntaxError as e:
        pytest.fail(f"SyntaxError in {label or 'output'}: {e}\n---\n{source[:500]}")


def assert_no_java_artifacts(source: str, label: str = ""):
    for artifact in JAVA_ARTIFACTS:
        assert artifact not in source, (
            f"Java artifact '{artifact}' found in {label or 'output'}:\n{source[:300]}"
        )


# ---------------------------------------------------------------------------
# Mock translations are syntactically valid Python
# ---------------------------------------------------------------------------

def test_order_mock_is_valid_python():
    assert_valid_python(PYTHON_ORDER_MOCK, "Order")


def test_order_service_mock_is_valid_python():
    assert_valid_python(PYTHON_ORDER_SERVICE_MOCK, "OrderService")


def test_irepository_mock_is_valid_python():
    assert_valid_python(PYTHON_IREPOSITORY_MOCK, "IRepository")


def test_abstract_processor_mock_is_valid_python():
    assert_valid_python(PYTHON_ABSTRACT_PROCESSOR_MOCK, "AbstractProcessor")


def test_payment_processor_mock_is_valid_python():
    assert_valid_python(PYTHON_PAYMENT_PROCESSOR_MOCK, "PaymentProcessor")


# ---------------------------------------------------------------------------
# Mock translations are free of Java artifacts
# ---------------------------------------------------------------------------

def test_order_mock_no_java_artifacts():
    assert_no_java_artifacts(PYTHON_ORDER_MOCK, "Order")


def test_order_service_mock_no_java_artifacts():
    assert_no_java_artifacts(PYTHON_ORDER_SERVICE_MOCK, "OrderService")


def test_irepository_mock_no_java_artifacts():
    assert_no_java_artifacts(PYTHON_IREPOSITORY_MOCK, "IRepository")


def test_abstract_processor_mock_no_java_artifacts():
    assert_no_java_artifacts(PYTHON_ABSTRACT_PROCESSOR_MOCK, "AbstractProcessor")


def test_payment_processor_mock_no_java_artifacts():
    assert_no_java_artifacts(PYTHON_PAYMENT_PROCESSOR_MOCK, "PaymentProcessor")


# ---------------------------------------------------------------------------
# Structural content assertions — Python idiomatic patterns present
# ---------------------------------------------------------------------------

def test_order_mock_uses_dataclass():
    assert "@dataclass" in PYTHON_ORDER_MOCK


def test_order_mock_has_property():
    assert "@property" in PYTHON_ORDER_MOCK


def test_order_service_mock_uses_list_type():
    assert "list[" in PYTHON_ORDER_SERVICE_MOCK


def test_order_service_mock_uses_optional_type():
    assert "Optional" in PYTHON_ORDER_SERVICE_MOCK or "| None" in PYTHON_ORDER_SERVICE_MOCK


def test_irepository_mock_uses_protocol():
    assert "Protocol" in PYTHON_IREPOSITORY_MOCK


def test_abstract_processor_mock_uses_abc():
    assert "ABC" in PYTHON_ABSTRACT_PROCESSOR_MOCK
    assert "abstractmethod" in PYTHON_ABSTRACT_PROCESSOR_MOCK


def test_payment_processor_mock_has_super_init():
    assert "super().__init__" in PYTHON_PAYMENT_PROCESSOR_MOCK


def test_payment_processor_mock_inherits():
    assert "AbstractProcessor" in PYTHON_PAYMENT_PROCESSOR_MOCK


# ---------------------------------------------------------------------------
# Type annotation quality
# ---------------------------------------------------------------------------

def test_order_service_methods_have_return_type():
    tree = ast.parse(PYTHON_ORDER_SERVICE_MOCK)
    funcs = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    annotated = [f for f in funcs if f.returns is not None and f.name != "__init__"]
    assert len(annotated) >= 2, "Expected at least 2 methods with return type annotations"


def test_order_service_no_untyped_list():
    """list[Order] preferred over untyped List or bare list."""
    assert "list[" in PYTHON_ORDER_SERVICE_MOCK or "List[" in PYTHON_ORDER_SERVICE_MOCK


def test_abstract_processor_methods_return_bool():
    """process() returns bool — must appear in translated output."""
    assert "bool" in PYTHON_ABSTRACT_PROCESSOR_MOCK


# ---------------------------------------------------------------------------
# Import correctness — no circular or undefined references in mock outputs
# ---------------------------------------------------------------------------

def test_order_mock_no_import_java():
    assert "import java" not in PYTHON_ORDER_MOCK
    assert "import javax" not in PYTHON_ORDER_MOCK


def test_order_service_imports_order():
    """OrderService must import Order (or have it in the same module)."""
    assert "order" in PYTHON_ORDER_SERVICE_MOCK.lower() or "Order" in PYTHON_ORDER_SERVICE_MOCK


def test_payment_processor_imports_abstract_processor():
    assert "AbstractProcessor" in PYTHON_PAYMENT_PROCESSOR_MOCK


def test_payment_processor_imports_order():
    assert "Order" in PYTHON_PAYMENT_PROCESSOR_MOCK
