from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from middleware.correlation import CorrelationIDMiddleware


def _make_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(CorrelationIDMiddleware)

    @app.get("/ping")
    async def ping():
        return {"ok": True}

    return app


async def test_correlation_id_present():
    transport = ASGITransport(app=_make_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/ping")
    assert "x-correlation-id" in res.headers


async def test_correlation_id_is_uuid_format():
    transport = ASGITransport(app=_make_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/ping")
    cid = res.headers["x-correlation-id"]
    assert len(cid) == 36
    assert cid.count("-") == 4


async def test_sequential_requests_different_ids():
    transport = ASGITransport(app=_make_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res1 = await client.get("/ping")
        res2 = await client.get("/ping")
    assert res1.headers["x-correlation-id"] != res2.headers["x-correlation-id"]
