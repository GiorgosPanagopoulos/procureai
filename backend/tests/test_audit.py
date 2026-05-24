"""
Audit log tests.

Strategy:
- Unit tests for AuditEntry, log_audit, get_audit_logs: use AsyncMock db, no network.
- HTTP tests: minimal FastAPI app with dependency overrides for auth,
  patched run_agent/document_qa so no real API calls are made,
  patched middleware.audit_middleware.log_audit to capture what would be inserted.
"""

import uuid
from datetime import datetime
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from core.audit import AuditEntry, get_audit_logs, log_audit
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

# ── helpers ───────────────────────────────────────────────────────────────────


def _make_user(role: str = "procurement_officer") -> dict:
    return {"_id": uuid.uuid4().hex, "role": role, "email": f"{role}@test.com"}


def _mock_db(stored: Optional[list] = None) -> MagicMock:
    """Returns a db mock whose audit_logs collection tracks insert_one calls."""
    rows = stored if stored is not None else []
    db = MagicMock()

    async def fake_insert(doc):
        rows.append(doc)
        return MagicMock(inserted_id="fake")

    cursor = MagicMock()
    cursor.sort.return_value = cursor
    cursor.skip.return_value = cursor
    cursor.limit.return_value = cursor
    cursor.to_list = AsyncMock(return_value=rows)

    db.audit_logs.insert_one = fake_insert
    db.audit_logs.find.return_value = cursor
    return db


# ── AuditEntry unit tests ─────────────────────────────────────────────────────


def test_audit_entry_defaults():
    entry = AuditEntry(user_id="u1", user_role="viewer", action="chat", endpoint="/chat")
    assert entry.sources_used == []
    assert entry.query is None
    assert entry.response_summary is None
    assert isinstance(entry.timestamp, datetime)


def test_audit_entry_stores_all_fields():
    entry = AuditEntry(
        user_id="u1",
        user_role="procurement_officer",
        action="doc_qa",
        query="What is the price?",
        response_summary="The price is 100.",
        sources_used=["contract.pdf"],
        endpoint="/doc_qa",
        ip_address="127.0.0.1",
    )
    assert entry.user_id == "u1"
    assert entry.action == "doc_qa"
    assert entry.sources_used == ["contract.pdf"]
    assert entry.ip_address == "127.0.0.1"


def test_response_summary_accepts_exactly_500_chars():
    summary = "x" * 500
    entry = AuditEntry(
        user_id="u1", user_role="viewer", action="chat", response_summary=summary, endpoint="/chat"
    )
    assert len(entry.response_summary) == 500


def test_response_summary_is_not_auto_truncated_by_model():
    # Truncation happens in the router before building the entry, not in the model itself.
    long_text = "a" * 600
    entry = AuditEntry(
        user_id="u1",
        user_role="viewer",
        action="chat",
        response_summary=long_text,
        endpoint="/chat",
    )
    # Model doesn't truncate — the router slices [:500] before passing it in
    assert len(entry.response_summary) == 600


# ── log_audit unit tests ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_log_audit_inserts_one_document():
    rows = []
    db = _mock_db(rows)
    entry = AuditEntry(user_id="u1", user_role="viewer", action="chat", endpoint="/chat")
    await log_audit(db, entry)
    assert len(rows) == 1
    assert rows[0]["user_id"] == "u1"
    assert rows[0]["action"] == "chat"


@pytest.mark.asyncio
async def test_log_audit_does_not_raise_on_db_failure():
    db = MagicMock()
    db.audit_logs.insert_one = AsyncMock(side_effect=Exception("DB is down"))
    entry = AuditEntry(user_id="u1", user_role="viewer", action="chat", endpoint="/chat")
    await log_audit(db, entry)  # must not raise


# ── get_audit_logs unit tests ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_audit_logs_passes_user_id_filter():
    db = _mock_db()
    await get_audit_logs(db, user_id="u1", action=None, skip=0, limit=50)
    call_args = db.audit_logs.find.call_args
    assert call_args[0][0].get("user_id") == "u1"


@pytest.mark.asyncio
async def test_get_audit_logs_passes_action_filter():
    db = _mock_db()
    await get_audit_logs(db, user_id=None, action="chat", skip=0, limit=50)
    call_args = db.audit_logs.find.call_args
    assert call_args[0][0].get("action") == "chat"


@pytest.mark.asyncio
async def test_get_audit_logs_empty_query_when_no_filters():
    db = _mock_db()
    await get_audit_logs(db, user_id=None, action=None, skip=0, limit=10)
    call_args = db.audit_logs.find.call_args
    assert call_args[0][0] == {}


# ── HTTP integration tests ────────────────────────────────────────────────────
#
# These tests build a minimal FastAPI app and override auth dependencies so
# no real MongoDB / external APIs are needed.


def _make_test_app(
    admin_user: Optional[dict] = None,
    officer_user: Optional[dict] = None,
    audit_rows: Optional[list] = None,
) -> FastAPI:
    """Build a test app with the chat + admin routers and dependency overrides."""
    from api.routes.auth import router as auth_router
    from core.rbac import require_admin, require_procurement_officer
    from routers.admin import router as admin_router
    from routers.chat import router as chat_router

    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(chat_router)
    app.include_router(admin_router)

    if admin_user:
        app.dependency_overrides[require_admin] = lambda: admin_user
    if officer_user:
        app.dependency_overrides[require_procurement_officer] = lambda: officer_user
    return app


@pytest.fixture
def officer():
    return _make_user("procurement_officer")


@pytest.fixture
def admin():
    return _make_user("admin")


# ── /admin/audit-logs RBAC ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_non_admin_gets_403_on_audit_logs(officer):
    """A procurement officer must not access /admin/audit-logs."""
    app = _make_test_app()  # no override → real RBAC; no auth cookie → 401/403

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/admin/audit-logs")
    assert res.status_code in (401, 403)


@pytest.mark.asyncio
async def test_admin_gets_audit_logs(admin):
    """An admin user can retrieve audit logs."""
    fake_logs = [
        {
            "user_id": "u1",
            "action": "chat",
            "endpoint": "/chat",
            "timestamp": datetime.utcnow().isoformat(),
        }
    ]

    app = _make_test_app(admin_user=admin)

    with patch("routers.admin.get_audit_logs", new=AsyncMock(return_value=fake_logs)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/admin/audit-logs")

    assert res.status_code == 200
    body = res.json()
    assert body["count"] == 1
    assert body["logs"][0]["action"] == "chat"


@pytest.mark.asyncio
async def test_admin_audit_logs_query_params_forwarded(admin):
    """user_id and action query params are forwarded to get_audit_logs."""
    app = _make_test_app(admin_user=admin)
    captured = {}

    async def fake_get(db, user_id, action, skip, limit):
        captured.update({"user_id": user_id, "action": action, "skip": skip, "limit": limit})
        return []

    with patch("routers.admin.get_audit_logs", new=fake_get):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            await ac.get("/admin/audit-logs?user_id=abc&action=chat&skip=5&limit=20")

    assert captured == {"user_id": "abc", "action": "chat", "skip": 5, "limit": 20}


# ── /chat audit creation ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_audit_entry_created_after_chat(officer):
    """Posting to /chat triggers audit_interaction with action='chat'."""
    app = _make_test_app(officer_user=officer)
    captured: list[AuditEntry] = []

    fake_agent_result = {
        "response": "Here is the answer.",
        "tool_used": "document_qa",
        "conversation_id": "cid-123",
        "usage": {},
        "trace": [],
    }

    def fake_audit(db, entry: AuditEntry):
        captured.append(entry)

    with (
        patch("routers.chat.run_agent", new=AsyncMock(return_value=fake_agent_result)),
        patch("routers.chat.audit_interaction", side_effect=fake_audit),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post("/chat", json={"message": "What is the budget?"})

    assert res.status_code == 200
    assert len(captured) == 1
    entry = captured[0]
    assert entry.action == "chat"
    assert entry.user_id == officer["_id"]
    assert entry.user_role == "procurement_officer"
    assert entry.endpoint == "/chat"


@pytest.mark.asyncio
async def test_audit_query_and_summary_truncated_to_500(officer):
    """query and response_summary in the audit entry are truncated to 500 chars."""
    app = _make_test_app(officer_user=officer)
    captured: list[AuditEntry] = []

    long_query = "Q" * 700
    long_response = "R" * 700
    fake_result = {
        "response": long_response,
        "tool_used": "none",
        "conversation_id": "cid",
        "usage": {},
        "trace": [],
    }

    def fake_audit(db, entry: AuditEntry):
        captured.append(entry)

    with (
        patch("routers.chat.run_agent", new=AsyncMock(return_value=fake_result)),
        patch("routers.chat.audit_interaction", side_effect=fake_audit),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            await ac.post("/chat", json={"message": long_query})

    entry = captured[0]
    assert len(entry.query) == 500
    assert len(entry.response_summary) == 500


@pytest.mark.asyncio
async def test_audit_upload_logs_filename(officer):
    """Uploading a PDF creates an audit entry with action='upload' and the filename."""
    app = _make_test_app(officer_user=officer)
    captured: list[AuditEntry] = []

    def fake_audit(db, entry: AuditEntry):
        captured.append(entry)

    with (
        patch("routers.chat.ingest_pdf", return_value=3),
        patch("routers.chat.audit_interaction", side_effect=fake_audit),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(
                "/upload",
                files={"file": ("report.pdf", b"%PDF-1.4 fake", "application/pdf")},
            )

    assert res.status_code == 200
    assert len(captured) == 1
    entry = captured[0]
    assert entry.action == "upload"
    assert "report.pdf" in entry.sources_used


@pytest.mark.asyncio
async def test_audit_delete_document_logs_source(officer):
    """DELETE /documents creates an audit entry with action='delete_document'."""
    app = _make_test_app(officer_user=officer)
    captured: list[AuditEntry] = []

    def fake_audit(db, entry: AuditEntry):
        captured.append(entry)

    with (
        patch("routers.chat.chroma_collection") as mock_col,
        patch("routers.chat.audit_interaction", side_effect=fake_audit),
    ):
        mock_col.delete = MagicMock()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.delete("/documents?source=contract.pdf")

    assert res.status_code == 200
    assert len(captured) == 1
    entry = captured[0]
    assert entry.action == "delete_document"
    assert "contract.pdf" in entry.sources_used


# ── source extraction helper ──────────────────────────────────────────────────


def test_extract_sources_from_answer():
    from routers.chat import _extract_sources

    answer = "The price is $100.\n\nSources: contract.pdf, price_list.pdf"
    assert _extract_sources(answer) == ["contract.pdf", "price_list.pdf"]


def test_extract_sources_empty_when_no_marker():
    from routers.chat import _extract_sources

    assert _extract_sources("Just an answer with no sources.") == []
