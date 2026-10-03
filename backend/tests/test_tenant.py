import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

# Prevent the embedding stack from loading
sys.modules.setdefault("rag.embeddings", MagicMock())

import pytest  # noqa: E402
from core.tenant import (  # noqa: E402
    SYSTEM_USER_ID,
    _current_user_id,
    build_metadata,
    get_active_user_id,
    get_search_filter,
)
from langchain_core.documents import Document  # noqa: E402
from pymongo import ReplaceOne  # noqa: E402


def _load_vectorstore():
    """The real rag/vectorstore.py, loaded under a private name.

    Other test modules put a MagicMock at sys.modules["rag.vectorstore"] so
    agent.tools can be imported offline; whichever module is collected first
    wins, so `import rag.vectorstore` here may not be the real thing.
    """
    path = Path(__file__).resolve().parent.parent / "rag" / "vectorstore.py"
    spec = importlib.util.spec_from_file_location("_real_rag_vectorstore", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


vectorstore = _load_vectorstore()


# ── Unit tests for helper functions ───────────────────────────────────────────


def test_get_search_filter_allows_own_and_system_chunks():
    assert get_search_filter("user_abc") == {"user_id": {"$in": ["user_abc", "system"]}}


def test_build_metadata_basic():
    meta = build_metadata("user_abc", "contract.pdf")
    assert meta == {"user_id": "user_abc", "source": "contract.pdf"}


def test_build_metadata_with_extra_kwargs():
    meta = build_metadata("user_abc", "contract.pdf", chunk="0", page="1")
    assert meta == {"user_id": "user_abc", "source": "contract.pdf", "chunk": "0", "page": "1"}


def test_get_active_user_id_default_is_none():
    # In a fresh context the ContextVar has no value set
    token = _current_user_id.set(None)
    try:
        assert get_active_user_id() is None
    finally:
        _current_user_id.reset(token)


def test_get_active_user_id_returns_set_value():
    token = _current_user_id.set("user_xyz")
    try:
        assert get_active_user_id() == "user_xyz"
    finally:
        _current_user_id.reset(token)


# ── rag.vectorstore wiring (MongoDBAtlasVectorSearch mocked) ──────────────────


def test_vector_store_targets_document_chunks_index():
    client = MagicMock()
    with (
        patch.object(vectorstore, "MongoDBAtlasVectorSearch") as atlas_cls,
        patch.object(vectorstore, "vector_client", client),
    ):
        vectorstore._create_vector_store()

    kwargs = atlas_cls.call_args.kwargs
    assert kwargs["collection"] is client.procureai["document_chunks"]
    assert kwargs["index_name"] == "vector_index"
    assert kwargs["text_key"] == "text"
    assert kwargs["embedding_key"] == "embedding"
    # M0 cannot create search indexes from the driver.
    assert kwargs["auto_create_index"] is False


def test_upsert_chunks_replaces_by_id_with_flat_metadata():
    store = MagicMock()
    with patch.object(vectorstore, "vector_store", store):
        vectorstore.upsert_chunks(
            ids=["u1_a.pdf_chunk_0"],
            texts=["chunk text"],
            embeddings=[[0.1, 0.2]],
            metadatas=[build_metadata("u1", "a.pdf", chunk="0")],
        )

    ops = store.collection.bulk_write.call_args.args[0]
    assert ops == [
        ReplaceOne(
            {"_id": "u1_a.pdf_chunk_0"},
            {
                "_id": "u1_a.pdf_chunk_0",
                "text": "chunk text",
                "embedding": [0.1, 0.2],
                "user_id": "u1",
                "source": "a.pdf",
                "chunk": "0",
            },
            upsert=True,
        )
    ]


def test_upsert_chunks_skips_empty_batch():
    store = MagicMock()
    with patch.object(vectorstore, "vector_store", store):
        vectorstore.upsert_chunks(ids=[], texts=[], embeddings=[], metadatas=[])
    store.collection.bulk_write.assert_not_called()


def test_count_chunks_counts_whole_collection():
    store = MagicMock()
    store.collection.count_documents.return_value = 24
    with patch.object(vectorstore, "vector_store", store):
        assert vectorstore.count_chunks() == 24
    store.collection.count_documents.assert_called_once_with({})


# ── Tenant isolation ──────────────────────────────────────────────────────────


def _matches(doc: dict, query: dict) -> bool:
    """The subset of MQL the app's filters use: equality, $eq and $in."""
    for field, cond in query.items():
        value = doc.get(field)
        if isinstance(cond, dict):
            if "$eq" in cond and value != cond["$eq"]:
                return False
            if "$in" in cond and value not in cond["$in"]:
                return False
        elif value != cond:
            return False
    return True


class _FakeChunkCollection:
    def __init__(self):
        self.docs: dict[str, dict] = {}

    def add(self, user_id: str, source: str, chunk: int, text: str) -> None:
        chunk_id = f"{user_id}_{source}_chunk_{chunk}"
        self.docs[chunk_id] = {
            "_id": chunk_id,
            "text": text,
            "embedding": [0.0],
            **build_metadata(user_id, source, chunk=str(chunk)),
        }

    def delete_many(self, query: dict):
        doomed = [i for i, d in self.docs.items() if _matches(d, query)]
        for chunk_id in doomed:
            del self.docs[chunk_id]
        return SimpleNamespace(deleted_count=len(doomed))

    def find(self, query: dict) -> list[dict]:
        return [d for d in self.docs.values() if _matches(d, query)]


class _FakeAtlasStore:
    """Stand-in for MongoDBAtlasVectorSearch that applies the $vectorSearch
    pre_filter the way Atlas does; ranking is irrelevant to isolation."""

    def __init__(self):
        self.collection = _FakeChunkCollection()

    def similarity_search_by_vector(self, embedding, k=4, pre_filter=None, **_kwargs):
        hits = self.collection.find(pre_filter or {})[:k]
        return [
            Document(
                page_content=d["text"],
                metadata={f: v for f, v in d.items() if f not in ("text", "embedding")},
            )
            for d in hits
        ]


@pytest.fixture
def store():
    return _FakeAtlasStore()


def _search_as(store: _FakeAtlasStore, user_id: str) -> list[str]:
    hits = store.similarity_search_by_vector([0.0], k=10, pre_filter=get_search_filter(user_id))
    return [d.page_content for d in hits]


def test_user_a_docs_invisible_to_user_b(store):
    """Documents ingested under user_a must not be returned when searching as user_b."""
    store.collection.add("user_a", "a_contract.pdf", 0, "User A's contract terms")
    store.collection.add("user_b", "b_order.pdf", 0, "User B's purchase order")

    assert _search_as(store, "user_b") == ["User B's purchase order"]


def test_user_b_docs_invisible_to_user_a(store):
    """Symmetric check: user_b docs not visible when searching as user_a."""
    store.collection.add("user_a", "a.pdf", 0, "User A only")
    store.collection.add("user_b", "b.pdf", 0, "User B only")

    assert _search_as(store, "user_a") == ["User A only"]


def test_system_docs_visible_to_every_user(store):
    store.collection.add(SYSTEM_USER_ID, "N4412_genika_kriteria.pdf", 0, "Law excerpt")
    store.collection.add("user_a", "a.pdf", 0, "User A only")

    assert sorted(_search_as(store, "user_a")) == ["Law excerpt", "User A only"]
    assert _search_as(store, "user_b") == ["Law excerpt"]


def test_search_with_no_docs_for_user_returns_empty(store):
    """A user with no documents gets no hits rather than someone else's."""
    store.collection.add("user_a", "file.pdf", 0, "Some document belonging to user_a")

    assert _search_as(store, "user_b") == []


def test_delete_removes_only_target_user_docs(store):
    """DELETE /documents' {user_id, source} filter removes only that user's file chunks."""
    store.collection.add("user_a", "contract.pdf", 0, "chunk 0")
    store.collection.add("user_a", "contract.pdf", 1, "chunk 1")
    store.collection.add("user_b", "contract.pdf", 0, "user b chunk 0")

    with patch.object(vectorstore, "vector_store", store):
        deleted = vectorstore.delete_chunks({"user_id": "user_a", "source": "contract.pdf"})

    assert deleted == 2
    assert store.collection.find({"user_id": "user_a"}) == []
    assert [d["_id"] for d in store.collection.find({"user_id": "user_b"})] == [
        "user_b_contract.pdf_chunk_0"
    ]


def test_delete_same_filename_different_users(store):
    """Two users uploading the same filename must not affect each other on delete."""
    store.collection.add("user_a", "invoice.pdf", 0, "user_a invoice content")
    store.collection.add("user_b", "invoice.pdf", 0, "user_b invoice content")

    with patch.object(vectorstore, "vector_store", store):
        vectorstore.delete_chunks({"user_id": "user_a", "source": "invoice.pdf"})

    assert store.collection.find({"user_id": "user_a"}) == []
    assert len(store.collection.find({"user_id": "user_b"})) == 1
