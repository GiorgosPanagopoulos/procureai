import os

# Must run before anything imports config/db - settings.MONGODB_URI is read
# once at import time, and backend/.env points at a real Atlas cluster.
# Tests must never be able to reach it, even by accident.
os.environ["MONGODB_URI"] = "mongodb://test-mongo-should-not-be-used.invalid:27017/procureai_test"
os.environ["ANONYMIZED_TELEMETRY"] = "False"

import uuid
from types import SimpleNamespace
from typing import Any, Optional

import db as db_module
import pytest
from api.routes.auth import router as auth_router
from auth.dependencies import get_current_user
from auth.security import create_access_token
from crud.user import create_user
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from schemas.user import UserCreate


class _FakeCollection:
    """Minimal in-memory stand-in for an AsyncIOMotorCollection.

    Same hand-rolled style as tests/test_audit.py::_mock_db. Only
    implements what the code under test calls: find_one with an
    equality filter, insert_one, count_documents, update_one /
    find_one_and_update ($set / $inc / $setOnInsert, upsert;
    find_one_and_update returns the updated doc), create_index
    (recorded, not enforced), and aggregate with a single ungrouped
    $group stage ($sum / $avg).
    """

    def __init__(self):
        self._docs: list[dict] = []
        self.indexes: list[tuple[Any, dict]] = []

    async def find_one(self, filt: dict) -> Optional[dict]:
        for doc in self._docs:
            if all(doc.get(k) == v for k, v in filt.items()):
                return doc
        return None

    async def insert_one(self, doc: dict):
        self._docs.append(doc)
        return SimpleNamespace(inserted_id=doc.get("_id"))

    async def find_one_and_update(
        self, filt: dict, update: dict, upsert: bool = False, **_kwargs
    ) -> Optional[dict]:
        doc = await self.find_one(filt)
        if doc is None:
            if not upsert:
                return None
            doc = {**filt, **update.get("$setOnInsert", {})}
            self._docs.append(doc)
        doc.update(update.get("$set", {}))
        for key, amount in update.get("$inc", {}).items():
            doc[key] = doc.get(key, 0) + amount
        return dict(doc)

    async def update_one(self, filt: dict, update: dict, upsert: bool = False):
        doc = await self.find_one_and_update(filt, update, upsert=upsert)
        return SimpleNamespace(matched_count=int(doc is not None))

    async def create_index(self, keys: Any, **kwargs) -> str:
        self.indexes.append((keys, kwargs))
        return str(keys)

    async def count_documents(self, filt: dict) -> int:
        return sum(1 for doc in self._docs if all(doc.get(k) == v for k, v in filt.items()))

    def aggregate(self, pipeline: list[dict]) -> "_FakeCursor":
        (stage,) = pipeline
        spec = stage["$group"]
        assert spec["_id"] is None, "fake only supports ungrouped $group"
        if not self._docs:
            return _FakeCursor([])
        row: dict = {"_id": None}
        for name, expr in spec.items():
            if name == "_id":
                continue
            (op, arg) = next(iter(expr.items()))
            values: list[Any] = [
                arg if not isinstance(arg, str) else d.get(arg[1:]) for d in self._docs
            ]
            if op == "$sum":
                row[name] = sum(values)
            elif op == "$avg":
                row[name] = sum(values) / len(values)
            else:
                raise NotImplementedError(op)
        return _FakeCursor([row])

    def reset(self) -> None:
        self._docs.clear()
        self.indexes.clear()


class _FakeCursor:
    def __init__(self, rows: list[dict]):
        self._rows = rows

    async def to_list(self, length: Optional[int] = None) -> list[dict]:
        return self._rows[:length] if length else list(self._rows)


class _FakeDB:
    def __init__(self):
        self.users = _FakeCollection()
        self.suppliers = _FakeCollection()
        self.bids = _FakeCollection()
        self.demo_usage = _FakeCollection()
        self.conversations = _FakeCollection()

    def reset(self) -> None:
        self.users.reset()
        self.suppliers.reset()
        self.bids.reset()
        self.demo_usage.reset()
        self.conversations.reset()


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
    _fake_mongo_client.procureai.reset()
    yield
    _fake_mongo_client.procureai.reset()


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


@pytest.fixture
def fake_db() -> _FakeDB:
    return _fake_mongo_client.procureai


@pytest.fixture
def make_user():
    """Insert a user with the given role straight through crud; returns (user, token).

    Pass is_demo=True to get a demo account.
    """

    async def _make(role: str = "viewer", **overrides) -> tuple[dict, str]:
        unique = uuid.uuid4().hex[:8]
        user_in = UserCreate(
            email=overrides.get("email", f"{role}_{unique}@procureai.test"),
            password=overrides.get("password", "TestPass123!"),  # pragma: allowlist secret
            full_name=overrides.get("full_name", f"{role} user"),
            role=role,
        )
        user = await create_user(db_module.db, user_in)
        assert user is not None
        # Same dict the fake collection stores, so this persists for later lookups.
        user["is_demo"] = overrides.get("is_demo", False)
        return user, create_access_token(subject=user["email"], role=user["role"])

    return _make
