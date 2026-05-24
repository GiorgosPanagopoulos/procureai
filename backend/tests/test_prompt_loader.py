"""
Tests for PromptLoader.

Strategy:
- Unit tests use a tmp_path-scoped PromptLoader so the real prompts directory
  is never modified and tests are fully isolated.
- The singleton `prompt_loader` exported from core.prompt_loader is tested only
  for the 5 expected production use cases.
- HTTP tests build a minimal FastAPI app with dependency overrides and patch
  `routers.admin.prompt_loader` to avoid touching the filesystem.
"""

import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from core.prompt_loader import (
    DEFAULT_PROMPT_VERSION,
    LoadedPrompt,
    PromptLoader,
    PromptMetadata,
    prompt_loader,
)
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

# ── helpers ───────────────────────────────────────────────────────────────────


def _write_prompt(base: Path, use_case: str, version: str, text: str, **meta) -> Path:
    """Write a well-formed prompt file to tmp_path and return the file path."""
    uc_dir = base / use_case
    uc_dir.mkdir(parents=True, exist_ok=True)
    created = meta.get("created", "2026-01-15")
    description = meta.get("description", f"Test prompt for {use_case}")
    content = (
        f"# use_case: {use_case}\n"
        f"# version: {version}\n"
        f"# created: {created}\n"
        f"# description: {description}\n"
        f"---\n"
        f"{text}"
    )
    path = uc_dir / f"{version}.txt"
    path.write_text(content, encoding="utf-8")
    return path


def _make_admin_user() -> dict:
    return {"_id": uuid.uuid4().hex, "role": "admin", "email": "admin@test.com"}


# ── loading ───────────────────────────────────────────────────────────────────


def test_all_five_production_prompts_load():
    expected = {"chat", "doc_qa", "tender_generation", "risk_assessment", "legal_validation"}
    assert expected.issubset(set(prompt_loader.list_use_cases()))


def test_all_production_prompts_have_v1():
    for uc in ("chat", "doc_qa", "tender_generation", "risk_assessment", "legal_validation"):
        assert "v1" in prompt_loader.list_versions(uc), f"v1 missing for {uc}"


# ── metadata parsing ──────────────────────────────────────────────────────────


def test_metadata_parsed_correctly(tmp_path):
    _write_prompt(
        tmp_path,
        "chat",
        "v1",
        "Hello world",
        created="2026-03-01",
        description="My description",
    )
    loader = PromptLoader(tmp_path)
    lp = loader.get_with_metadata("chat")

    assert lp.metadata.use_case == "chat"
    assert lp.metadata.version == "v1"
    assert lp.metadata.created == "2026-03-01"
    assert lp.metadata.description == "My description"


def test_version_inferred_from_filename(tmp_path):
    _write_prompt(tmp_path, "doc_qa", "v2", "v2 content")
    loader = PromptLoader(tmp_path)
    assert loader.get("doc_qa", "v2") == "v2 content"
    assert loader.get_with_metadata("doc_qa", "v2").metadata.version == "v2"


# ── get() strips metadata header ──────────────────────────────────────────────


def test_get_returns_text_without_metadata_header(tmp_path):
    _write_prompt(tmp_path, "chat", "v1", "Actual prompt text here.")
    loader = PromptLoader(tmp_path)
    text = loader.get("chat")
    assert text == "Actual prompt text here."
    assert "#" not in text
    assert "---" not in text
    assert "use_case" not in text


def test_get_supports_greek_characters(tmp_path):
    greek_text = "Βοηθός δημοσίων συμβάσεων για ελληνικό δημόσιο τομέα."
    _write_prompt(tmp_path, "chat", "v1", greek_text)
    loader = PromptLoader(tmp_path)
    assert loader.get("chat") == greek_text


# ── error cases ───────────────────────────────────────────────────────────────


def test_unknown_use_case_raises_value_error(tmp_path):
    _write_prompt(tmp_path, "chat", "v1", "text")
    loader = PromptLoader(tmp_path)
    with pytest.raises(ValueError, match="nonexistent"):
        loader.get("nonexistent")


def test_unknown_version_raises_value_error(tmp_path):
    _write_prompt(tmp_path, "chat", "v1", "text")
    loader = PromptLoader(tmp_path)
    with pytest.raises(ValueError, match="v99"):
        loader.get("chat", "v99")


def test_get_with_metadata_unknown_raises_value_error(tmp_path):
    loader = PromptLoader(tmp_path)
    with pytest.raises(ValueError):
        loader.get_with_metadata("missing", "v1")


# ── list helpers ──────────────────────────────────────────────────────────────


def test_list_versions_returns_correct_versions(tmp_path):
    _write_prompt(tmp_path, "chat", "v1", "a")
    _write_prompt(tmp_path, "chat", "v2", "b")
    loader = PromptLoader(tmp_path)
    assert loader.list_versions("chat") == ["v1", "v2"]


def test_list_versions_empty_for_unknown_use_case(tmp_path):
    loader = PromptLoader(tmp_path)
    assert loader.list_versions("ghost") == []


def test_list_use_cases_returns_all_five(tmp_path):
    for uc in ("chat", "doc_qa", "tender_generation", "risk_assessment", "legal_validation"):
        _write_prompt(tmp_path, uc, "v1", f"{uc} text")
    loader = PromptLoader(tmp_path)
    assert set(loader.list_use_cases()) == {
        "chat",
        "doc_qa",
        "tender_generation",
        "risk_assessment",
        "legal_validation",
    }


# ── reload ────────────────────────────────────────────────────────────────────


def test_reload_re_reads_from_disk(tmp_path):
    path = _write_prompt(tmp_path, "chat", "v1", "Original content")
    loader = PromptLoader(tmp_path)
    assert loader.get("chat") == "Original content"

    path.write_text(
        "# use_case: chat\n# version: v1\n# created: 2026-01-01\n# description: t\n---\nModified content",
        encoding="utf-8",
    )
    loader.reload()
    assert loader.get("chat") == "Modified content"


# ── missing separator ─────────────────────────────────────────────────────────


def test_no_separator_treats_entire_file_as_text(tmp_path):
    uc_dir = tmp_path / "chat"
    uc_dir.mkdir()
    (uc_dir / "v1.txt").write_text("Just the prompt text.", encoding="utf-8")
    loader = PromptLoader(tmp_path)
    assert loader.get("chat") == "Just the prompt text."
    lp = loader.get_with_metadata("chat")
    assert lp.metadata.created == ""
    assert lp.metadata.description == ""


def test_lenient_header_skips_non_matching_lines(tmp_path):
    uc_dir = tmp_path / "doc_qa"
    uc_dir.mkdir()
    content = (
        "# use_case: doc_qa\n"
        "# version: v1\n"
        "this line has no colon\n"
        "# created: 2026-05-01\n"
        "# description: OK\n"
        "---\n"
        "Body text."
    )
    (uc_dir / "v1.txt").write_text(content, encoding="utf-8")
    loader = PromptLoader(tmp_path)
    lp = loader.get_with_metadata("doc_qa")
    assert lp.metadata.created == "2026-05-01"
    assert lp.text == "Body text."


# ── DEFAULT_PROMPT_VERSION constant ──────────────────────────────────────────


def test_default_prompt_version_constant():
    assert DEFAULT_PROMPT_VERSION == "v1"


def test_get_uses_default_version(tmp_path):
    _write_prompt(tmp_path, "chat", "v1", "default text")
    loader = PromptLoader(tmp_path)
    assert loader.get("chat") == loader.get("chat", DEFAULT_PROMPT_VERSION)


# ── empty prompts directory ───────────────────────────────────────────────────


def test_empty_prompts_dir_is_handled_gracefully(tmp_path):
    loader = PromptLoader(tmp_path)
    assert loader.list_use_cases() == []


def test_nonexistent_prompts_dir_is_handled_gracefully(tmp_path):
    loader = PromptLoader(tmp_path / "does_not_exist")
    assert loader.list_use_cases() == []


# ── HTTP admin endpoint tests ─────────────────────────────────────────────────


def _make_test_app(admin_user=None) -> FastAPI:
    from core.rbac import require_admin
    from routers.admin import router as admin_router

    app = FastAPI()
    app.include_router(admin_router)
    if admin_user:
        app.dependency_overrides[require_admin] = lambda: admin_user
    return app


def _fake_loader(use_cases=("chat", "doc_qa"), version="v1") -> MagicMock:
    """Return a mock PromptLoader pre-configured with the given use_cases."""
    mock = MagicMock()
    mock.list_use_cases.return_value = list(use_cases)
    mock.list_versions.side_effect = lambda uc: [version] if uc in use_cases else []

    def _get_with_meta(uc, v=version):
        if uc not in use_cases or v != version:
            raise ValueError(f"Prompt '{uc}/{v}' not found.")
        return LoadedPrompt(
            metadata=PromptMetadata(
                use_case=uc,
                version=v,
                created="2026-01-15",
                description=f"Description for {uc}",
            ),
            text=f"Prompt text for {uc}",
        )

    mock.get_with_metadata.side_effect = _get_with_meta
    return mock


@pytest.mark.asyncio
async def test_non_admin_gets_403_on_list_prompts():
    app = _make_test_app()  # no override → real RBAC, no auth token → 401/403
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/admin/prompts")
    assert res.status_code in (401, 403)


@pytest.mark.asyncio
async def test_non_admin_gets_403_on_get_prompt():
    app = _make_test_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/admin/prompts/chat/v1")
    assert res.status_code in (401, 403)


@pytest.mark.asyncio
async def test_admin_list_prompts_returns_metadata():
    admin = _make_admin_user()
    app = _make_test_app(admin_user=admin)
    fake = _fake_loader(use_cases=("chat", "doc_qa"))

    with (
        patch("routers.admin.prompt_loader", fake),
        patch("routers.admin.audit_interaction"),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/admin/prompts")

    assert res.status_code == 200
    body = res.json()
    use_case_names = {p["use_case"] for p in body["prompts"]}
    assert "chat" in use_case_names
    assert "doc_qa" in use_case_names
    first = next(p for p in body["prompts"] if p["use_case"] == "chat")
    assert "v1" in first["versions"]
    assert first["metadata"]["v1"]["use_case"] == "chat"
    assert first["metadata"]["v1"]["description"] == "Description for chat"


@pytest.mark.asyncio
async def test_admin_get_prompt_returns_text_and_metadata():
    admin = _make_admin_user()
    app = _make_test_app(admin_user=admin)
    fake = _fake_loader(use_cases=("chat",))

    with (
        patch("routers.admin.prompt_loader", fake),
        patch("routers.admin.audit_interaction"),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/admin/prompts/chat/v1")

    assert res.status_code == 200
    body = res.json()
    assert body["text"] == "Prompt text for chat"
    assert body["metadata"]["use_case"] == "chat"
    assert body["metadata"]["version"] == "v1"
    assert body["metadata"]["created"] == "2026-01-15"


@pytest.mark.asyncio
async def test_admin_get_prompt_404_for_unknown():
    admin = _make_admin_user()
    app = _make_test_app(admin_user=admin)
    fake = _fake_loader(use_cases=("chat",))

    with (
        patch("routers.admin.prompt_loader", fake),
        patch("routers.admin.audit_interaction"),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/admin/prompts/nonexistent/v1")

    assert res.status_code == 404


@pytest.mark.asyncio
async def test_admin_list_prompts_triggers_audit():
    admin = _make_admin_user()
    app = _make_test_app(admin_user=admin)
    fake = _fake_loader()
    captured = []

    def fake_audit(db, entry):
        captured.append(entry)

    with (
        patch("routers.admin.prompt_loader", fake),
        patch("routers.admin.audit_interaction", side_effect=fake_audit),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            await ac.get("/admin/prompts")

    assert len(captured) == 1
    assert captured[0].action == "view_prompt"
    assert captured[0].user_id == admin["_id"]
