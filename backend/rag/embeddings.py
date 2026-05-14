from typing import List

import structlog
from llm.clients import openai_client

log = structlog.get_logger()


def embed_text(text: str) -> List[float]:
    if not text.strip():
        return [0.0] * 1536
    try:
        return (
            openai_client.embeddings.create(model="text-embedding-3-small", input=text[:8191])
            .data[0]
            .embedding
        )
    except Exception as exc:
        log.error("embed_failed", error=str(exc))
        return [0.0] * 1536
