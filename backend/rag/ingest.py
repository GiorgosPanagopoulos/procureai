from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import structlog
from chromadb.api.types import Metadata as ChromaMetadata
from core.chroma_tenant import build_metadata
from exceptions import DocumentIngestionError
from pypdf import PdfReader

from rag.chunking import split_text_chunks
from rag.embeddings import embed_text
from rag.vectorstore import chroma_collection

log = structlog.get_logger()


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    except Exception as exc:
        log.error("pdf_extract_failed", error=str(exc))
        raise DocumentIngestionError(detail=f"Failed to extract text: {exc}")


def ingest_text(source: str, text: str, user_id: str) -> int:
    if not text.strip():
        return 0
    chunks = split_text_chunks(text)
    if not chunks:
        return 0
    ids = [f"{user_id}_{source}_chunk_{i}" for i in range(len(chunks))]
    embeddings = [embed_text(c) for c in chunks]
    raw_metadatas: List[Dict[str, str]] = [
        build_metadata(user_id=user_id, source=source, chunk=str(i)) for i in range(len(chunks))
    ]
    safe_metadatas: List[ChromaMetadata] = [
        {str(k): str(v) for k, v in m.items()} for m in raw_metadatas
    ]
    try:
        chroma_collection.add(
            ids=ids,
            metadatas=safe_metadatas,
            documents=chunks,
            embeddings=np.array(embeddings),
        )  # type: ignore[arg-type]
    except Exception as exc:
        log.error("chroma_add_failed", error=str(exc))
        raise DocumentIngestionError(detail=f"Failed to store chunks: {exc}")
    return len(chunks)


def ingest_pdf(source: str, pdf_bytes: bytes, user_id: str) -> int:
    return ingest_text(source, extract_text_from_pdf(pdf_bytes), user_id)


def ingest_pdf_file(path: Path, user_id: str = "system") -> Dict[str, Any]:
    try:
        return {"file": path.name, "chunks": ingest_pdf(path.name, path.read_bytes(), user_id)}
    except DocumentIngestionError:
        raise
    except Exception as exc:
        log.error("pdf_file_ingest_failed", file=path.name, error=str(exc))
        raise DocumentIngestionError(detail=f"Failed to ingest file {path.name}: {exc}")


def is_vectorstore_empty() -> bool:
    try:
        return chroma_collection.count() == 0
    except Exception:
        return True
