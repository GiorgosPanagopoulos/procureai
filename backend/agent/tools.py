import asyncio
import json
import re
from typing import Dict, List

import numpy as np
import sentry_sdk
import structlog
from anthropic.types import TextBlock
from config import settings
from core.chroma_tenant import get_active_user_id, get_user_filter
from db import db
from langchain_core.tools import tool
from llm.clients import _raw_anthropic_async, claude_llm
from llm.pricing import MODEL_NAME, _current_usage
from rag.embeddings import embed_text
from rag.reranker import _get_reranker
from rag.vectorstore import chroma_collection
from schemas import BidComparisonResult

from agent.prompt import get_doc_qa_system_prompt

log = structlog.get_logger()

# Rows handed to the model per lookup. The tools count the full match set as
# well, so a capped result is reported as "showing N of M" rather than as M.
_BID_LIMIT = 10
_SUPPLIER_LIMIT = 10


@tool
async def document_qa(question: str) -> str:
    """ALWAYS use this tool first for any question involving: prices, cost, price lists,
    budget, contracts, contract terms, document contents, or comparisons between suppliers
    based on price. This tool searches the vector database of uploaded PDFs including
    price lists and contracts. Input: the question to answer."""
    if not question.strip():
        return "Please provide a question."

    user_id = get_active_user_id()
    if not user_id:
        return "Authentication required to query documents."

    query_embedding = await asyncio.to_thread(embed_text, question)
    n_retrieve = 20 if settings.USE_RERANKER else 4

    sentry_sdk.add_breadcrumb(category="rag", message="RAG retrieval start", level="info")
    try:
        # Chroma raises when n_results exceeds the number of stored chunks, so a
        # small collection would otherwise look like "no relevant documents".
        stored_chunks = await asyncio.to_thread(chroma_collection.count)
        n_retrieve = max(1, min(n_retrieve, stored_chunks))
        with sentry_sdk.start_span(op="db.chromadb", description="RAG vector search") as _span:
            _span.set_data("collection", "procureai_documents")
            _span.set_data("n_results", n_retrieve)
            results = await asyncio.to_thread(
                chroma_collection.query,
                query_embeddings=np.array([query_embedding]),
                n_results=n_retrieve,
                include=["documents", "metadatas"],
                where={"$or": [get_user_filter(user_id), {"user_id": "system"}]},
            )
    except Exception as exc:
        exc_str = str(exc)
        if "Number of requested results" in exc_str or "greater than number of elements" in exc_str:
            return "No relevant documents found."
        return f"Error searching documents: {exc}"

    all_docs: List[str] = []
    all_metas: List[Dict] = []
    if results:
        for dl in results.get("documents") or []:
            if dl is not None:
                all_docs.extend(dl)
        for ml in results.get("metadatas") or []:
            all_metas.extend(list(ml) if ml is not None else [])  # type: ignore[arg-type]

    if settings.USE_RERANKER and all_docs:
        reranker = _get_reranker()
        if reranker is not None:
            scores = await asyncio.to_thread(reranker.predict, [(question, d) for d in all_docs])
            top_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:5]
            all_docs = [all_docs[i] for i in top_idx]
            all_metas = [all_metas[i] for i in top_idx]

    context = "\n".join(all_docs) if all_docs else "No relevant documents found."
    source_refs = list({m.get("source", "unknown") for m in all_metas})

    sentry_sdk.add_breadcrumb(category="llm", message="LLM call start", level="info")
    try:
        with sentry_sdk.start_span(op="llm.invoke", description="Claude API call") as _span:
            _span.set_data("model", MODEL_NAME)
            _span.set_data("tool", "document_qa")
            response = await _raw_anthropic_async.messages.create(
                model=MODEL_NAME,
                max_tokens=1024,
                system=[
                    {
                        "type": "text",
                        "text": get_doc_qa_system_prompt(),
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"Context:\n{context}",
                                "cache_control": {"type": "ephemeral"},
                            },
                            {
                                "type": "text",
                                "text": f"\nQuestion: {question}\n\nAnswer:",
                            },
                        ],
                    }
                ],
            )
            _span.set_data("tokens_used", getattr(response.usage, "output_tokens", "N/A"))
        accum = _current_usage.get()
        if accum is not None:
            accum.add_anthropic(response.usage)
        first_block = response.content[0]
        answer: str = first_block.text if isinstance(first_block, TextBlock) else str(first_block)
    except Exception as exc:
        answer = f"Error generating answer: {exc}"

    sources_note = f"\n\nSources: {', '.join(source_refs)}" if source_refs else ""
    return answer + sources_note


async def _no_match_hint(collection, label: str, requested: str) -> str:
    """Observation for a category filter that matched nothing.

    Categories are stored as Greek labels ("Ιατρικά Υλικά & Εξοπλισμός"), so an
    English filter such as "medical equipment" never matches. Listing the real
    labels lets the agent retry once with one of them instead of guessing
    synonyms until it hits the iteration cap (eval q07, 2026-09-12c).
    """
    categories = sorted(c for c in await collection.distinct("category") if c)
    message = f"No {label} found for category: {requested}."
    if not categories:
        return message
    return (
        f"{message} Categories in the system are: {', '.join(categories)}. "
        "Retry with one of these labels (a distinctive part of it, such as "
        f"'{categories[0].split()[0]}', is enough)."
    )


def _format_bids_text(bids: List[Dict], total_matched: int) -> str:
    """Plain-text ranking used as the fallback observation when Claude is unavailable."""
    ranked = sorted(bids, key=lambda b: (b.get("total_price", 0), b.get("delivery_days", 0)))
    if total_matched > len(ranked):
        result = (
            f"Bid Comparison Results (showing {len(ranked)} of {total_matched} matching bids; "
            "results truncated):\n"
        )
    else:
        result = f"Bid Comparison Results ({total_matched} bids):\n"
    for i, bid in enumerate(ranked, 1):
        result += (
            f"\n{i}. Supplier ID: {bid.get('supplier_id', 'N/A')}\n"
            f"   Total Price: €{bid.get('total_price', 0):.2f}\n"
            f"   Delivery Days: {bid.get('delivery_days', 'N/A')}\n"
            f"   Terms: {bid.get('terms', 'N/A')}\n"
            f"   Status: {bid.get('status', 'pending')}\n"
        )
    return result


@tool
async def bid_comparison(category: str = "") -> str:
    """Rank or compare submitted bids by price and delivery time, and recommend one.
    Returns the individual bids as a ranked list, so use it for comparing, ranking,
    listing or filtering bids (e.g. 'the bids for IT hardware', 'accepted bids',
    'which bid delivers fastest'), including when the comparison spans every bid.
    Input: a category filter (e.g. 'office equipment', 'IT hardware'), or an
    empty string for the full ranked set. Not for dataset-wide totals, averages,
    counts or status breakdowns: those belong to report_generation, since this
    tool only sees a capped page of matches."""
    try:
        mongo_query: Dict = {}
        if category.strip():
            # re.escape so a category containing regex metacharacters is matched literally.
            mongo_query["category"] = {"$regex": re.escape(category.strip()), "$options": "i"}

        total_matched = await db.bids.count_documents(mongo_query)
        bids_list = await db.bids.find(mongo_query).limit(_BID_LIMIT).to_list(length=_BID_LIMIT)
        if not bids_list:
            if category.strip():
                return await _no_match_hint(db.bids, "bids", category.strip())
            return "No bids found in the system."
    except Exception as exc:
        return f"Error comparing bids: {exc}"

    truncated = total_matched > len(bids_list)

    raw_bids = [
        {
            "supplier_id": str(bid.get("supplier_id", "")),
            "category": bid.get("category", ""),
            "total_price_eur": bid.get("total_price", 0),
            "delivery_days": bid.get("delivery_days", 0),
            "terms": bid.get("terms", ""),
            "status": bid.get("status", "pending"),
        }
        for bid in bids_list
    ]

    sentry_sdk.add_breadcrumb(category="llm", message="LLM call start", level="info")
    try:
        with sentry_sdk.start_span(op="llm.invoke", description="Claude API call") as _span:
            _span.set_data("model", MODEL_NAME)
            _span.set_data("tool", "bid_comparison")
            _span.set_data("bid_count", len(raw_bids))
            _span.set_data("total_matched", total_matched)
            coverage = f"{len(raw_bids)} of {total_matched} matching bids are listed below"
            if truncated:
                coverage += (
                    "; the list is truncated, so the recommendation must say it covers "
                    f"only {len(raw_bids)} of the {total_matched} matching bids"
                )
            # claude_llm carries _UsageCallback, which feeds _current_usage on
            # on_llm_end; accumulating here as well would double-count the call.
            structured = claude_llm.with_structured_output(BidComparisonResult)
            result = await structured.ainvoke(
                "Rank these procurement bids best-value first, weighing total price "
                f"against delivery time, and recommend one.\n"
                "All prices are in euros (EUR); do not convert them.\n"
                f"{coverage}.\n"
                f"Bids:\n{json.dumps(raw_bids, ensure_ascii=False, indent=2)}"
            )
        if not isinstance(result, BidComparisonResult):
            raise TypeError(f"Unexpected structured output type: {type(result).__name__}")
        # The counts come from Mongo, not from the model: overwrite whatever it echoed.
        result = result.model_copy(update={"total_matched": total_matched, "truncated": truncated})
        return result.model_dump_json(indent=2)
    except Exception as exc:
        log.warning("bid_comparison_structured_failed", error=str(exc))
        return _format_bids_text(bids_list, total_matched)


@tool
async def supplier_lookup(query: str = "") -> str:
    """Find and filter suppliers by category or rating.
    Input: category name (e.g. 'IT Hardware', 'Medical'), or 'rating:4.0' to filter
    by minimum rating, or empty string to list all suppliers."""
    try:
        mongo_query: Dict = {}
        if query.startswith("rating:"):
            try:
                min_rating = float(query.split(":")[1].strip())
                mongo_query["rating"] = {"$gte": min_rating}
            except ValueError:
                pass
        elif query.strip():
            mongo_query["category"] = {"$regex": query.strip(), "$options": "i"}

        total_matched = await db.suppliers.count_documents(mongo_query)
        suppliers_list = (
            await db.suppliers.find(mongo_query)
            .limit(_SUPPLIER_LIMIT)
            .to_list(length=_SUPPLIER_LIMIT)
        )
        if not suppliers_list:
            if "category" in mongo_query:
                return await _no_match_hint(db.suppliers, "suppliers", query.strip())
            return f"No suppliers found matching: {query}"

        sorted_s = sorted(suppliers_list, key=lambda x: x.get("rating", 0), reverse=True)
        if total_matched > len(sorted_s):
            result = (
                f"Supplier Lookup Results (showing {len(sorted_s)} of {total_matched} "
                "matching suppliers; results truncated):\n"
            )
        else:
            result = f"Supplier Lookup Results ({len(sorted_s)} found):\n"
        for i, s in enumerate(sorted_s, 1):
            result += (
                f"\n{i}. {s.get('name', 'N/A')}\n"
                f"   Category: {s.get('category', 'N/A')}\n"
                f"   Rating: {s.get('rating', 'N/A')}/5.0\n"
                f"   Contact: {s.get('contact', 'N/A')}\n"
            )
        return result
    except Exception as exc:
        return f"Error looking up suppliers: {exc}"


@tool
async def report_generation(report_type: str = "procurement") -> str:
    """Generate a structured procurement summary report from live MongoDB data.
    Reads every supplier and bid and returns the dataset-wide aggregates: supplier
    count and average rating, bid count, total bid value, average delivery time
    in days, and the status distribution. Use it for any total, average, count or
    status breakdown across all bids. Input: report type, e.g. 'procurement',
    'summary', or 'full'."""
    try:
        suppliers_list = await db.suppliers.find({}).to_list(length=None)
        bids_list = await db.bids.find({}).to_list(length=None)

        report = f"PROCUREMENT REPORT — {report_type.upper()}\n{'=' * 40}\n\n"
        report += f"SUPPLIERS SUMMARY:\n- Total Suppliers: {len(suppliers_list)}\n"
        if suppliers_list:
            avg_rating = sum(s.get("rating", 0) for s in suppliers_list) / len(suppliers_list)
            categories = sorted({s.get("category", "unknown") for s in suppliers_list})
            report += (
                f"- Average Rating: {avg_rating:.2f}/5.0\n- Categories: {', '.join(categories)}\n"
            )

        report += f"\nBIDS SUMMARY:\n- Total Bids: {len(bids_list)}\n"
        if bids_list:
            total_value = sum(b.get("total_price", 0) for b in bids_list)
            avg_delivery = sum(b.get("delivery_days", 0) for b in bids_list) / len(bids_list)
            statuses: Dict[str, int] = {}
            for bid in bids_list:
                s = bid.get("status", "pending")
                statuses[s] = statuses.get(s, 0) + 1
            report += (
                f"- Total Bid Value: €{total_value:,.2f}\n"
                f"- Average Delivery Time: {avg_delivery:.1f} days\n"
                f"- Status Distribution: {statuses}\n"
            )
        return report
    except Exception as exc:
        return f"Error generating report: {exc}"
