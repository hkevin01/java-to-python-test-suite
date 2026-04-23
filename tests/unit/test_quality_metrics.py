import pytest

from core.quality_metrics import (
    build_quality_snapshot,
    calculate_dpmo,
    classify_latency,
    get_performance_budget,
    sigma_band_from_dpmo,
)


pytestmark = pytest.mark.unit


def test_get_performance_budget_defaults_translate():
    budget = get_performance_budget("translate")
    assert budget.target_ms == 250
    assert budget.warning_ms == 200


def test_classify_latency_within_control():
    budget = get_performance_budget("translate")
    assert classify_latency(50, budget) == "within_control"


def test_classify_latency_warning():
    budget = get_performance_budget("translate")
    assert classify_latency(220, budget) == "warning"


def test_classify_latency_breach():
    budget = get_performance_budget("translate")
    assert classify_latency(300, budget) == "breach"


def test_calculate_dpmo_handles_zero_units():
    assert calculate_dpmo(defects=1, units=0, opportunities_per_unit=4) == 0.0


def test_calculate_dpmo_basic_case():
    assert calculate_dpmo(defects=1, units=10, opportunities_per_unit=5) == 20000.0


def test_sigma_band_world_class():
    assert sigma_band_from_dpmo(3.4) == "world_class"


def test_sigma_band_out_of_control():
    assert sigma_band_from_dpmo(100000.0) == "out_of_control"


def test_build_quality_snapshot_contains_loadrunner_and_ctq_metrics():
    snapshot = build_quality_snapshot(action="translate", latency_ms=125.0)
    assert snapshot["performance_status"] == "within_control"
    assert snapshot["ctq_metrics"]["traceability"] == "pass"
    assert snapshot["loadrunner"]["transaction"] == "translate"


def test_build_quality_snapshot_records_defects_as_watch_or_worse():
    snapshot = build_quality_snapshot(action="translate_project", latency_ms=450.0, defects=1, units=4, opportunities_per_unit=3)
    assert snapshot["six_sigma"]["control_state"] == "out_of_control"
    assert snapshot["six_sigma"]["dpmo"] > 0