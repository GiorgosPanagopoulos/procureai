import os

# Must run before anything imports config/db - settings.MONGODB_URI is read
# once at import time, and backend/.env points at a real Atlas cluster.
# Tests must never be able to reach it, even by accident.
os.environ["MONGODB_URI"] = "mongodb://test-mongo-should-not-be-used.invalid:27017/procureai_test"
os.environ["ANONYMIZED_TELEMETRY"] = "False"

import uuid
from types import SimpleNamespace
from typing import Optional

import db as db_module
import pytest
from api.routes.auth import router as auth_router
from auth.dependencies import get_current_user
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient


class _FakeCollection:
    """Minimal in-memory stand-in for an AsyncIOMotorCollection.

    Same hand-rolled style as tests/test_audit.py::_mock_db. Only
    implements what crud/user.py actually calls: find_one with an
    equality filter, and insert_one.
    """

    def __init__(self):
        self._docs: list[dict] = []

    async def find_one(self, filt: dict) -> Optional[dict]:
        for doc in self._docs:
            if all(doc.get(k) == v for k, v in filt.items()):
                return doc
        return None

    async def insert_one(self, doc: dict):
        self._docs.append(doc)
        return SimpleNamespace(inserted_id=doc.get("_id"))

    def reset(self) -> None:
        self._docs.clear()


class _FakeDB:
    def __init__(self):
        self.users = _FakeCollection()


class _FakeMongoClient:
    def __init__(self):
        self.procureai = _FakeDB()


# db.mongo_client is a LazyProxy(_create_mongo_client) built once at db.py
# import time (see utils/lazy.py): _lazy_proxy(factory) closes over the
# factory *function object* itself in self._factory, so monkeypatching the
# module-level name db._create_mongo_client afterwards has no effect on
# the already-constructed proxy - it would still call the real factory.
# We patch the proxy instance's own _factory attribute instead. db.db
# (the AsyncIOMotorDatabase proxy) doesn't need patching separately: its
# factory (_get_db) just returns `mongo_client.procureai`, so once
# mongo_client resolves to the fake client, db resolves to the fake db.
#
# _obj caches on the proxy instance for the whole process, so this only
# actually runs once (on the first test's first db access) regardless of
# which test triggers it - per-test isolation comes from clearing the
# fake's contents, not from recreating the proxy.
_fake_mongo_client = _FakeMongoClient()


@pytest.fixture(autouse=True)
def fake_mongo(monkeypatch):
    monkeypatch.setattr(db_module.mongo_client, "_factory", lambda: _fake_mongo_client)
    _fake_mongo_client.procureai.users.reset()
    yield
    _fake_mongo_client.procureai.users.reset()


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
