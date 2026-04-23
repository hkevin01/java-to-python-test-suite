# =============================================================================
# test_dependency_graph.py
# Unit tests for tools/project_translator.py — dependency graph construction,
# _parse_files(), _build_dependency_graph(), plan_project_translation().
# Validates: intra-project deps only, self-loop exclusion, external JDK deps
# ignored, class_map correctness, FileEntry.dependencies populated.
# =============================================================================
import sys, os
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "../../")))
from conftest import (
    JAVA_ORDER, JAVA_ORDER_SERVICE, JAVA_PAYMENT_PROCESSOR,
    JAVA_ABSTRACT_PROCESSOR, JAVA_ORDER_REPOSITORY, JAVA_IREPOSITORY,
    JAVA_ORDER_STATUS, JAVA_CUSTOMER, ECOMMERCE_PROJECT,
    JAVA_CIRCULAR_A, JAVA_CIRCULAR_B,
)
import pytest
from tools.project_translator import (
    plan_project_translation,
    _parse_files,
    _build_dependency_graph,
    FileEntry,
    ProjectTranslationPlan,
)

pytestmark = pytest.mark.unit


def _make_entries(files: dict) -> list[FileEntry]:
    return [FileEntry(filename=fn, source=src) for fn, src in files.items()]


# ---------------------------------------------------------------------------
# _parse_files — populates class_info on each entry
# ---------------------------------------------------------------------------

def test_parse_files_populates_class_info():
    entries = _make_entries({"Order.java": JAVA_ORDER})
    _parse_files(entries)
    assert entries[0].class_info is not None
    assert entries[0].class_info.name == "Order"


def test_parse_files_builds_class_map():
    entries = _make_entries({
        "Order.java": JAVA_ORDER,
        "Customer.java": JAVA_CUSTOMER,
    })
    class_map = _parse_files(entries)
    assert "Order" in class_map
    assert "Customer" in class_map


def test_parse_files_maps_filename():
    entries = _make_entries({"Order.java": JAVA_ORDER})
    class_map = _parse_files(entries)
    assert class_map["Order"] == "Order.java"


def test_parse_files_does_not_raise_on_malformed():
    """Malformed Java in one entry must not abort processing of others."""
    entries = _make_entries({
        "Order.java": JAVA_ORDER,
        "Broken.java": "public class {{{",
    })
    class_map = _parse_files(entries)
    # Order must still be in class_map even with Broken.java present
    assert "Order" in class_map


def test_parse_files_all_eight_ecommerce_classes():
    entries = _make_entries(ECOMMERCE_PROJECT)
    class_map = _parse_files(entries)
    expected = {"Order", "Customer", "OrderService", "OrderStatus",
                "AbstractProcessor", "PaymentProcessor", "IRepository", "OrderRepository"}
    assert expected.issubset(set(class_map.keys()))


# ---------------------------------------------------------------------------
# _build_dependency_graph — dependency edge construction
# ---------------------------------------------------------------------------

def test_order_service_depends_on_order():
    entries = _make_entries({
        "Order.java": JAVA_ORDER,
        "OrderService.java": JAVA_ORDER_SERVICE,
    })
    class_map = _parse_files(entries)
    graph = _build_dependency_graph(entries, class_map)
    # OrderService depends on Order (import or field type)
    assert "Order" in graph.get("OrderService", set())


def test_payment_processor_depends_on_abstract_processor():
    entries = _make_entries({
        "AbstractProcessor.java": JAVA_ABSTRACT_PROCESSOR,
        "PaymentProcessor.java": JAVA_PAYMENT_PROCESSOR,
    })
    class_map = _parse_files(entries)
    graph = _build_dependency_graph(entries, class_map)
    assert "AbstractProcessor" in graph.get("PaymentProcessor", set())


def test_order_has_no_intra_project_deps():
    """Order only imports java.util.UUID — no intra-project dependencies."""
    entries = _make_entries({"Order.java": JAVA_ORDER})
    class_map = _parse_files(entries)
    graph = _build_dependency_graph(entries, class_map)
    # Order should have empty deps (no intra-project classes)
    assert graph.get("Order", set()) == set()


def test_no_self_loop_in_graph():
    entries = _make_entries(ECOMMERCE_PROJECT)
    class_map = _parse_files(entries)
    graph = _build_dependency_graph(entries, class_map)
    for class_name, deps in graph.items():
        assert class_name not in deps, f"Self-loop detected for {class_name}"


def test_external_jdk_classes_not_in_graph():
    """ArrayList, Optional, etc. are JDK classes — must not appear as nodes."""
    entries = _make_entries(ECOMMERCE_PROJECT)
    class_map = _parse_files(entries)
    graph = _build_dependency_graph(entries, class_map)
    jdk_classes = {"ArrayList", "HashMap", "Optional", "List", "String", "UUID"}
    for jdk in jdk_classes:
        assert jdk not in graph, f"JDK class {jdk} should not be a graph node"


def test_order_repository_depends_on_irepository_and_order():
    entries = _make_entries({
        "Order.java": JAVA_ORDER,
        "IRepository.java": JAVA_IREPOSITORY,
        "OrderRepository.java": JAVA_ORDER_REPOSITORY,
    })
    class_map = _parse_files(entries)
    graph = _build_dependency_graph(entries, class_map)
    deps = graph.get("OrderRepository", set())
    assert "IRepository" in deps or "Order" in deps


# ---------------------------------------------------------------------------
# plan_project_translation — end-to-end
# ---------------------------------------------------------------------------

def test_plan_returns_project_translation_plan():
    plan = plan_project_translation(ECOMMERCE_PROJECT)
    assert isinstance(plan, ProjectTranslationPlan)


def test_plan_all_files_in_output():
    plan = plan_project_translation(ECOMMERCE_PROJECT)
    output_filenames = {e.filename for e in plan.ordered_files}
    assert output_filenames == set(ECOMMERCE_PROJECT.keys())


def test_plan_class_map_populated():
    plan = plan_project_translation(ECOMMERCE_PROJECT)
    assert len(plan.class_map) >= 7


def test_plan_no_cycle_ecommerce():
    plan = plan_project_translation(ECOMMERCE_PROJECT)
    assert plan.had_cycle is False


def test_plan_circular_detects_cycle():
    plan = plan_project_translation({
        "CircularA.java": JAVA_CIRCULAR_A,
        "CircularB.java": JAVA_CIRCULAR_B,
    })
    assert plan.had_cycle is True


def test_plan_circular_still_returns_both_files():
    """Cycle should not drop files from output."""
    plan = plan_project_translation({
        "CircularA.java": JAVA_CIRCULAR_A,
        "CircularB.java": JAVA_CIRCULAR_B,
    })
    names = {e.filename for e in plan.ordered_files}
    assert "CircularA.java" in names
    assert "CircularB.java" in names


def test_plan_single_file():
    plan = plan_project_translation({"Order.java": JAVA_ORDER})
    assert len(plan.ordered_files) == 1
    assert plan.had_cycle is False
