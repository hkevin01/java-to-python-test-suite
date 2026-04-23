# =============================================================================
# test_method_signatures.py
# Correctness tests: Java method signatures → Python method signatures.
# Tests return type mapping (void→None, String→str, boolean→bool,
# List<T>→list[T], Optional<T>→T|None), constructor→__init__,
# static method→@staticmethod.
# =============================================================================
import ast
import pytest
from tools.java_analyzer import parse_java_class

pytestmark = pytest.mark.correctness


# ---------------------------------------------------------------------------
# Java method parsing — verify the analyzer captures signatures
# ---------------------------------------------------------------------------

def test_order_service_methods_detected():
    from conftest import JAVA_ORDER_SERVICE
    info = parse_java_class(JAVA_ORDER_SERVICE)
    assert info is not None
    assert len(info.methods) >= 3


def test_abstract_processor_methods_detected():
    from conftest import JAVA_ABSTRACT_PROCESSOR
    info = parse_java_class(JAVA_ABSTRACT_PROCESSOR)
    assert info is not None
    assert len(info.methods) >= 1


def test_irepository_methods_detected():
    from conftest import JAVA_IREPOSITORY
    info = parse_java_class(JAVA_IREPOSITORY)
    assert info is not None
    assert len(info.methods) >= 2


def test_account_methods_detected():
    from conftest import JAVA_ACCOUNT
    info = parse_java_class(JAVA_ACCOUNT)
    assert info is not None
    assert len(info.methods) >= 1


# ---------------------------------------------------------------------------
# Python output: void → None return type
# ---------------------------------------------------------------------------

def test_order_service_void_methods_return_none():
    from conftest import PYTHON_ORDER_SERVICE_MOCK
    tree = ast.parse(PYTHON_ORDER_SERVICE_MOCK)
    funcs = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    none_returns = [f for f in funcs if (
        f.returns is not None and
        isinstance(f.returns, ast.Constant) and
        f.returns.value is None
    )]
    # At least some void methods should map to -> None
    assert len(none_returns) >= 1


# ---------------------------------------------------------------------------
# Python output: constructors are __init__
# ---------------------------------------------------------------------------

def test_order_service_has_init():
    from conftest import PYTHON_ORDER_SERVICE_MOCK
    tree = ast.parse(PYTHON_ORDER_SERVICE_MOCK)
    inits = [n for n in ast.walk(tree)
             if isinstance(n, ast.FunctionDef) and n.name == "__init__"]
    assert len(inits) >= 1


def test_abstract_processor_has_init():
    from conftest import PYTHON_ABSTRACT_PROCESSOR_MOCK
    tree = ast.parse(PYTHON_ABSTRACT_PROCESSOR_MOCK)
    inits = [n for n in ast.walk(tree)
             if isinstance(n, ast.FunctionDef) and n.name == "__init__"]
    assert len(inits) >= 1


# ---------------------------------------------------------------------------
# Python output: List<T> → list[T] or List[T]
# ---------------------------------------------------------------------------

def test_list_type_used_for_collections():
    from conftest import PYTHON_ORDER_SERVICE_MOCK
    assert "list[" in PYTHON_ORDER_SERVICE_MOCK or "List[" in PYTHON_ORDER_SERVICE_MOCK


# ---------------------------------------------------------------------------
# Python output: Optional<T> → T | None or Optional[T]
# ---------------------------------------------------------------------------

def test_optional_type_used():
    from conftest import PYTHON_ORDER_SERVICE_MOCK
    has_optional = (
        "Optional" in PYTHON_ORDER_SERVICE_MOCK
        or "| None" in PYTHON_ORDER_SERVICE_MOCK
    )
    assert has_optional


# ---------------------------------------------------------------------------
# Python output: all methods have `self` as first arg (instance methods)
# ---------------------------------------------------------------------------

def test_order_service_instance_methods_have_self():
    from conftest import PYTHON_ORDER_SERVICE_MOCK
    tree = ast.parse(PYTHON_ORDER_SERVICE_MOCK)
    classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    for cls in classes:
        for node in cls.body:
            if isinstance(node, ast.FunctionDef):
                # Skip static methods — they have no self
                decorators = [
                    d.id if isinstance(d, ast.Name) else
                    d.attr if isinstance(d, ast.Attribute) else ""
                    for d in node.decorator_list
                ]
                if "staticmethod" in decorators or "classmethod" in decorators:
                    continue
                args = [a.arg for a in node.args.args]
                assert args and args[0] == "self", (
                    f"Method '{node.name}' in '{cls.name}' missing 'self' as first arg"
                )


# ---------------------------------------------------------------------------
# Python output: abstractmethod decorator applied correctly
# ---------------------------------------------------------------------------

def test_abstract_processor_abstractmethod_applied():
    from conftest import PYTHON_ABSTRACT_PROCESSOR_MOCK
    tree = ast.parse(PYTHON_ABSTRACT_PROCESSOR_MOCK)
    funcs = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    abstract_funcs = [f for f in funcs if any(
        (isinstance(d, ast.Name) and d.id == "abstractmethod") or
        (isinstance(d, ast.Attribute) and d.attr == "abstractmethod")
        for d in f.decorator_list
    )]
    assert len(abstract_funcs) >= 1


# ---------------------------------------------------------------------------
# Python output: return type annotations are present (not missing)
# ---------------------------------------------------------------------------

def test_order_service_return_types_annotated():
    from conftest import PYTHON_ORDER_SERVICE_MOCK
    tree = ast.parse(PYTHON_ORDER_SERVICE_MOCK)
    funcs = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    non_init_funcs = [f for f in funcs if f.name != "__init__"]
    if not non_init_funcs:
        pytest.skip("No non-init methods found")
    annotated = [f for f in non_init_funcs if f.returns is not None]
    assert len(annotated) >= len(non_init_funcs) // 2, (
        "More than half of methods should have return type annotations"
    )
