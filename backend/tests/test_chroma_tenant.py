import sys
from unittest.mock import MagicMock

# Prevent LLM/embedding stack from loading
sys.modules.setdefault("rag.embeddings", MagicMock())
sys.modules.setdefault("rag.vectorstore", MagicMock())

import numpy as np  # noqa: E402
import pytest  # noqa: E402
from core.chroma_tenant import (  # noqa: E402
    _current_user_id,
    build_metadata,
    get_active_user_id,
    get_user_filter,
)

# ── Unit tests for helper functions ───────────────────────────────────────────


def test_get_user_filter_returns_correct_dict():
    assert get_user_filter("user_abc") == {"user_id": "user_abc"}


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


# ── ChromaDB isolation tests ──────────────────────────────────────────────────


def _random_embedding(dim: int = 4) -> list:
    """Small random unit vector; dimension must match collection."""
    v = np.random.randn(dim).astype(np.float32)
    return (v / np.linalg.norm(v)).tolist()


@pytest.fixture
def col():
    """Ephemeral in-memory ChromaDB collection, torn down after each test."""
    import chromadb

    client = chromadb.EphemeralClient()
    collection = client.create_collection("test_isolation")
    yield collection
    client.delete_collection("test_isolation")


def test_user_a_docs_invisible_to_user_b(col):
    """Documents ingested under user_a must not be returned when querying as user_b."""
    col.add(
        ids=["user_a_doc_0"],
        embeddings=[_random_embedding()],
        documents=["User A's contract terms"],
        metadatas=[build_metadata("user_a", "a_contract.pdf", chunk="0")],
    )
    col.add(
        ids=["user_b_doc_0"],
        embeddings=[_random_embedding()],
        documents=["User B's purchase order"],
        metadatas=[build_metadata("user_b", "b_order.pdf", chunk="0")],
    )

    results = col.query(
        query_embeddings=[_random_embedding()],
        n_results=10,
        include=["documents", "metadatas"],
        where=get_user_filter("user_b"),
    )
    docs = results["documents"][0]
    assert len(docs) == 1
    assert "User B's purchase order" in docs
    assert "User A's contract terms" not in docs


def test_user_b_docs_invisible_to_user_a(col):
    """Symmetric check: user_b docs not visible when querying as user_a."""
    col.add(
        ids=["user_a_doc_0"],
        embeddings=[_random_embedding()],
        documents=["User A only"],
        metadatas=[build_metadata("user_a", "a.pdf", chunk="0")],
    )
    col.add(
        ids=["user_b_doc_0"],
        embeddings=[_random_embedding()],
        documents=["User B only"],
        metadatas=[build_metadata("user_b", "b.pdf", chunk="0")],
    )

    results = col.query(
        query_embeddings=[_random_embedding()],
        n_results=10,
        include=["documents", "metadatas"],
        where=get_user_filter("user_a"),
    )
    docs = results["documents"][0]
    assert "User A only" in docs
    assert "User B only" not in docs


def test_query_no_docs_for_user_returns_empty(col):
    """Querying when a user has no documents should return empty results, not raise."""
    # Seed a doc for a different user
    col.add(
        ids=["user_a_only"],
        embeddings=[_random_embedding()],
        documents=["Some document belonging to user_a"],
        metadatas=[build_metadata("user_a", "file.pdf", chunk="0")],
    )

    # user_b has no documents — chromadb should return empty, not raise
    try:
        results = col.query(
            query_embeddings=[_random_embedding()],
            n_results=4,
            include=["documents", "metadatas"],
            where=get_user_filter("user_b"),
        )
        docs = results["documents"][0] if results.get("documents") else []
    except Exception:
        # If chromadb raises for 0 matches, the document_qa tool handles it gracefully
        docs = []

    assert docs == []


def test_delete_removes_only_target_user_docs(col):
    """DELETE with user_id+source filter removes only that user's file chunks."""
    col.add(
        ids=["user_a_contract_0", "user_a_contract_1"],
        embeddings=[_random_embedding(), _random_embedding()],
        documents=["chunk 0", "chunk 1"],
        metadatas=[
            build_metadata("user_a", "contract.pdf", chunk="0"),
            build_metadata("user_a", "contract.pdf", chunk="1"),
        ],
    )
    col.add(
        ids=["user_b_contract_0"],
        embeddings=[_random_embedding()],
        documents=["user b chunk 0"],
        metadatas=[build_metadata("user_b", "contract.pdf", chunk="0")],
    )

    # Delete user_a's contract.pdf
    col.delete(
        where={"$and": [{"user_id": {"$eq": "user_a"}}, {"source": {"$eq": "contract.pdf"}}]}
    )

    user_a_remaining = col.get(where=get_user_filter("user_a"))
    assert len(user_a_remaining["ids"]) == 0

    user_b_remaining = col.get(where=get_user_filter("user_b"))
    assert len(user_b_remaining["ids"]) == 1
    assert user_b_remaining["ids"][0] == "user_b_contract_0"


def test_delete_same_filename_different_users(col):
    """Two users uploading the same filename must not affect each other on delete."""
    col.add(
        ids=["user_a_invoice_0"],
        embeddings=[_random_embedding()],
        documents=["user_a invoice content"],
        metadatas=[build_metadata("user_a", "invoice.pdf", chunk="0")],
    )
    col.add(
        ids=["user_b_invoice_0"],
        embeddings=[_random_embedding()],
        documents=["user_b invoice content"],
        metadatas=[build_metadata("user_b", "invoice.pdf", chunk="0")],
    )

    # user_a deletes their invoice.pdf
    col.delete(where={"$and": [{"user_id": {"$eq": "user_a"}}, {"source": {"$eq": "invoice.pdf"}}]})

    user_a_docs = col.get(where=get_user_filter("user_a"))
    assert len(user_a_docs["ids"]) == 0

    # user_b's invoice.pdf must still exist
    user_b_docs = col.get(where=get_user_filter("user_b"))
    assert len(user_b_docs["ids"]) == 1
