import pytest
from api.routes.auth import router as auth_router
from core.rbac import require_procurement_officer, require_viewer
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

# NB: don't `from db import db` here - db.db is a LazyProxy that defines
# __call__, so pytest's collector (and the anyio plugin's istestfunction
# check) probes it for a __test__ attribute while collecting this module,
# which eagerly triggers real Mongo client construction *during
# collection*, before any fixture gets a chance to patch it in. Importing
# the module and doing the attribute lookup at call time avoids that.


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


@pytest.fixture
def register(make_user):
    async def _register(role: str = "viewer") -> str:
        _, token = await make_user(role)
        return token

    return _register


@pytest.mark.asyncio
async def test_viewer_can_read(rbac_client: AsyncClient, register):
    token = await register(role="viewer")
    res = await rbac_client.get("/read-only", headers={"Cookie": f"access_token={token}"})
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_viewer_cannot_post(rbac_client: AsyncClient, register):
    token = await register(role="viewer")
    res = await rbac_client.post("/write-action", headers={"Cookie": f"access_token={token}"})
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_procurement_officer_can_post(rbac_client: AsyncClient, register):
    token = await register(role="procurement_officer")
    res = await rbac_client.post("/write-action", headers={"Cookie": f"access_token={token}"})
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_procurement_officer_can_read(rbac_client: AsyncClient, register):
    token = await register(role="procurement_officer")
    res = await rbac_client.get("/read-only", headers={"Cookie": f"access_token={token}"})
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_unauthenticated_cannot_post(rbac_client: AsyncClient):
    res = await rbac_client.post("/write-action")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_invalid_role_rejected_at_registration(rbac_client: AsyncClient, register):
    admin_token = await register(role="admin")
    res = await rbac_client.post(
        "/auth/register",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "email": "bad_role@procureai.test",
            "password": "TestPass123!",  # pragma: allowlist secret
            "full_name": "Bad Role",
            "role": "superuser",
        },
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_viewer_cannot_register_users(rbac_client: AsyncClient, register):
    token = await register(role="viewer")
    res = await rbac_client.post(
        "/auth/register",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "email": "escalate@procureai.test",
            "password": "TestPass123!",  # pragma: allowlist secret
            "full_name": "Escalation",
            "role": "admin",
        },
    )
    assert res.status_code == 403
