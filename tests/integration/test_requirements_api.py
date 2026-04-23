# =============================================================================
# test_requirements_api.py
# Integration tests: POST /api/v1/translate-requirements endpoint.
# Tests that requirements text produces a Python scaffold with def stubs
# and pytest test stubs.
# =============================================================================
import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport

pytestmark = pytest.mark.integration

SAMPLE_REQUIREMENTS = """\
REQ-001: The system shall validate that the user's email address is unique.
REQ-002: The system shall reject orders with amount <= 0.
REQ-003: The system shall store all completed orders in persistent storage.
REQ-004: The system shall notify the user upon successful order completion.
"""

MOCK_SCAFFOLD = """\
from __future__ import annotations


def validate_unique_email(email: str) -> bool:
    \"\"\"REQ-001: Validate that user email is unique.\"\"\"
    raise NotImplementedError


def validate_order_amount(amount: float) -> None:
    \"\"\"REQ-002: Reject orders with amount <= 0.\"\"\"
    raise NotImplementedError


def store_completed_order(order_id: str) -> None:
    \"\"\"REQ-003: Store completed order.\"\"\"
    raise NotImplementedError


def notify_user(user_id: str, message: str) -> None:
    \"\"\"REQ-004: Notify user on completion.\"\"\"
    raise NotImplementedError


# --- pytest stubs ---
def test_validate_unique_email():
    raise NotImplementedError

def test_validate_order_amount():
    raise NotImplementedError

def test_store_completed_order():
    raise NotImplementedError

def test_notify_user():
    raise NotImplementedError
"""


@pytest.fixture(scope="module")
def app():
    from main import app as _app
    return _app


@pytest.fixture
async def engineer_client(app):
    from core.auth import verify_token
    app.dependency_overrides[verify_token] = lambda: {"sub": "eng-1", "role": "engineer"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


def _mock_llm(ret: str = MOCK_SCAFFOLD):
    return patch("api.routes.call_llm", new=AsyncMock(return_value=ret))


# ---------------------------------------------------------------------------
# Basic structure
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_requirements_returns_200(engineer_client):
    with _mock_llm():
        resp = await engineer_client.post(
            "/api/v1/translate-requirements",
            json={"text": SAMPLE_REQUIREMENTS},
        )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_requirements_response_has_python_field(engineer_client):
    with _mock_llm():
        resp = await engineer_client.post(
            "/api/v1/translate-requirements",
            json={"text": SAMPLE_REQUIREMENTS},
        )
    assert "python" in resp.json()


@pytest.mark.asyncio
async def test_requirements_output_contains_def(engineer_client):
    with _mock_llm():
        resp = await engineer_client.post(
            "/api/v1/translate-requirements",
            json={"text": SAMPLE_REQUIREMENTS},
        )
    assert "def " in resp.json().get("python", "")


@pytest.mark.asyncio
async def test_requirements_output_contains_pytest_stubs(engineer_client):
    with _mock_llm():
        resp = await engineer_client.post(
            "/api/v1/translate-requirements",
            json={"text": SAMPLE_REQUIREMENTS},
        )
    python_output = resp.json().get("python", "")
    assert "def test_" in python_output


# ---------------------------------------------------------------------------
# Auth enforcement
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_requirements_without_auth_returns_401_or_403(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post(
            "/api/v1/translate-requirements",
            json={"text": SAMPLE_REQUIREMENTS},
        )
    assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Empty text → 400 or 422
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_requirements_empty_text_rejected(engineer_client):
    resp = await engineer_client.post(
        "/api/v1/translate-requirements",
        json={"text": ""},
    )
    assert resp.status_code in (400, 422)


# ---------------------------------------------------------------------------
# Output redaction — credentials in LLM response redacted
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_requirements_output_credentials_redacted(engineer_client):
    with _mock_llm("api_key=supersecret123"):
        resp = await engineer_client.post(
            "/api/v1/translate-requirements",
            json={"text": SAMPLE_REQUIREMENTS},
        )
    body = resp.json()
    assert resp.status_code == 200
    assert "supersecret123" not in body.get("python", "")
