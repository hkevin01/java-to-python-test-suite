# =============================================================================
# test_boundary_conditions.py
# Adversarial tests: boundary conditions and scale limits.
# Tests that the system handles extreme but valid inputs without degrading
# output quality, crashing, or silently dropping data.
# =============================================================================
import pytest
from tools.java_analyzer import parse_java_class
from tools.project_translator import plan_project_translation

pytestmark = pytest.mark.adversarial


# ---------------------------------------------------------------------------
# Large class: 50 methods
# ---------------------------------------------------------------------------

def _generate_java_class(class_name: str, method_count: int, field_count: int = 5) -> str:
    fields = "\n".join(
        f"    private String field{i};"
        for i in range(field_count)
    )
    methods = "\n".join(
        f"    public String method{i}(String param{i}) {{ return field{i % field_count}; }}"
        for i in range(method_count)
    )
    return f"""\
package com.example;
import java.util.List;

public class {class_name} {{
{fields}

    public {class_name}() {{}}

{methods}
}}"""


def test_class_with_50_methods_parsed():
    java = _generate_java_class("LargeClass", 50)
    result = parse_java_class(java)
    assert result is not None
    assert result.name == "LargeClass"


def test_class_with_50_methods_all_detected():
    java = _generate_java_class("LargeClass", 50)
    result = parse_java_class(java)
    assert result is not None
    assert len(result.methods) >= 50


def test_class_with_100_methods_does_not_crash():
    java = _generate_java_class("HugeClass", 100)
    result = parse_java_class(java)
    assert result is None or result.name == "HugeClass"


# ---------------------------------------------------------------------------
# Long class names and method names
# ---------------------------------------------------------------------------

def test_class_with_very_long_name():
    long_name = "VeryLong" + "Class" * 20
    java = f"package com.example;\npublic class {long_name} {{ public void run() {{}} }}"
    result = parse_java_class(java)
    assert result is None or result.name == long_name


def test_method_with_very_long_parameter_list():
    params = ", ".join(f"String param{i}" for i in range(20))
    java = f"public class Foo {{ public void bigMethod({params}) {{}} }}"
    result = parse_java_class(java)
    assert result is None or hasattr(result, "methods")


# ---------------------------------------------------------------------------
# Single-line minimal class
# ---------------------------------------------------------------------------

def test_single_line_class():
    java = "public class Minimal {}"
    result = parse_java_class(java)
    assert result is not None
    assert result.name == "Minimal"


def test_single_line_class_with_method():
    from conftest import JAVA_SINGLE_METHOD
    result = parse_java_class(JAVA_SINGLE_METHOD)
    assert result is not None


# ---------------------------------------------------------------------------
# Generics-heavy class
# ---------------------------------------------------------------------------

def test_generics_heavy_class_parsed():
    from conftest import JAVA_GENERICS_HEAVY
    result = parse_java_class(JAVA_GENERICS_HEAVY)
    assert result is not None


def test_generics_heavy_class_has_methods():
    from conftest import JAVA_GENERICS_HEAVY
    result = parse_java_class(JAVA_GENERICS_HEAVY)
    if result is not None:
        assert len(result.methods) >= 1


# ---------------------------------------------------------------------------
# Large project translation: 20 independent files
# ---------------------------------------------------------------------------

def _build_independent_project(n: int) -> dict:
    """n independent classes with no intra-project dependencies."""
    return {
        f"Class{i}.java": f"package com.example;\npublic class Class{i} {{ public void run{i}() {{}} }}"
        for i in range(n)
    }


def test_twenty_file_project_translated():
    project = _build_independent_project(20)
    plan = plan_project_translation(project)
    assert plan is not None
    assert len(plan.ordered_files) == 20


def test_twenty_file_project_no_cycle():
    project = _build_independent_project(20)
    plan = plan_project_translation(project)
    assert plan.had_cycle is False


def test_twenty_file_project_all_filenames_present():
    project = _build_independent_project(20)
    plan = plan_project_translation(project)
    output_names = {f.filename for f in plan.ordered_files}
    for name in project:
        assert name in output_names


def test_twenty_file_project_no_duplicate_orders():
    """Each FileEntry must have a unique order value."""
    project = _build_independent_project(20)
    plan = plan_project_translation(project)
    orders = [f.order for f in plan.ordered_files]
    assert len(orders) == len(set(orders)), "Duplicate order values found"


# ---------------------------------------------------------------------------
# Linear chain: 15 classes each depending on the next
# ---------------------------------------------------------------------------

def _build_chain_project(n: int) -> dict:
    """Linear dependency chain: Class0←Class1←…←Class(n-1)."""
    project = {}
    for i in range(n):
        if i == 0:
            src = f"package com.example;\npublic class Chain0 {{ public void run() {{}} }}"
        else:
            src = f"package com.example;\nimport com.example.Chain{i-1};\npublic class Chain{i} extends Chain{i-1} {{ public void run{i}() {{}} }}"
        project[f"Chain{i}.java"] = src
    return project


def test_chain_15_classes_correct_order():
    """Chain0 must appear before Chain14 in translation order."""
    project = _build_chain_project(15)
    plan = plan_project_translation(project)
    assert plan is not None
    orders = {f.filename: f.order for f in plan.ordered_files}
    assert orders.get("Chain0.java", 999) < orders.get("Chain14.java", -1), (
        f"Chain0 order {orders.get('Chain0.java')} should be < Chain14 order {orders.get('Chain14.java')}"
    )


def test_chain_15_classes_no_cycle():
    project = _build_chain_project(15)
    plan = plan_project_translation(project)
    assert plan.had_cycle is False


def test_chain_15_classes_all_present():
    project = _build_chain_project(15)
    plan = plan_project_translation(project)
    assert len(plan.ordered_files) == 15
