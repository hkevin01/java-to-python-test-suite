# =============================================================================
# test_topological_sort.py
# Unit tests for _topological_sort() in tools/project_translator.py.
# This function implements Kahn's algorithm — base classes before subclasses.
# Validates: correct ordering, cycle detection, empty graph, single node,
# diamond dependency, large chain, and the invariant that for every node
# all its dependencies appear at a lower index in the output list.
# =============================================================================
import pytest
from tools.project_translator import _topological_sort, plan_project_translation
from conftest import ECOMMERCE_PROJECT

pytestmark = pytest.mark.unit


def _deps_before(result: list, node: str, deps: set) -> bool:
    """Return True if every dep in deps appears before node in result."""
    if node not in result:
        return False
    node_idx = result.index(node)
    for dep in deps:
        if dep in result and result.index(dep) >= node_idx:
            return False
    return True


# ---------------------------------------------------------------------------
# Empty and trivial graphs
# ---------------------------------------------------------------------------

def test_empty_graph_returns_empty():
    result, had_cycle = _topological_sort({})
    assert result == []
    assert had_cycle is False


def test_single_node_no_deps():
    graph = {"A": set()}
    result, had_cycle = _topological_sort(graph)
    assert result == ["A"]
    assert had_cycle is False


def test_two_nodes_a_depends_on_b():
    graph = {"A": {"B"}, "B": set()}
    result, had_cycle = _topological_sort(graph)
    assert result.index("B") < result.index("A")
    assert had_cycle is False


# ---------------------------------------------------------------------------
# Linear chain
# ---------------------------------------------------------------------------

def test_linear_chain_three_nodes():
    """A → B → C: C must come first, then B, then A."""
    graph = {"A": {"B"}, "B": {"C"}, "C": set()}
    result, had_cycle = _topological_sort(graph)
    assert result.index("C") < result.index("B") < result.index("A")
    assert had_cycle is False


def test_linear_chain_five_nodes():
    graph = {"E": {"D"}, "D": {"C"}, "C": {"B"}, "B": {"A"}, "A": set()}
    result, had_cycle = _topological_sort(graph)
    for i, node in enumerate("EDCBA"):
        assert node in result
    assert result.index("A") < result.index("B") < result.index("C")
    assert had_cycle is False


# ---------------------------------------------------------------------------
# Diamond dependency pattern (common in Java inheritance)
# ---------------------------------------------------------------------------

def test_diamond_dependency():
    """
    D depends on B and C; B and C both depend on A.
    A must appear before B and C; B and C before D.
    """
    graph = {
        "D": {"B", "C"},
        "B": {"A"},
        "C": {"A"},
        "A": set(),
    }
    result, had_cycle = _topological_sort(graph)
    assert result.index("A") < result.index("B")
    assert result.index("A") < result.index("C")
    assert result.index("B") < result.index("D")
    assert result.index("C") < result.index("D")
    assert had_cycle is False


# ---------------------------------------------------------------------------
# Cycle detection
# ---------------------------------------------------------------------------

def test_direct_cycle_detected():
    graph = {"A": {"B"}, "B": {"A"}}
    result, had_cycle = _topological_sort(graph)
    assert had_cycle is True


def test_three_node_cycle():
    graph = {"A": {"C"}, "B": {"A"}, "C": {"B"}}
    result, had_cycle = _topological_sort(graph)
    assert had_cycle is True


def test_cycle_all_nodes_still_in_result():
    """Even with a cycle, every node must appear exactly once in result."""
    graph = {"A": {"B"}, "B": {"C"}, "C": {"A"}}
    result, had_cycle = _topological_sort(graph)
    assert had_cycle is True
    assert set(result) == {"A", "B", "C"}
    assert len(result) == len(set(result))  # no duplicates


def test_cycle_plus_clean_node():
    """A cycle in A-B-C should not affect the ordering of independent D."""
    graph = {"A": {"B"}, "B": {"A"}, "D": set()}
    result, had_cycle = _topological_sort(graph)
    assert had_cycle is True
    assert "D" in result
    assert result.index("D") < result.index("A") or result.index("D") < result.index("B")


# ---------------------------------------------------------------------------
# Multiple independent subgraphs
# ---------------------------------------------------------------------------

def test_two_independent_chains():
    graph = {
        "ServiceA": {"ModelA"},
        "ModelA": set(),
        "ServiceB": {"ModelB"},
        "ModelB": set(),
    }
    result, had_cycle = _topological_sort(graph)
    assert had_cycle is False
    assert result.index("ModelA") < result.index("ServiceA")
    assert result.index("ModelB") < result.index("ServiceB")


# ---------------------------------------------------------------------------
# Ecommerce project — end-to-end ordering invariant
# ---------------------------------------------------------------------------

def test_ecommerce_order_before_order_service():
    """
    Order has no intra-project dependencies.
    OrderService depends on Order.
    Therefore Order must appear before OrderService in the plan.
    """
    plan = plan_project_translation(ECOMMERCE_PROJECT)
    names = [e.class_info.name for e in plan.ordered_files if e.class_info]
    assert "Order" in names and "OrderService" in names
    assert names.index("Order") < names.index("OrderService")


def test_ecommerce_abstract_processor_before_payment_processor():
    plan = plan_project_translation(ECOMMERCE_PROJECT)
    names = [e.class_info.name for e in plan.ordered_files if e.class_info]
    assert names.index("AbstractProcessor") < names.index("PaymentProcessor")


def test_ecommerce_irepository_before_order_repository():
    plan = plan_project_translation(ECOMMERCE_PROJECT)
    names = [e.class_info.name for e in plan.ordered_files if e.class_info]
    assert names.index("IRepository") < names.index("OrderRepository")


def test_ecommerce_no_broken_ordering_invariant():
    """
    For every class in the plan, all its intra-project dependencies must
    have a lower index (i.e., appear earlier in the translation order).
    """
    plan = plan_project_translation(ECOMMERCE_PROJECT)
    name_to_idx = {
        e.class_info.name: i
        for i, e in enumerate(plan.ordered_files)
        if e.class_info
    }
    for entry in plan.ordered_files:
        if not entry.class_info:
            continue
        class_name = entry.class_info.name
        class_idx = name_to_idx[class_name]
        for dep in entry.dependencies:
            if dep in name_to_idx:
                assert name_to_idx[dep] < class_idx, (
                    f"Ordering violated: {dep} (idx={name_to_idx[dep]}) "
                    f"should come before {class_name} (idx={class_idx})"
                )


def test_ecommerce_order_set_correctly():
    """FileEntry.order field must be consistent with position in ordered_files."""
    plan = plan_project_translation(ECOMMERCE_PROJECT)
    for i, entry in enumerate(plan.ordered_files):
        if entry.class_info:
            assert entry.order == i
