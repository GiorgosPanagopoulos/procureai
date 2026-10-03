"""Conversation ownership: who may read a trace, and who may continue a conversation."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from middleware.rate_limit import limiter
from routers.chat import router as chat_router

TRACE = [{"type": "tool_call", "tool": "supplier_lookup", "input": "IT"}]


@pytest.fixture(autouse=True)
def _no_rate_limit(monkeypatch):
    monkeypatch.setattr(limiter, "enabled", False)


@pytest.fixture
async def api():
    app = FastAPI()
    app.include_router(chat_router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
def add_conversation(fake_db):
    async def _add(conversation_id: str, owner: dict | None) -> None:
        doc = {"conversation_id": conversation_id, "trace": TRACE}
        if owner is not None:
            doc["user_id"] = str(owner["_id"])
        await fake_db.conversations.insert_one(doc)

    return _add


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _trace(api: AsyncClient, conversation_id: str, token: str):
    return await api.get(f"/conversations/{conversation_id}/trace", headers=_auth(token))


# ── GET /conversations/{id}/trace ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_owner_can_read_trace(api, make_user, add_conversation):
    owner, token = await make_user("procurement_officer")
    await add_conversation("c1", owner)

    res = await _trace(api, "c1", token)
    assert res.status_code == 200
    assert res.json() == {"conversation_id": "c1", "trace": TRACE}


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["viewer", "procurement_officer"])
async def test_other_users_get_404(api, make_user, add_conversation, role):
    owner, _ = await make_user("procurement_officer")
    _, other = await make_user(role)
    await add_conversation("c1", owner)

    res = await _trace(api, "c1", other)
    assert res.status_code == 404
    assert "trace" not in res.json()


@pytest.mark.asyncio
async def test_admin_can_read_any_trace(api, make_user, add_conversation):
    owner, _ = await make_user("procurement_officer")
    _, admin = await make_user("admin")
    await add_conversation("c1", owner)

    assert (await _trace(api, "c1", admin)).status_code == 200


@pytest.mark.asyncio
async def test_legacy_conversation_without_owner_is_admin_only(api, make_user, add_conversation):
    _, officer = await make_user("procurement_officer")
    _, admin = await make_user("admin")
    await add_conversation("legacy", owner=None)

    assert (await _trace(api, "legacy", officer)).status_code == 404
    assert (await _trace(api, "legacy", admin)).status_code == 200


@pytest.mark.asyncio
async def test_demo_user_cannot_read_even_the_shared_accounts_traces(
    api, make_user, add_conversation
):
    demo, token = await make_user("viewer", is_demo=True)
    await add_conversation("c1", demo)

    assert (await _trace(api, "c1", token)).status_code == 404


@pytest.mark.asyncio
async def test_missing_conversation_is_404(api, make_user):
    _, token = await make_user("admin")
    assert (await _trace(api, "nope", token)).status_code == 404


# ── POST /chat conversation ids ──────────────────────────────────────────────


@pytest.fixture
def agent():
    with (
        patch("routers.chat.run_agent", new=AsyncMock(return_value={"response": "hi"})) as run,
        patch("routers.chat.audit_interaction"),
    ):
        yield run


async def _chat(api: AsyncClient, token: str, conversation_id: str | None):
    body = {"message": "hello", "conversation_id": conversation_id}
    return await api.post("/chat", json=body, headers=_auth(token))


@pytest.mark.asyncio
async def test_chat_passes_owner_to_agent(api, make_user, agent):
    user, token = await make_user("procurement_officer")

    res = await _chat(api, token, None)

    cid = res.json()["conversation_id"]
    agent.assert_awaited_once_with("hello", cid, user_id=str(user["_id"]))


@pytest.mark.asyncio
async def test_owner_continues_own_conversation(api, make_user, add_conversation, agent):
    user, token = await make_user("procurement_officer")
    await add_conversation("c1", user)

    res = await _chat(api, token, "c1")
    assert res.json()["conversation_id"] == "c1"


@pytest.mark.asyncio
async def test_someone_elses_conversation_id_starts_a_new_one(
    api, make_user, add_conversation, agent
):
    owner, _ = await make_user("procurement_officer")
    _, intruder = await make_user("procurement_officer")
    await add_conversation("c1", owner)

    res = await _chat(api, intruder, "c1")

    new_cid = res.json()["conversation_id"]
    assert new_cid != "c1"
    assert agent.await_args.args[1] == new_cid
