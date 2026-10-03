from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from routers.health import router as health_router


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(health_router)
    return app


async def test_health_returns_200():
    transport = ASGITransport(app=_make_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/")
    assert res.status_code == 200


async def test_health_response_has_required_keys():
    transport = ASGITransport(app=_make_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/")
    data = res.json()
    assert "message" in data
    assert "version" in data
    assert data["version"] == "4.0.0"


async def test_liveness_returns_ok():
    transport = ASGITransport(app=_make_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


async def test_readiness_ok_when_mongo_pings():
    mock_db = MagicMock()
    mock_db.command = AsyncMock(return_value={"ok": 1})
    transport = ASGITransport(app=_make_app())
    with patch("routers.health.db", new=mock_db):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/health/ready")
    assert res.status_code == 200
    assert res.json() == {"status": "ready", "checks": {"mongo": "ok"}}
    mock_db.command.assert_awaited_once_with("ping")


async def test_readiness_degraded_when_mongo_fails():
    mock_db = MagicMock()
    mock_db.command = AsyncMock(side_effect=TimeoutError("server selection timeout"))
    transport = ASGITransport(app=_make_app())
    with patch("routers.health.db", new=mock_db):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/health/ready")
    assert res.status_code == 503
    assert res.json() == {"status": "degraded", "checks": {"mongo": "error: TimeoutError"}}
