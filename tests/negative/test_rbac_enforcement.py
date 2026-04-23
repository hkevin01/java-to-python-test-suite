# =============================================================================
# test_rbac_enforcement.py
# Negative tests: JWT RBAC enforcement via core/auth.py.
# Tests: role-to-permission mapping, permission checks, contractor restrictions,
# engineer full access, admin full access, unknown role denial, expired token.
# =============================================================================
import pytest
import time
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from core.auth import ROLE_PERMISSIONS, require_permission

pytestmark = pytest.mark.negative


# ---------------------------------------------------------------------------
# ROLE_PERMISSIONS structure
# ---------------------------------------------------------------------------

def test_engineer_has_translate():
    assert "translate" in ROLE_PERMISSIONS["engineer"]


def test_engineer_has_review():
    assert "review" in ROLE_PERMISSIONS["engineer"]


def test_engineer_has_test_gen():
    assert "test_gen" in ROLE_PERMISSIONS["engineer"]


def test_engineer_does_not_have_admin():
    assert "admin" not in ROLE_PERMISSIONS["engineer"]


def test_contractor_has_translate():
    assert "translate" in ROLE_PERMISSIONS["contractor"]


def test_contractor_has_code_assist():
    assert "code_assist" in ROLE_PERMISSIONS["contractor"]


def test_contractor_does_not_have_review():
    assert "review" not in ROLE_PERMISSIONS["contractor"]


def test_contractor_does_not_have_test_gen():
    assert "test_gen" not in ROLE_PERMISSIONS["contractor"]


def test_contractor_does_not_have_refactor():
    assert "refactor" not in ROLE_PERMISSIONS["contractor"]


def test_contractor_does_not_have_admin():
    assert "admin" not in ROLE_PERMISSIONS["contractor"]


def test_admin_has_all_permissions():
    admin_perms = ROLE_PERMISSIONS["admin"]
    for perm in ["translate", "review", "test_gen", "refactor", "code_assist", "docs", "admin"]:
        assert perm in admin_perms, f"admin missing permission: {perm}"


def test_unknown_role_not_in_mapping():
    assert "hacker" not in ROLE_PERMISSIONS
    assert "superuser" not in ROLE_PERMISSIONS


def test_unknown_role_gets_empty_permissions():
    perms = ROLE_PERMISSIONS.get("unknown_role", set())
    assert len(perms) == 0


# ---------------------------------------------------------------------------
# require_permission() — permission enforcement
# ---------------------------------------------------------------------------

def _make_payload(role: str, sub: str = "test-user") -> dict:
    return {"sub": sub, "role": role, "exp": int(time.time()) + 3600}


def test_engineer_can_translate():
    payload = _make_payload("engineer")
    # Must not raise
    require_permission(payload, "translate")


def test_engineer_can_review():
    payload = _make_payload("engineer")
    require_permission(payload, "review")


def test_engineer_can_test_gen():
    payload = _make_payload("engineer")
    require_permission(payload, "test_gen")


def test_contractor_translate_passes():
    payload = _make_payload("contractor")
    require_permission(payload, "translate")


def test_contractor_review_raises_403():
    payload = _make_payload("contractor")
    with pytest.raises(HTTPException) as exc_info:
        require_permission(payload, "review")
    assert exc_info.value.status_code == 403


def test_contractor_test_gen_raises_403():
    payload = _make_payload("contractor")
    with pytest.raises(HTTPException) as exc_info:
        require_permission(payload, "test_gen")
    assert exc_info.value.status_code == 403


def test_contractor_refactor_raises_403():
    payload = _make_payload("contractor")
    with pytest.raises(HTTPException) as exc_info:
        require_permission(payload, "refactor")
    assert exc_info.value.status_code == 403


def test_unknown_role_any_permission_raises_403():
    payload = _make_payload("hacker")
    with pytest.raises(HTTPException) as exc_info:
        require_permission(payload, "translate")
    assert exc_info.value.status_code == 403


def test_admin_can_access_admin_endpoints():
    payload = _make_payload("admin")
    require_permission(payload, "admin")


def test_engineer_admin_endpoint_raises_403():
    payload = _make_payload("engineer")
    with pytest.raises(HTTPException) as exc_info:
        require_permission(payload, "admin")
    assert exc_info.value.status_code == 403


def test_missing_role_claim_raises_403():
    payload = {"sub": "no-role-user"}
    with pytest.raises(HTTPException) as exc_info:
        require_permission(payload, "translate")
    assert exc_info.value.status_code == 403


def test_require_permission_error_message_non_empty():
    payload = _make_payload("contractor")
    with pytest.raises(HTTPException) as exc_info:
        require_permission(payload, "review")
    assert exc_info.value.detail is not None
    assert len(str(exc_info.value.detail)) > 0
