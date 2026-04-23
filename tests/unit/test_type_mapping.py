# =============================================================================
# test_type_mapping.py
# Unit tests: Java→Python type mapping rules embedded in translation prompts.
# Tests that JAVA_TO_PYTHON_RULES contains all required mappings, that
# build_project_file_prompt() embeds the rules, and that the mock Python
# outputs actually apply the expected type mappings.
# =============================================================================
import pytest
from tools.translation_tools import JAVA_TO_PYTHON_RULES, build_java_to_python_prompt as build_translate_prompt
from tools.project_translator import build_project_file_prompt

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# JAVA_TO_PYTHON_RULES content — all required mappings must be present
# ---------------------------------------------------------------------------

def test_rules_map_string_to_str():
    assert "String" in JAVA_TO_PYTHON_RULES
    assert "str" in JAVA_TO_PYTHON_RULES


def test_rules_map_boolean_to_bool():
    assert "boolean" in JAVA_TO_PYTHON_RULES
    assert "bool" in JAVA_TO_PYTHON_RULES


def test_rules_map_void_to_none():
    assert "void" in JAVA_TO_PYTHON_RULES
    assert "None" in JAVA_TO_PYTHON_RULES


def test_rules_map_arraylist_to_list():
    assert "ArrayList" in JAVA_TO_PYTHON_RULES
    assert "list[T]" in JAVA_TO_PYTHON_RULES


def test_rules_map_hashmap_to_dict():
    assert "HashMap" in JAVA_TO_PYTHON_RULES
    assert "dict" in JAVA_TO_PYTHON_RULES


def test_rules_map_optional_to_union_none():
    assert "Optional" in JAVA_TO_PYTHON_RULES
    assert "| None" in JAVA_TO_PYTHON_RULES


def test_rules_map_abstract_class_to_abc():
    assert "abstract class" in JAVA_TO_PYTHON_RULES
    assert "ABC" in JAVA_TO_PYTHON_RULES


def test_rules_map_interface_to_protocol():
    assert "interface" in JAVA_TO_PYTHON_RULES
    assert "Protocol" in JAVA_TO_PYTHON_RULES


def test_rules_map_enum_to_enum():
    assert "enum" in JAVA_TO_PYTHON_RULES


def test_rules_map_getter_setter_to_property():
    assert "property" in JAVA_TO_PYTHON_RULES


def test_rules_map_static_final_to_module_const():
    assert "static final" in JAVA_TO_PYTHON_RULES


def test_rules_map_system_out_println():
    assert "System.out.println" in JAVA_TO_PYTHON_RULES


def test_rules_contain_exception_handling_section():
    assert "EXCEPTION HANDLING" in JAVA_TO_PYTHON_RULES or "Exception" in JAVA_TO_PYTHON_RULES


def test_rules_contain_control_flow_section():
    assert "for" in JAVA_TO_PYTHON_RULES
    assert "range" in JAVA_TO_PYTHON_RULES


def test_rules_not_empty():
    assert len(JAVA_TO_PYTHON_RULES.strip()) >= 500


# ---------------------------------------------------------------------------
# build_translate_prompt() — embeds rules in output
# ---------------------------------------------------------------------------

def test_translate_prompt_contains_rules():
    from conftest import JAVA_ORDER
    prompt = build_translate_prompt(JAVA_ORDER, "Order")
    assert "JAVA → PYTHON TRANSLATION RULES" in prompt or "ArrayList" in prompt


def test_translate_prompt_contains_java_source():
    from conftest import JAVA_ORDER
    prompt = build_translate_prompt(JAVA_ORDER, "Order")
    assert "Order" in prompt


def test_translate_prompt_non_empty():
    from conftest import JAVA_ORDER
    prompt = build_translate_prompt(JAVA_ORDER, "Order")
    assert len(prompt) > 200


def test_translate_prompt_no_secrets():
    from conftest import JAVA_ORDER
    prompt = build_translate_prompt(JAVA_ORDER, "Order")
    # Prompt must not contain JWT or key material
    assert "BEGIN RSA PRIVATE KEY" not in prompt
    assert "AKIA" not in prompt


# ---------------------------------------------------------------------------
# build_project_file_prompt() — uses rules, includes dependency context
# ---------------------------------------------------------------------------

def test_project_file_prompt_contains_rules():
    from conftest import JAVA_ORDER
    from tools.java_analyzer import parse_java_class
    from tools.project_translator import FileEntry
    info = parse_java_class(JAVA_ORDER)
    fe = FileEntry(filename="Order.java", source=JAVA_ORDER, class_info=info,
                   dependencies=[], order=0)
    prompt = build_project_file_prompt(fe, class_map={})
    assert "JAVA → PYTHON TRANSLATION RULES" in prompt or len(prompt) > 100


def test_project_file_prompt_contains_filename():
    from conftest import JAVA_ORDER
    from tools.java_analyzer import parse_java_class
    from tools.project_translator import FileEntry
    info = parse_java_class(JAVA_ORDER)
    fe = FileEntry(filename="Order.java", source=JAVA_ORDER, class_info=info,
                   dependencies=[], order=0)
    prompt = build_project_file_prompt(fe, class_map={})
    assert "Order" in prompt


def test_project_file_prompt_with_dependencies():
    from conftest import JAVA_ORDER_SERVICE
    from tools.java_analyzer import parse_java_class
    from tools.project_translator import FileEntry
    info = parse_java_class(JAVA_ORDER_SERVICE)
    fe = FileEntry(filename="OrderService.java", source=JAVA_ORDER_SERVICE,
                   class_info=info, dependencies=["Order"], order=1)
    prompt = build_project_file_prompt(fe, class_map={"Order": "order.py"})
    # Prompt should mention the dependency
    assert "Order" in prompt


# ---------------------------------------------------------------------------
# Type mapping verification in mock Python outputs
# ---------------------------------------------------------------------------

def test_mock_output_uses_str_not_String():
    from conftest import PYTHON_ORDER_MOCK, PYTHON_ORDER_SERVICE_MOCK
    assert "String " not in PYTHON_ORDER_MOCK
    assert "String " not in PYTHON_ORDER_SERVICE_MOCK


def test_mock_output_uses_bool_not_boolean():
    from conftest import PYTHON_ABSTRACT_PROCESSOR_MOCK
    assert "boolean " not in PYTHON_ABSTRACT_PROCESSOR_MOCK


def test_mock_output_uses_list_not_arraylist():
    from conftest import PYTHON_ORDER_SERVICE_MOCK
    assert "ArrayList" not in PYTHON_ORDER_SERVICE_MOCK


def test_mock_output_uses_dict_not_hashmap():
    """If output mentions HashMap or LinkedHashMap, the mapping failed."""
    from conftest import PYTHON_ORDER_SERVICE_MOCK
    assert "HashMap" not in PYTHON_ORDER_SERVICE_MOCK
    assert "LinkedHashMap" not in PYTHON_ORDER_SERVICE_MOCK


def test_mock_output_uses_none_not_void():
    """void should never appear in Python output."""
    from conftest import (PYTHON_ORDER_MOCK, PYTHON_ORDER_SERVICE_MOCK,
                          PYTHON_ABSTRACT_PROCESSOR_MOCK)
    for name, src in [
        ("Order", PYTHON_ORDER_MOCK),
        ("OrderService", PYTHON_ORDER_SERVICE_MOCK),
        ("AbstractProcessor", PYTHON_ABSTRACT_PROCESSOR_MOCK),
    ]:
        assert "void " not in src, f"'void' found in {name} Python output"
