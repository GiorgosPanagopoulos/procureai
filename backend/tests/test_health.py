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
