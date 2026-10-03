import asyncio
import json
import re
import sys
from types import SimpleNamespace
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.documents import Document

# Stub the LLM/embedding stack BEFORE importing agent.tools so no real
# clients or vector store connections are opened during test collection.
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
    """Regression: embed_text and the vector search must go through asyncio.to_thread."""
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
            # hits returned for vector_store.similarity_search_by_vector call
            [
                Document(
                    page_content="procurement contract clause", metadata={"source": "contract.pdf"}
                )
            ],
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
        f"Expected at least 2 asyncio.to_thread calls (embed + vector search), "
        f"got {fake_to_thread.call_count}"
    )


async def test_document_qa_searches_with_tenant_pre_filter():
    """The $vectorSearch pre-filter must limit hits to the caller's own chunks plus
    the shared system documents (Chroma's where={"$or": [user, system]} before)."""
    from anthropic.types import TextBlock

    fake_response = MagicMock()
    fake_response.content = [TextBlock(text="answer from the chunks", type="text")]
    fake_response.usage = SimpleNamespace(
        input_tokens=10,
        output_tokens=5,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=0,
    )

    store = MagicMock()
    store.similarity_search_by_vector.return_value = [
        Document(page_content="chunk a", metadata={"source": "law.pdf"}),
        Document(page_content="chunk b", metadata={"source": "law.pdf"}),
    ]
    # Run the offloaded call inline so the fake store is exercised.
    passthrough_to_thread = AsyncMock(side_effect=lambda fn, *a, **kw: fn(*a, **kw))

    with (
        patch("asyncio.to_thread", new=passthrough_to_thread),
        patch.object(tools_module.settings, "USE_RERANKER", False),
        patch("agent.tools.embed_text", return_value=[0.1] * 4),
        patch("agent.tools.vector_store", store),
        patch("agent.tools.get_active_user_id", return_value="user-42"),
        patch.object(
            tools_module._raw_anthropic_async.messages,
            "create",
            new=AsyncMock(return_value=fake_response),
        ),
    ):
        observation = await document_qa.ainvoke("what does the law say?")

    args, kwargs = store.similarity_search_by_vector.call_args
    assert args == ([0.1] * 4,)
    assert kwargs == {"k": 4, "pre_filter": {"user_id": {"$in": ["user-42", "system"]}}}
    assert observation.startswith("answer from the chunks")
    assert "Sources: law.pdf" in observation


async def test_document_qa_reports_vector_search_errors():
    """A failing $vectorSearch (e.g. the Atlas index is missing) surfaces as an
    observation instead of raising out of the tool."""
    store = MagicMock()
    store.similarity_search_by_vector.side_effect = RuntimeError("index not found")
    passthrough_to_thread = AsyncMock(side_effect=lambda fn, *a, **kw: fn(*a, **kw))

    with (
        patch("asyncio.to_thread", new=passthrough_to_thread),
        patch("agent.tools.embed_text", return_value=[0.1] * 4),
        patch("agent.tools.vector_store", store),
        patch("agent.tools.get_active_user_id", return_value="user-42"),
    ):
        observation = await document_qa.ainvoke("anything")

    assert observation == "Error searching documents: index not found"


def _fake_collection(
    docs, total: Optional[int] = None, categories: Optional[list] = None
) -> MagicMock:
    """Stand-in for a Motor collection: count_documents(q), find(q).limit(n).to_list(length=n)
    and distinct("category").

    `total` is what count_documents reports; it defaults to len(docs) (nothing
    truncated) and can be set higher to simulate a match set beyond the limit.
    `categories` is what distinct("category") reports for the whole collection.
    """
    cursor = MagicMock()
    cursor.limit.return_value = cursor
    cursor.to_list = AsyncMock(return_value=docs)
    return MagicMock(
        find=MagicMock(return_value=cursor),
        count_documents=AsyncMock(return_value=len(docs) if total is None else total),
        distinct=AsyncMock(return_value=categories or []),
    )


def _fake_bids_db(
    bids, total: Optional[int] = None, categories: Optional[list] = None
) -> MagicMock:
    return MagicMock(bids=_fake_collection(bids, total, categories))


def _fake_suppliers_db(
    suppliers, total: Optional[int] = None, categories: Optional[list] = None
) -> MagicMock:
    return MagicMock(suppliers=_fake_collection(suppliers, total, categories))


def _bid(i: int) -> dict:
    return {"supplier_id": f"s{i}", "total_price": 100.0 * i, "delivery_days": i}


def _supplier(i: int) -> dict:
    return {"name": f"Supplier {i}", "category": "IT", "rating": 3.0 + i / 10, "contact": "n/a"}


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
    assert result == "No bids found for category: Εξοπλισμός IT."


async def test_bid_comparison_lists_real_categories_when_filter_matches_nothing():
    # Eval q07 ("Show me bids for medical equipment"): categories are Greek labels, so
    # the agent tried "medical equipment", "Medical", "medical supplies", "healthcare"
    # and then supplier_lookup("Medical"), hit the 5-iteration cap and answered
    # "Agent stopped due to iteration limit". The observation must name the labels so
    # the next call can use one.
    from agent.tools import bid_comparison

    fake_db = _fake_bids_db(
        [], categories=["Εξοπλισμός IT", "Ιατρικά Υλικά & Εξοπλισμός", "", "Γραφική Ύλη"]
    )
    with patch("agent.tools.db", fake_db):
        observation = await bid_comparison.ainvoke("medical equipment")

    fake_db.bids.distinct.assert_awaited_once_with("category")
    assert observation.startswith("No bids found for category: medical equipment.")
    assert (
        "Categories in the system are: Γραφική Ύλη, Εξοπλισμός IT, Ιατρικά Υλικά & Εξοπλισμός."
        in observation
    )
    assert "Retry with one of these labels" in observation
    assert "'Γραφική'" in observation


async def test_bid_comparison_no_match_without_categories_stays_short():
    from agent.tools import bid_comparison

    fake_db = _fake_bids_db([])
    with patch("agent.tools.db", fake_db):
        observation = await bid_comparison.ainvoke("medical equipment")

    assert observation == "No bids found for category: medical equipment."


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
        total_matched=1,
        truncated=False,
    )
    fake_db = _fake_bids_db([{"supplier_id": "s1", "total_price": 450.0, "delivery_days": 3}])
    llm = _structured_llm(parsed)

    with patch("agent.tools.db", fake_db), patch("agent.tools.claude_llm", llm):
        observation = await bid_comparison.ainvoke("")

    llm.with_structured_output.assert_called_once_with(BidComparisonResult)
    assert json.loads(observation) == parsed.model_dump()


def _ranked(bids: list) -> list:
    from schemas import RankedBid

    return [
        RankedBid(
            supplier_id=b["supplier_id"],
            total_price_eur=b["total_price"],
            delivery_days=b["delivery_days"],
            status="pending",
        )
        for b in bids
    ]


async def test_bid_comparison_labels_truncated_results():
    """Regression: 16 bids matched but only 10 were fetched, and the report said
    "Total bids: 10". The counts must come from Mongo, not from the capped page."""
    from agent.tools import bid_comparison
    from schemas import BidComparisonResult

    page = [_bid(i) for i in range(1, 11)]
    fake_db = _fake_bids_db(page, total=16)
    # The model echoes the wrong counts; the tool must overwrite them.
    llm = _structured_llm(
        BidComparisonResult(
            bids=_ranked(page), recommendation="Award to s1.", total_matched=10, truncated=False
        )
    )

    with patch("agent.tools.db", fake_db), patch("agent.tools.claude_llm", llm):
        observation = json.loads(await bid_comparison.ainvoke("Εξοπλισμός IT"))

    mongo_query = fake_db.bids.find.call_args.args[0]
    fake_db.bids.count_documents.assert_awaited_once_with(mongo_query)
    fake_db.bids.find.return_value.limit.assert_called_once_with(10)
    assert observation["total_matched"] == 16
    assert observation["truncated"] is True
    assert len(observation["bids"]) == 10
    # The model is told about the gap so the recommendation can state it.
    prompt = llm.with_structured_output.return_value.ainvoke.call_args.args[0]
    assert "10 of 16 matching bids" in prompt
    assert "truncated" in prompt


async def test_bid_comparison_reports_full_set_when_not_truncated():
    from agent.tools import bid_comparison
    from schemas import BidComparisonResult

    page = [_bid(i) for i in range(1, 4)]
    fake_db = _fake_bids_db(page)  # count_documents == len(page) == 3
    llm = _structured_llm(
        BidComparisonResult(
            bids=_ranked(page), recommendation="Award to s1.", total_matched=3, truncated=False
        )
    )

    with patch("agent.tools.db", fake_db), patch("agent.tools.claude_llm", llm):
        observation = json.loads(await bid_comparison.ainvoke(""))

    assert observation["total_matched"] == 3
    assert observation["truncated"] is False
    prompt = llm.with_structured_output.return_value.ainvoke.call_args.args[0]
    assert "3 of 3 matching bids" in prompt
    assert "truncated" not in prompt


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

    assert observation.startswith("Bid Comparison Results (2 bids):")
    assert observation.index("cheap") < observation.index("expensive")


async def test_bid_comparison_plain_text_fallback_labels_truncation():
    from agent.tools import bid_comparison

    fake_db = _fake_bids_db([_bid(1), _bid(2)], total=5)
    llm = _structured_llm(RuntimeError("anthropic unavailable"))

    with patch("agent.tools.db", fake_db), patch("agent.tools.claude_llm", llm):
        observation = await bid_comparison.ainvoke("")

    assert observation.startswith(
        "Bid Comparison Results (showing 2 of 5 matching bids; results truncated):"
    )


# ── supplier_lookup ──────────────────────────────────────────────────────────


async def test_supplier_lookup_labels_truncated_results():
    from agent.tools import supplier_lookup

    fake_db = _fake_suppliers_db([_supplier(i) for i in range(1, 11)], total=16)

    with patch("agent.tools.db", fake_db):
        observation = await supplier_lookup.ainvoke("IT")

    mongo_query = fake_db.suppliers.find.call_args.args[0]
    fake_db.suppliers.count_documents.assert_awaited_once_with(mongo_query)
    fake_db.suppliers.find.return_value.limit.assert_called_once_with(10)
    assert observation.startswith(
        "Supplier Lookup Results (showing 10 of 16 matching suppliers; results truncated):"
    )
    assert observation.count("\n   Rating:") == 10


async def test_supplier_lookup_lists_real_categories_when_filter_matches_nothing():
    # Same dead end as bid_comparison in eval q07: supplier_lookup("Medical") returned
    # "No suppliers found" against Greek category labels.
    from agent.tools import supplier_lookup

    fake_db = _fake_suppliers_db([], categories=["Ιατρικά Υλικά & Εξοπλισμός", "Εξοπλισμός IT"])
    with patch("agent.tools.db", fake_db):
        observation = await supplier_lookup.ainvoke("Medical")

    fake_db.suppliers.distinct.assert_awaited_once_with("category")
    assert observation.startswith("No suppliers found for category: Medical.")
    assert "Categories in the system are: Εξοπλισμός IT, Ιατρικά Υλικά & Εξοπλισμός." in observation


async def test_supplier_lookup_rating_filter_no_match_does_not_list_categories():
    from agent.tools import supplier_lookup

    fake_db = _fake_suppliers_db([], categories=["Εξοπλισμός IT"])
    with patch("agent.tools.db", fake_db):
        observation = await supplier_lookup.ainvoke("rating:4.9")

    fake_db.suppliers.distinct.assert_not_awaited()
    assert observation == "No suppliers found matching: rating:4.9"


async def test_supplier_lookup_reports_full_set_when_not_truncated():
    from agent.tools import supplier_lookup

    fake_db = _fake_suppliers_db([_supplier(1), _supplier(2)])

    with patch("agent.tools.db", fake_db):
        observation = await supplier_lookup.ainvoke("IT")

    assert observation.startswith("Supplier Lookup Results (2 found):")
    assert "truncated" not in observation


async def test_report_generation_averages_delivery_over_every_bid():
    """q12 (2026-09-12d) passed via bid_comparison with an average over 10 of 16 bids.
    The report reads the whole collection, so its average must cover every bid."""
    from agent.tools import report_generation

    bids = [_bid(i) for i in range(1, 17)]  # delivery_days 1..16, mean 8.5
    fake_db = MagicMock(suppliers=_fake_collection([]), bids=_fake_collection(bids))
    with patch("agent.tools.db", fake_db):
        result = await report_generation.ainvoke("summary")

    fake_db.bids.find.return_value.to_list.assert_awaited_once_with(length=None)
    assert "- Total Bids: 16" in result
    assert "- Average Delivery Time: 8.5 days" in result
