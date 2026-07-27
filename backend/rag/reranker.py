from typing import Any

import structlog

log = structlog.get_logger()

_reranker: Any = None


def _get_reranker() -> Any:
    global _reranker
    if _reranker is None:
        try:
            from sentence_transformers import CrossEncoder
        except ImportError:
            raise RuntimeError(
                "Reranker enabled (USE_RERANKER=true) but sentence-transformers is not installed.\n"
                "Run: pip install -r backend/requirements-rerank.txt"
            )
        try:
            _reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
            log.info("reranker_loaded", model="cross-encoder/ms-marco-MiniLM-L-6-v2")
        except Exception as exc:
            log.error(
                "reranker_load_failed",
                error=str(exc),
                fallback="continuing without reranking",
            )
    return _reranker
