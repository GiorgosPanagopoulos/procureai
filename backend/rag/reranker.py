from typing import Any

import structlog

log = structlog.get_logger()

_reranker: Any = None


def _get_reranker() -> Any:
    global _reranker
    if _reranker is None:
        try:
            from sentence_transformers import CrossEncoder

            _reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
            log.info("reranker_loaded", model="cross-encoder/ms-marco-MiniLM-L-6-v2")
        except Exception as exc:
            log.warning("reranker_unavailable", error=str(exc))
    return _reranker
