import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from middleware.rate_limit import setup_rate_limit
from routers.stats import router as stats_router


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def stats_client():
    app = FastAPI()
    setup_rate_limit(app)
    app.include_router(stats_router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


def _seed(fake_db) -> None:
    fake_db.suppliers._docs.extend({"_id": f"s{i}", "name": f"Supplier {i}"} for i in range(3))
    fake_db.bids._docs.extend(
        [
            {"_id": "b1", "supplier_id": "s0", "total_price": 1000.0, "delivery_days": 10},
            {"_id": "b2", "supplier_id": "s1", "total_price": 2500.5, "delivery_days": 20},
            {"_id": "b3", "supplier_id": "s2", "total_price": 499.5, "delivery_days": 15},
            {"_id": "b4", "supplier_id": "s2", "total_price": 0.0, "delivery_days": 6},
        ]
    )


@pytest.mark.asyncio
async def test_stats_requires_auth(stats_client: AsyncClient):
    res = await stats_client.get("/stats")
    assert res.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["viewer", "procurement_officer", "admin"])
async def test_stats_any_authenticated_role(stats_client: AsyncClient, make_user, role: str):
    _, token = await make_user(role)
    res = await stats_client.get("/stats", headers=_bearer(token))
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_stats_shape_and_values(stats_client: AsyncClient, make_user, fake_db):
    _seed(fake_db)
    _, token = await make_user("viewer")
    res = await stats_client.get("/stats", headers=_bearer(token))
    assert res.status_code == 200
    assert res.json() == {
        "suppliers": 3,
        "bids": 4,
        "total_value_eur": 4000.0,
        "avg_delivery_days": 12.8,
    }


@pytest.mark.asyncio
async def test_stats_empty_collections(stats_client: AsyncClient, make_user):
    _, token = await make_user("viewer")
    res = await stats_client.get("/stats", headers=_bearer(token))
    assert res.json() == {
        "suppliers": 0,
        "bids": 0,
        "total_value_eur": 0.0,
        "avg_delivery_days": None,
    }
