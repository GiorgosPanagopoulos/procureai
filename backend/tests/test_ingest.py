import sys
from unittest.mock import MagicMock

# Prevent the full LLM/embeddings stack from loading during unit tests
sys.modules.setdefault("rag.embeddings", MagicMock())
sys.modules.setdefault("rag.vectorstore", MagicMock())

import pytest  # noqa: E402
from exceptions import DocumentIngestionError  # noqa: E402
from rag.ingest import extract_text_from_pdf  # noqa: E402


def test_extract_text_invalid_bytes_raises():
    with pytest.raises(DocumentIngestionError) as exc_info:
        extract_text_from_pdf(b"not a pdf")
    assert exc_info.value.status_code == 400
    assert "Failed to extract text" in exc_info.value.detail


def test_extract_text_empty_bytes_raises():
    with pytest.raises(DocumentIngestionError):
        extract_text_from_pdf(b"")
