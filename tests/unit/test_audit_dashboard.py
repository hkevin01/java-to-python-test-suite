import pytest

from core.audit_dashboard import build_release_dashboard


pytestmark = pytest.mark.unit


def test_release_dashboard_contains_zero_trust_section():
    records = [
        {
            "action": "translate",
            "status": "ok",
            "blocked": False,
            "user_id": "u1",
            "latency_ms": 55.0,
            "performance_status": "within_control",
            "ctq_metrics": {"latency": "within_control", "reliability": "pass"},
            "six_sigma": {"dpmo": 0.0, "sigma_band": "world_class", "control_state": "in_control"},
            "loadrunner": {"transaction": "translate", "passed": True},
        }
    ]

    dashboard = build_release_dashboard(records)

    assert "zero_trust" in dashboard
    assert dashboard["zero_trust"]["posture"] in {"strong", "moderate", "needs_hardening", "insufficient_data"}
    assert dashboard["zero_trust"]["identity_verification_rate"] == 1.0
    assert dashboard["zero_trust"]["policy_decision_rate"] == 1.0


def test_release_dashboard_zero_trust_needs_hardening_without_identity_signal():
    records = [
        {
            "action": "translate",
            "status": "ok",
            "blocked": False,
            "latency_ms": 60.0,
            "performance_status": "within_control",
            "ctq_metrics": {"latency": "within_control"},
            "loadrunner": {"transaction": "translate", "passed": True},
        }
    ]

    dashboard = build_release_dashboard(records)

    assert dashboard["zero_trust"]["identity_verification_rate"] == 0.0
    assert dashboard["zero_trust"]["posture"] == "needs_hardening"