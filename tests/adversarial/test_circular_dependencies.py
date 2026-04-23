# =============================================================================
# test_circular_dependencies.py
# Adversarial tests: circular dependency handling in project translation.
# Tests that the system detects and handles cycles gracefully — no infinite
# loops, all files still present in output, had_cycle=True flag set.
# =============================================================================
import pytest
from tools.project_translator import plan_project_translation

pytestmark = pytest.mark.adversarial


# ---------------------------------------------------------------------------
# Two-class direct cycle (A extends B, B extends A)
# ---------------------------------------------------------------------------

def test_two_class_cycle_detected():
    from conftest import JAVA_CIRCULAR_A, JAVA_CIRCULAR_B
    plan = plan_project_translation({
        "CircularA.java": JAVA_CIRCULAR_A,
        "CircularB.java": JAVA_CIRCULAR_B,
    })
    assert plan.had_cycle is True


def test_two_class_cycle_all_files_present():
    from conftest import JAVA_CIRCULAR_A, JAVA_CIRCULAR_B
    plan = plan_project_translation({
        "CircularA.java": JAVA_CIRCULAR_A,
        "CircularB.java": JAVA_CIRCULAR_B,
    })
    filenames = [f.filename for f in plan.ordered_files]
    assert "CircularA.java" in filenames
    assert "CircularB.java" in filenames


def test_two_class_cycle_no_infinite_loop():
    """plan_project_translation must return — no infinite recursion."""
    from conftest import JAVA_CIRCULAR_A, JAVA_CIRCULAR_B
    import signal

    def timeout_handler(signum, frame):
        pytest.fail("plan_project_translation timed out — possible infinite loop")

    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(5)
    try:
        plan_project_translation({
            "CircularA.java": JAVA_CIRCULAR_A,
            "CircularB.java": JAVA_CIRCULAR_B,
        })
    finally:
        signal.alarm(0)


def test_two_class_cycle_order_values_assigned():
    from conftest import JAVA_CIRCULAR_A, JAVA_CIRCULAR_B
    plan = plan_project_translation({
        "CircularA.java": JAVA_CIRCULAR_A,
        "CircularB.java": JAVA_CIRCULAR_B,
    })
    for fe in plan.ordered_files:
        assert fe.order >= 0


# ---------------------------------------------------------------------------
# Three-class cycle: A→B→C→A
# ---------------------------------------------------------------------------

THREE_WAY_A = """\
package com.example;
public class ThreeA extends ThreeC {
    public void doA() {}
}"""

THREE_WAY_B = """\
package com.example;
public class ThreeB extends ThreeA {
    public void doB() {}
}"""

THREE_WAY_C = """\
package com.example;
public class ThreeC extends ThreeB {
    public void doC() {}
}"""


def test_three_class_cycle_detected():
    plan = plan_project_translation({
        "ThreeA.java": THREE_WAY_A,
        "ThreeB.java": THREE_WAY_B,
        "ThreeC.java": THREE_WAY_C,
    })
    assert plan.had_cycle is True


def test_three_class_cycle_all_files_present():
    plan = plan_project_translation({
        "ThreeA.java": THREE_WAY_A,
        "ThreeB.java": THREE_WAY_B,
        "ThreeC.java": THREE_WAY_C,
    })
    filenames = [f.filename for f in plan.ordered_files]
    assert "ThreeA.java" in filenames
    assert "ThreeB.java" in filenames
    assert "ThreeC.java" in filenames


def test_three_class_cycle_no_infinite_loop():
    import signal

    def timeout_handler(signum, frame):
        pytest.fail("three-way cycle caused infinite loop")

    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(5)
    try:
        plan_project_translation({
            "ThreeA.java": THREE_WAY_A,
            "ThreeB.java": THREE_WAY_B,
            "ThreeC.java": THREE_WAY_C,
        })
    finally:
        signal.alarm(0)


# ---------------------------------------------------------------------------
# Cycle + clean node: cycle should be detected, clean node unaffected
# ---------------------------------------------------------------------------

CLEAN_D = """\
package com.example;
public class CleanD {
    public void doD() {}
}"""


def test_cycle_plus_clean_node():
    from conftest import JAVA_CIRCULAR_A, JAVA_CIRCULAR_B
    plan = plan_project_translation({
        "CircularA.java": JAVA_CIRCULAR_A,
        "CircularB.java": JAVA_CIRCULAR_B,
        "CleanD.java": CLEAN_D,
    })
    assert plan.had_cycle is True
    filenames = [f.filename for f in plan.ordered_files]
    assert "CleanD.java" in filenames


def test_cycle_plus_clean_node_all_three_present():
    from conftest import JAVA_CIRCULAR_A, JAVA_CIRCULAR_B
    plan = plan_project_translation({
        "CircularA.java": JAVA_CIRCULAR_A,
        "CircularB.java": JAVA_CIRCULAR_B,
        "CleanD.java": CLEAN_D,
    })
    assert len(plan.ordered_files) == 3


# ---------------------------------------------------------------------------
# No cycle — clean project
# ---------------------------------------------------------------------------

def test_ecommerce_no_cycle():
    from conftest import ECOMMERCE_PROJECT
    plan = plan_project_translation(ECOMMERCE_PROJECT)
    assert plan.had_cycle is False


def test_single_file_no_cycle():
    from conftest import JAVA_ORDER
    plan = plan_project_translation({"Order.java": JAVA_ORDER})
    assert plan.had_cycle is False
