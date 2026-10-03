"""Demo account guards: daily LLM quota and write protection.

Runs the real chat router and auth stack against the in-memory fake Mongo
from conftest; only the LLM / ingestion calls are patched out.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from api.routes.auth import router as auth_router
from config import settings
from core import demo
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from middleware.rate_limit import limiter
from routers.chat import router as chat_router

LIMIT = 3
DAY_1 = datetime(2026, 10, 3, 23, 59, tzinfo=timezone.utc)
DAY_2 = DAY_1 + timedelta(minutes=2)
NEW_PASSWORD = "TestPass123!"  # pragma: allowlist secret


@pytest.fixture(autouse=True)
def _demo_env(monkeypatch):
    monkeypatch.setattr(settings, "DEMO_DAILY_LIMIT", LIMIT)
    # The per-IP slowapi limit would otherwise interfere with the request counts here.
    monkeypatch.setattr(limiter, "enabled", False)
    monkeypatch.setattr(demo, "_utc_now", lambda: DAY_1)


@pytest.fixture(autouse=True)
def _no_llm():
    qa_tool = MagicMock()
    qa_tool.ainvoke = AsyncMock(return_value="answer")
    with (
        patch("routers.chat.run_agent", new=AsyncMock(return_value={"response": "hi"})),
        patch("routers.chat.document_qa", new=qa_tool),
        patch("routers.chat.ingest_pdf", return_value=3) as ingest,
        patch("routers.chat.delete_chunks") as delete,
        patch("routers.chat.audit_interaction"),
    ):
        yield {"ingest": ingest, "delete": delete}


@pytest.fixture
async def api():
    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(chat_router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _chat(api: AsyncClient, token: str):
    return await api.post("/chat", json={"message": "hello"}, headers=_auth(token))


@pytest.mark.asyncio
async def test_demo_quota_allows_limit_then_429(api, make_user):
    _, token = await make_user("viewer", is_demo=True)

    for _ in range(LIMIT):
        assert (await _chat(api, token)).status_code == 200

    res = await _chat(api, token)
    assert res.status_code == 429
    assert res.json()["detail"] == "Demo limit reached for today, try again tomorrow."


@pytest.mark.asyncio
async def test_chat_and_doc_qa_share_the_daily_budget(api, make_user):
    _, token = await make_user("viewer", is_demo=True)

    for _ in range(LIMIT - 1):
        assert (await _chat(api, token)).status_code == 200
    res = await api.post("/doc_qa", params={"question": "q"}, headers=_auth(token))
    assert res.status_code == 200

    res = await api.post("/doc_qa", params={"question": "q"}, headers=_auth(token))
    assert res.status_code == 429


@pytest.mark.asyncio
async def test_non_demo_users_are_not_counted(api, make_user, fake_db):
    _, token = await make_user("procurement_officer")

    for _ in range(LIMIT + 2):
        assert (await _chat(api, token)).status_code == 200
    assert await fake_db.demo_usage.count_documents({}) == 0


@pytest.mark.asyncio
async def test_quota_resets_on_next_utc_day(api, make_user, monkeypatch):
    _, token = await make_user("viewer", is_demo=True)
    for _ in range(LIMIT):
        await _chat(api, token)
    assert (await _chat(api, token)).status_code == 429

    monkeypatch.setattr(demo, "_utc_now", lambda: DAY_2)
    assert (await _chat(api, token)).status_code == 200


@pytest.mark.asyncio
async def test_quotas_are_per_user(api, make_user):
    _, first = await make_user("viewer", is_demo=True)
    _, second = await make_user("viewer", is_demo=True)
    for _ in range(LIMIT):
        await _chat(api, first)
    assert (await _chat(api, first)).status_code == 429
    assert (await _chat(api, second)).status_code == 200


@pytest.mark.asyncio
async def test_usage_doc_has_created_at_for_ttl(api, make_user, fake_db):
    user, token = await make_user("viewer", is_demo=True)
    await _chat(api, token)

    doc = await fake_db.demo_usage.find_one({"_id": f"{user['_id']}:2026-10-03"})
    assert doc is not None
    assert doc["count"] == 1
    assert doc["created_at"] == DAY_1


@pytest.mark.asyncio
async def test_plain_viewer_still_cannot_chat(api, make_user):
    _, token = await make_user("viewer")
    assert (await _chat(api, token)).status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["viewer", "procurement_officer", "admin"])
async def test_demo_user_cannot_upload_regardless_of_role(api, make_user, role, _no_llm):
    _, token = await make_user(role, is_demo=True)
    res = await api.post(
        "/upload",
        files={"file": ("x.pdf", b"%PDF-1.4 fake", "application/pdf")},
        headers=_auth(token),
    )
    assert res.status_code == 403
    _no_llm["ingest"].assert_not_called()


@pytest.mark.asyncio
async def test_demo_user_cannot_delete_documents(api, make_user, _no_llm):
    _, token = await make_user("procurement_officer", is_demo=True)
    res = await api.delete("/documents", params={"source": "a.pdf"}, headers=_auth(token))
    assert res.status_code == 403
    _no_llm["delete"].assert_not_called()


@pytest.mark.asyncio
async def test_demo_admin_cannot_register_users(api, make_user):
    _, token = await make_user("admin", is_demo=True)
    res = await api.post(
        "/auth/register",
        json={"email": "new@procureai.test", "password": NEW_PASSWORD},
        headers=_auth(token),
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_me_exposes_is_demo(api, make_user):
    _, token = await make_user("viewer", is_demo=True)
    res = await api.get("/auth/me", headers=_auth(token))
    assert res.json()["is_demo"] is True


@pytest.mark.asyncio
async def test_ttl_index_is_48h(fake_db):
    await demo.ensure_demo_indexes()
    assert fake_db.demo_usage.indexes == [("created_at", {"expireAfterSeconds": 48 * 60 * 60})]
