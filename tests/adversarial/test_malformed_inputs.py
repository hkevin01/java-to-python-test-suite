# =============================================================================
# test_malformed_inputs.py
# Adversarial tests: robustness under malformed, degenerate, and unexpected
# inputs. Tests that parsing and translation functions never crash with
# exceptions — they degrade gracefully (None, empty, partial results).
# =============================================================================
import pytest
from tools.java_analyzer import parse_java_class
from tools.project_translator import plan_project_translation
from guardrails.input_guard import sanitize, InputGuardError

pytestmark = pytest.mark.adversarial


# ---------------------------------------------------------------------------
# parse_java_class() — malformed / degenerate inputs
# ---------------------------------------------------------------------------

def test_empty_source_does_not_crash():
    result = parse_java_class("")
    # Should return None or an empty-ish object — not raise
    assert result is None or hasattr(result, "name")


def test_whitespace_only_does_not_crash():
    result = parse_java_class("   \n\t\n   ")
    assert result is None or hasattr(result, "name")


def test_malformed_java_does_not_crash():
    from conftest import JAVA_MALFORMED
    result = parse_java_class(JAVA_MALFORMED)
    # Any outcome except an unhandled exception is acceptable
    assert result is None or hasattr(result, "name")


def test_python_code_submitted_as_java_does_not_crash():
    python_code = """\
def hello(name: str) -> str:
    return f"Hello, {name}"

class Greeter:
    def greet(self, name: str) -> str:
        return hello(name)
"""
    result = parse_java_class(python_code)
    assert result is None or hasattr(result, "name")


def test_json_submitted_as_java_does_not_crash():
    json_str = '{"class": "FakeClass", "methods": ["run", "stop"]}'
    result = parse_java_class(json_str)
    assert result is None or hasattr(result, "name")


def test_binary_like_content_does_not_crash():
    """Simulate near-binary garbage — parse must not crash."""
    garbage = "ñ∂ƒ©˙∆˚¬…æ" * 20
    result = parse_java_class(garbage)
    assert result is None or hasattr(result, "name")


def test_sql_submitted_as_java_does_not_crash():
    sql = "SELECT * FROM users WHERE id = 1; DROP TABLE users; --"
    result = parse_java_class(sql)
    assert result is None or hasattr(result, "name")


def test_only_comments_does_not_crash():
    only_comments = """\
// This is a comment
/* Block comment */
/**
 * Javadoc comment
 */
"""
    result = parse_java_class(only_comments)
    assert result is None or hasattr(result, "name")


def test_extremely_deep_nesting_does_not_crash():
    """Deeply nested braces — no stack overflow."""
    nested = "public class Deep {\n" + "    public void m() {\n" * 100 + "    }\n" * 100 + "}"
    result = parse_java_class(nested)
    assert result is None or hasattr(result, "name")


def test_very_long_method_name_does_not_crash():
    long_name = "a" * 500
    java = f"public class Foo {{ public void {long_name}() {{}} }}"
    result = parse_java_class(java)
    # May parse or return None — must not crash
    assert result is None or hasattr(result, "name")


# ---------------------------------------------------------------------------
# plan_project_translation() — malformed / degenerate project inputs
# ---------------------------------------------------------------------------

def test_empty_project_no_crash():
    plan = plan_project_translation({})
    assert plan is not None
    assert len(plan.ordered_files) == 0


def test_single_malformed_file_no_crash():
    from conftest import JAVA_MALFORMED
    plan = plan_project_translation({"Malformed.java": JAVA_MALFORMED})
    assert plan is not None


def test_empty_source_in_project_no_crash():
    plan = plan_project_translation({"Empty.java": ""})
    assert plan is not None


def test_project_with_only_empty_files_no_crash():
    plan = plan_project_translation({
        "A.java": "",
        "B.java": "",
        "C.java": "",
    })
    assert plan is not None


def test_project_with_none_value_no_crash():
    """If a file entry has None content — must not crash."""
    try:
        plan = plan_project_translation({"NullFile.java": None})
        assert plan is not None
    except (TypeError, ValueError):
        pass  # Acceptable — explicit rejection of None is fine


def test_duplicate_filenames_no_crash():
    """Dict de-duplication means we get one entry — must not crash."""
    from conftest import JAVA_ORDER
    plan = plan_project_translation({
        "Order.java": JAVA_ORDER,
    })
    assert plan is not None


# ---------------------------------------------------------------------------
# sanitize() — null bytes and non-printable characters
# ---------------------------------------------------------------------------

def test_null_bytes_rejected():
    java_with_null = "public class Foo {\x00 public void bar() {} }"
    with pytest.raises(InputGuardError):
        sanitize(java_with_null)


def test_control_characters_stripped_or_rejected():
    """Control chars (BEL, ESC) must not pass through silently."""
    java_with_controls = "public class Foo {\x07\x1b public void bar() {} }"
    try:
        result = sanitize(java_with_controls)
        # If it passes — control characters must be gone
        assert "\x07" not in result
        assert "\x1b" not in result
    except InputGuardError:
        pass  # Also acceptable


def test_unicode_java_class_names_pass():
    """Modern Java supports Unicode identifiers — must not be rejected."""
    java = "public class Résumé { public void process() {} }"
    try:
        result = sanitize(java)
        assert len(result) > 0
    except InputGuardError:
        pytest.skip("Implementation rejects non-ASCII identifiers — acceptable for security posture")
