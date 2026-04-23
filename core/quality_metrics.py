from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class PerformanceBudget:
    action: str
    target_ms: int
    warning_ms: int


DEFAULT_PERFORMANCE_BUDGETS: dict[str, PerformanceBudget] = {
    "translate": PerformanceBudget(action="translate", target_ms=250, warning_ms=200),
    "translate_project": PerformanceBudget(action="translate_project", target_ms=500, warning_ms=400),
    "translate_requirements": PerformanceBudget(action="translate_requirements", target_ms=250, warning_ms=200),
}


SIGMA_BANDS: tuple[tuple[float, str], ...] = (
    (3.4, "world_class"),
    (233.0, "excellent"),
    (6210.0, "good"),
    (66807.0, "watch"),
)


def _env_name_for_action(action: str) -> str:
    return f"{action.upper()}_SLA_MS"


def get_performance_budget(action: str) -> PerformanceBudget:
    budget = DEFAULT_PERFORMANCE_BUDGETS.get(action, PerformanceBudget(action=action, target_ms=300, warning_ms=240))
    env_override = os.getenv(_env_name_for_action(action))
    if not env_override:
        return budget

    try:
        target_ms = max(1, int(env_override))
    except ValueError:
        return budget

    warning_ms = max(1, int(target_ms * 0.8))
    return PerformanceBudget(action=action, target_ms=target_ms, warning_ms=warning_ms)


def classify_latency(latency_ms: float, budget: PerformanceBudget) -> str:
    if latency_ms <= budget.warning_ms:
        return "within_control"
    if latency_ms <= budget.target_ms:
        return "warning"
    return "breach"


def calculate_dpmo(defects: int, units: int, opportunities_per_unit: int) -> float:
    if units <= 0 or opportunities_per_unit <= 0:
        return 0.0
    total_opportunities = units * opportunities_per_unit
    return (max(defects, 0) / total_opportunities) * 1_000_000


def sigma_band_from_dpmo(dpmo: float) -> str:
    for threshold, band in SIGMA_BANDS:
        if dpmo <= threshold:
            return band
    return "out_of_control"


def control_state(latency_status: str, defects: int) -> str:
    if defects > 0 or latency_status == "breach":
        return "out_of_control"
    if latency_status == "warning":
        return "watch"
    return "in_control"


def build_loadrunner_transaction(action: str, latency_ms: float, budget: PerformanceBudget) -> dict[str, object]:
    return {
        "transaction": action,
        "response_time_ms": round(latency_ms, 3),
        "sla_ms": budget.target_ms,
        "passed": latency_ms <= budget.target_ms,
    }


def build_quality_snapshot(
    *,
    action: str,
    latency_ms: float,
    defects: int = 0,
    units: int = 1,
    opportunities_per_unit: int = 4,
) -> dict[str, object]:
    budget = get_performance_budget(action)
    latency_status = classify_latency(latency_ms, budget)
    dpmo = calculate_dpmo(defects=defects, units=units, opportunities_per_unit=opportunities_per_unit)
    sigma_band = sigma_band_from_dpmo(dpmo)

    return {
        "latency_ms": round(latency_ms, 3),
        "performance_budget_ms": budget.target_ms,
        "performance_status": latency_status,
        "ctq_metrics": {
            "latency": latency_status,
            "reliability": "pass" if defects == 0 else "fail",
            "traceability": "pass",
            "safety": "pass",
        },
        "six_sigma": {
            "defects": defects,
            "units": units,
            "opportunities_per_unit": opportunities_per_unit,
            "dpmo": round(dpmo, 3),
            "sigma_band": sigma_band,
            "control_state": control_state(latency_status, defects),
        },
        "loadrunner": build_loadrunner_transaction(action, latency_ms, budget),
    }