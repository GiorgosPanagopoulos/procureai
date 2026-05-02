import uuid

import pytest
from fastapi import Depends, FastAPI
from httpx import AsyncClient, ASGITransport

from api.routes.auth import router as auth_router
from auth.dependencies import get_current_user


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(auth_router)

    @app.get("/suppliers")
    async def suppliers(_user: dict = Depends(get_current_user)):
        return []

    return app


@pytest.fixture
async def client():
    transport = ASGITransport(app=_make_app())
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def test_user():
    unique = uuid.uuid4().hex[:8]
    return {
        "email": f"test_{unique}@procureai.test",
        "password": "TestPass123!",
        "full_name": "Test User",
    }
