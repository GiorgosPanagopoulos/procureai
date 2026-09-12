import asyncio
import json
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
            50,  # stored chunk count returned for chroma_collection.count call
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

    assert fake_to_thread.call_count >= 3, (
        f"Expected at least 3 asyncio.to_thread calls (embed + count + query), "
        f"got {fake_to_thread.call_count}"
    )


async def test_document_qa_clamps_n_results_to_collection_size():
    """Regression: with the reranker on, n_retrieve is 20, but Chroma raises when
    n_results exceeds the stored chunk count and the tool reported that as
    "No relevant documents found". The request must be clamped instead."""
    from anthropic.types import TextBlock

    fake_response = MagicMock()
    fake_response.content = [TextBlock(text="answer from the three chunks", type="text")]
    fake_response.usage = SimpleNamespace(
        input_tokens=10,
        output_tokens=5,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=0,
    )

    collection = MagicMock()
    collection.count.return_value = 3

    def _query(*, n_results, **_kwargs):
        if n_results > collection.count():
            raise RuntimeError(
                f"Number of requested results {n_results} is greater than number of "
                f"elements in index {collection.count()}"
            )
        return {
            "documents": [["chunk a", "chunk b", "chunk c"]],
            "metadatas": [[{"source": "law.pdf"}] * 3],
        }

    collection.query.side_effect = _query
    # Run the offloaded call inline so the fake collection's count/query are exercised.
    passthrough_to_thread = AsyncMock(side_effect=lambda fn, *a, **kw: fn(*a, **kw))

    with (
        patch("asyncio.to_thread", new=passthrough_to_thread),
        patch.object(tools_module.settings, "USE_RERANKER", True),
        patch("agent.tools._get_reranker", return_value=None),
        patch("agent.tools.embed_text", return_value=[0.0] * 4),
        patch("agent.tools.chroma_collection", collection),
        patch("agent.tools.get_active_user_id", return_value="test_user_id"),
        patch.object(
            tools_module._raw_anthropic_async.messages,
            "create",
            new=AsyncMock(return_value=fake_response),
        ),
    ):
        observation = await document_qa.ainvoke("what does the law say?")

    assert collection.query.call_args.kwargs["n_results"] == 3
    assert "No relevant documents found" not in observation
    assert observation.startswith("answer from the three chunks")
    assert "Sources: law.pdf" in observation


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


def _structured_llm(result) -> MagicMock:
    """Stand-in for claude_llm.with_structured_output(...).ainvoke(...)."""
    chain = MagicMock()
    chain.ainvoke = AsyncMock(
        side_effect=result if isinstance(result, Exception) else None,
        return_value=None if isinstance(result, Exception) else result,
    )
    llm = MagicMock()
    llm.with_structured_output.return_value = chain
    return llm


async def test_bid_comparison_returns_structured_json():
    from agent.tools import bid_comparison
    from schemas import BidComparisonResult, RankedBid

    parsed = BidComparisonResult(
        bids=[
            RankedBid(
                supplier_id="s1",
                total_price_eur=450.0,
                delivery_days=3,
                status="accepted",
            )
        ],
        recommendation="Award to s1: lowest total price and fastest delivery.",
    )
    fake_db = _fake_bids_db([{"supplier_id": "s1", "total_price": 450.0, "delivery_days": 3}])
    llm = _structured_llm(parsed)

    with patch("agent.tools.db", fake_db), patch("agent.tools.claude_llm", llm):
        observation = await bid_comparison.ainvoke("")

    llm.with_structured_output.assert_called_once_with(BidComparisonResult)
    assert json.loads(observation) == parsed.model_dump()


async def test_bid_comparison_falls_back_to_plain_text_when_structured_call_fails():
    from agent.tools import bid_comparison

    fake_db = _fake_bids_db(
        [
            {"supplier_id": "expensive", "total_price": 900.0, "delivery_days": 2},
            {"supplier_id": "cheap", "total_price": 100.0, "delivery_days": 9},
        ]
    )
    llm = _structured_llm(RuntimeError("anthropic unavailable"))

    with patch("agent.tools.db", fake_db), patch("agent.tools.claude_llm", llm):
        observation = await bid_comparison.ainvoke("")

    assert observation.startswith("Bid Comparison Results:")
    assert observation.index("cheap") < observation.index("expensive")
