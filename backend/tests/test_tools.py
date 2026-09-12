import asyncio
import re
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

# Stub the LLM/embedding stack BEFORE importing agent.tools so no real
# clients or ChromaDB connections are opened during test collection.
sys.modules.setdefault("rag.embeddings", MagicMock())
sys.modules.setdefault("rag.vectorstore", MagicMock())
sys.modules.setdefault("llm.clients", MagicMock())

import agent.tools as tools_module  # noqa: E402
from agent.tools import document_qa  # noqa: E402


def test_document_qa_is_async_tool():
    """Regression: document_qa must be registered as an async LangChain tool."""
    assert asyncio.iscoroutinefunction(document_qa.coroutine)
    assert document_qa.func is None


async def test_document_qa_offloads_blocking_calls_to_thread():
    """Regression: embed_text and chroma_collection.query must go through asyncio.to_thread."""
    from anthropic.types import TextBlock

    fake_usage = SimpleNamespace(
        input_tokens=10,
        output_tokens=5,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=0,
    )
    fake_response = MagicMock()
    fake_response.content = [TextBlock(text="answer", type="text")]
    fake_response.usage = fake_usage

    # Each call to asyncio.to_thread returns the next value from this list.
    fake_to_thread = AsyncMock(
        side_effect=[
            [0.0] * 4,  # embedding returned for embed_text call
            {  # chroma results returned for chroma_collection.query call
                "documents": [["procurement contract clause"]],
                "metadatas": [[{"source": "contract.pdf"}]],
            },
        ]
    )

    with (
        patch("asyncio.to_thread", new=fake_to_thread),
        patch("agent.tools.get_active_user_id", return_value="test_user_id"),
        patch.object(
            tools_module._raw_anthropic_async.messages,
            "create",
            new=AsyncMock(return_value=fake_response),
        ),
    ):
        await document_qa.ainvoke("test question")

    assert fake_to_thread.call_count >= 2, (
        f"Expected at least 2 asyncio.to_thread calls (embed + query), "
        f"got {fake_to_thread.call_count}"
    )


def _fake_bids_db(bids) -> MagicMock:
    """Stand-in for db.bids: find(...).limit(n).to_list(length=n)."""
    cursor = MagicMock()
    cursor.limit.return_value = cursor
    cursor.to_list = AsyncMock(return_value=bids)
    return MagicMock(bids=MagicMock(find=MagicMock(return_value=cursor)))


async def test_bid_comparison_applies_category_filter():
    """Regression: the `category` argument must reach the Mongo query, not be ignored."""
    from agent.tools import bid_comparison

    fake_db = _fake_bids_db([])
    with patch("agent.tools.db", fake_db):
        result = await bid_comparison.ainvoke("Εξοπλισμός IT")

    fake_db.bids.find.assert_called_once()
    mongo_query = fake_db.bids.find.call_args.args[0]
    assert mongo_query["category"]["$options"] == "i"
    assert mongo_query["category"]["$regex"] == re.escape("Εξοπλισμός IT")
    assert "Εξοπλισμός IT" in result


async def test_bid_comparison_escapes_regex_metacharacters():
    from agent.tools import bid_comparison

    fake_db = _fake_bids_db([])
    with patch("agent.tools.db", fake_db):
        await bid_comparison.ainvoke("IT (hardware)")

    assert fake_db.bids.find.call_args.args[0]["category"]["$regex"] == re.escape("IT (hardware)")


async def test_bid_comparison_without_category_queries_all_bids():
    from agent.tools import bid_comparison

    fake_db = _fake_bids_db([])
    with patch("agent.tools.db", fake_db):
        result = await bid_comparison.ainvoke("")

    assert fake_db.bids.find.call_args.args[0] == {}
    assert result == "No bids found in the system."
