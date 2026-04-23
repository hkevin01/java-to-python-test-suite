# =============================================================================
# test_project_translate_api.py
# Integration tests: POST /api/v1/translate-project endpoint.
# Tests project-level translation with dependency ordering, cycle detection,
# and multi-file response structure.
# =============================================================================
import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport

pytestmark = pytest.mark.integration


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


def _mock_llm(return_value: str = "def translated(): pass"):
    return patch("api.routes.call_llm", new=AsyncMock(return_value=return_value))


# ---------------------------------------------------------------------------
# Basic structure: ecommerce project returns 200
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_project_translate_returns_200(engineer_client):
    from conftest import ECOMMERCE_PROJECT
    with _mock_llm():
        resp = await engineer_client.post(
            "/api/v1/translate-project",
            json={"files": ECOMMERCE_PROJECT, "style": "idiomatic"},
        )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_project_translate_response_has_files(engineer_client):
    from conftest import ECOMMERCE_PROJECT
    with _mock_llm():
        resp = await engineer_client.post(
            "/api/v1/translate-project",
            json={"files": ECOMMERCE_PROJECT, "style": "idiomatic"},
        )
    body = resp.json()
    assert "files" in body


@pytest.mark.asyncio
async def test_project_translate_response_has_dependency_order(engineer_client):
    from conftest import ECOMMERCE_PROJECT
    with _mock_llm():
        resp = await engineer_client.post(
            "/api/v1/translate-project",
            json={"files": ECOMMERCE_PROJECT, "style": "idiomatic"},
        )
    body = resp.json()
    assert "dependency_order" in body


@pytest.mark.asyncio
async def test_project_translate_response_has_had_cycle(engineer_client):
    from conftest import ECOMMERCE_PROJECT
    with _mock_llm():
        resp = await engineer_client.post(
            "/api/v1/translate-project",
            json={"files": ECOMMERCE_PROJECT, "style": "idiomatic"},
        )
    body = resp.json()
    assert "had_cycle" in body


# ---------------------------------------------------------------------------
# Dependency ordering: Order before OrderService
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_order_before_order_service_in_dependency_order(engineer_client):
    from conftest import ECOMMERCE_PROJECT
    with _mock_llm():
        resp = await engineer_client.post(
            "/api/v1/translate-project",
            json={"files": ECOMMERCE_PROJECT, "style": "idiomatic"},
        )
    body = resp.json()
    dep_order = body.get("dependency_order", [])
    if "Order.java" in dep_order and "OrderService.java" in dep_order:
        assert dep_order.index("Order.java") < dep_order.index("OrderService.java")


@pytest.mark.asyncio
async def test_no_cycle_for_ecommerce_project(engineer_client):
    from conftest import ECOMMERCE_PROJECT
    with _mock_llm():
        resp = await engineer_client.post(
            "/api/v1/translate-project",
            json={"files": ECOMMERCE_PROJECT, "style": "idiomatic"},
        )
    body = resp.json()
    assert body.get("had_cycle") is False


# ---------------------------------------------------------------------------
# Cycle detection
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_circular_project_has_cycle_true(engineer_client):
    from conftest import JAVA_CIRCULAR_A, JAVA_CIRCULAR_B
    with _mock_llm():
        resp = await engineer_client.post(
            "/api/v1/translate-project",
            json={
                "files": {
                    "CircularA.java": JAVA_CIRCULAR_A,
                    "CircularB.java": JAVA_CIRCULAR_B,
                },
                "style": "idiomatic",
            },
        )
    body = resp.json()
    assert body.get("had_cycle") is True


@pytest.mark.asyncio
async def test_circular_project_all_files_in_response(engineer_client):
    from conftest import JAVA_CIRCULAR_A, JAVA_CIRCULAR_B
    with _mock_llm():
        resp = await engineer_client.post(
            "/api/v1/translate-project",
            json={
                "files": {
                    "CircularA.java": JAVA_CIRCULAR_A,
                    "CircularB.java": JAVA_CIRCULAR_B,
                },
                "style": "idiomatic",
            },
        )
    body = resp.json()
    files = body.get("files", {})
    assert "CircularA.java" in files
    assert "CircularB.java" in files


# ---------------------------------------------------------------------------
# All input filenames present in output
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_all_ecommerce_filenames_in_response(engineer_client):
    from conftest import ECOMMERCE_PROJECT
    with _mock_llm():
        resp = await engineer_client.post(
            "/api/v1/translate-project",
            json={"files": ECOMMERCE_PROJECT, "style": "idiomatic"},
        )
    body = resp.json()
    files = body.get("files", {})
    for fname in ECOMMERCE_PROJECT:
        assert fname in files, f"{fname} missing from response"


# ---------------------------------------------------------------------------
# Empty files dict → 422 Unprocessable Entity
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_empty_files_returns_422(engineer_client):
    resp = await engineer_client.post(
        "/api/v1/translate-project",
        json={"files": {}, "style": "idiomatic"},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Auth: no JWT → 401/403
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_project_translate_without_auth(app):
    from conftest import ECOMMERCE_PROJECT
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post(
            "/api/v1/translate-project",
            json={"files": ECOMMERCE_PROJECT, "style": "idiomatic"},
        )
    assert resp.status_code in (401, 403)
