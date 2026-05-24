from typing import Dict, List

import numpy as np
import sentry_sdk
import structlog
from anthropic.types import TextBlock
from config import settings
from core.chroma_tenant import get_active_user_id, get_user_filter
from db import db
from langchain_core.tools import tool
from llm.clients import _raw_anthropic
from llm.pricing import MODEL_NAME, _current_usage
from rag.embeddings import embed_text
from rag.reranker import _get_reranker
from rag.vectorstore import chroma_collection

from agent.prompt import get_doc_qa_system_prompt

log = structlog.get_logger()


@tool
def document_qa(question: str) -> str:
    """ALWAYS use this tool first for any question involving: prices, cost, price lists,
    budget, contracts, contract terms, document contents, or comparisons between suppliers
    based on price. This tool searches the vector database of uploaded PDFs including
    price lists and contracts. Input: the question to answer."""
    if not question.strip():
        return "Please provide a question."

    user_id = get_active_user_id()
    if not user_id:
        return "Authentication required to query documents."

    query_embedding = embed_text(question)
    n_retrieve = 20 if settings.USE_RERANKER else 4

    sentry_sdk.add_breadcrumb(category="rag", message="RAG retrieval start", level="info")
    try:
        with sentry_sdk.start_span(op="db.chromadb", description="RAG vector search") as _span:
            _span.set_data("collection", "procureai_documents")
            _span.set_data("n_results", n_retrieve)
            results = chroma_collection.query(
                query_embeddings=np.array([query_embedding]),
                n_results=n_retrieve,
                include=["documents", "metadatas"],
                where=get_user_filter(user_id),
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
            scores = reranker.predict([(question, d) for d in all_docs])
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
            response = _raw_anthropic.messages.create(
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


@tool
async def bid_comparison(category: str = "") -> str:
    """Compare procurement bids ranked by price and delivery time.
    Input: optional category filter (e.g. 'office equipment', 'IT hardware')
    or empty string to compare all bids."""
    try:
        bids_list = await db.bids.find({}).limit(10).to_list(length=10)
        if not bids_list:
            return "No bids found in the system."
        sorted_bids = sorted(
            bids_list,
            key=lambda x: (x.get("total_price", 0), x.get("delivery_days", 0)),
        )
        result = "Bid Comparison Results:\n"
        for i, bid in enumerate(sorted_bids, 1):
            result += (
                f"\n{i}. Supplier ID: {bid.get('supplier_id', 'N/A')}\n"
                f"   Total Price: ${bid.get('total_price', 0):.2f}\n"
                f"   Delivery Days: {bid.get('delivery_days', 'N/A')}\n"
                f"   Terms: {bid.get('terms', 'N/A')}\n"
                f"   Status: {bid.get('status', 'pending')}\n"
            )
        return result
    except Exception as exc:
        return f"Error comparing bids: {exc}"


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

        suppliers_list = await db.suppliers.find(mongo_query).limit(10).to_list(length=10)
        if not suppliers_list:
            return f"No suppliers found matching: {query}"

        sorted_s = sorted(suppliers_list, key=lambda x: x.get("rating", 0), reverse=True)
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
    Input: report type, e.g. 'procurement', 'summary', or 'full'."""
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
                f"- Total Bid Value: ${total_value:,.2f}\n"
                f"- Average Delivery Time: {avg_delivery:.1f} days\n"
                f"- Status Distribution: {statuses}\n"
            )
        return report
    except Exception as exc:
        return f"Error generating report: {exc}"
