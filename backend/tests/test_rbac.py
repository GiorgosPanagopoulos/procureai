import uuid

import pytest
from api.routes.auth import router as auth_router
from core.rbac import require_procurement_officer, require_viewer
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient


def _make_rbac_app() -> FastAPI:
    app = FastAPI()
    app.include_router(auth_router)

    @app.get("/read-only")
    async def read_only(_user: dict = Depends(require_viewer)):
        return {"ok": True}

    @app.post("/write-action")
    async def write_action(_user: dict = Depends(require_procurement_officer)):
        return {"ok": True}

    return app


@pytest.fixture
async def rbac_client():
    transport = ASGITransport(app=_make_rbac_app())
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _extract_token(response) -> str:
    for header in response.headers.multi_items():
        if header[0].lower() == "set-cookie" and "access_token=" in header[1]:
            return header[1].split(";")[0].split("=", 1)[1]
    return ""


async def _register(client: AsyncClient, role: str = "viewer") -> str:
    unique = uuid.uuid4().hex[:8]
    res = await client.post(
        "/auth/register",
        json={
            "email": f"rbac_{unique}@procureai.test",
            "password": "TestPass123!",  # pragma: allowlist secret
            "full_name": "RBAC Test",
            "role": role,
        },
    )
    assert res.status_code == 200, res.text
    return _extract_token(res)


@pytest.mark.asyncio
async def test_viewer_can_read(rbac_client: AsyncClient):
    token = await _register(rbac_client, role="viewer")
    res = await rbac_client.get("/read-only", headers={"Cookie": f"access_token={token}"})
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_viewer_cannot_post(rbac_client: AsyncClient):
    token = await _register(rbac_client, role="viewer")
    res = await rbac_client.post("/write-action", headers={"Cookie": f"access_token={token}"})
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_procurement_officer_can_post(rbac_client: AsyncClient):
    token = await _register(rbac_client, role="procurement_officer")
    res = await rbac_client.post("/write-action", headers={"Cookie": f"access_token={token}"})
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_procurement_officer_can_read(rbac_client: AsyncClient):
    token = await _register(rbac_client, role="procurement_officer")
    res = await rbac_client.get("/read-only", headers={"Cookie": f"access_token={token}"})
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_unauthenticated_cannot_post(rbac_client: AsyncClient):
    res = await rbac_client.post("/write-action")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_invalid_role_rejected_at_registration(rbac_client: AsyncClient):
    res = await rbac_client.post(
        "/auth/register",
        json={
            "email": "bad_role@procureai.test",
            "password": "TestPass123!",  # pragma: allowlist secret
            "full_name": "Bad Role",
            "role": "superuser",
        },
    )
    assert res.status_code == 422
