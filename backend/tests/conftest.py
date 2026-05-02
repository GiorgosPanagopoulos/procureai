import asyncio
import uuid

import pytest
from httpx import AsyncClient, ASGITransport

from main import app


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
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
