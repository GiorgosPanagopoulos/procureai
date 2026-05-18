from exceptions import (
    AgentExecutionError,
    DocumentIngestionError,
    NotFoundError,
    ProcureAIException,
    ValidationError,
)
from fastapi import HTTPException


def test_procureai_default_status():
    exc = ProcureAIException()
    assert exc.status_code == 500


def test_procureai_default_detail():
    exc = ProcureAIException()
    assert exc.detail == "Internal server error"


def test_procureai_custom_values():
    exc = ProcureAIException(status_code=422, detail="Unprocessable entity")
    assert exc.status_code == 422
    assert exc.detail == "Unprocessable entity"


def test_procureai_is_http_exception():
    assert isinstance(ProcureAIException(), HTTPException)


def test_document_ingestion_default():
    exc = DocumentIngestionError()
    assert exc.status_code == 400
    assert exc.detail == "Failed to ingest document"


def test_document_ingestion_custom_detail():
    exc = DocumentIngestionError(detail="PDF parse error")
    assert exc.status_code == 400
    assert exc.detail == "PDF parse error"


def test_agent_execution_default():
    exc = AgentExecutionError()
    assert exc.status_code == 500
    assert exc.detail == "Agent execution failed"


def test_all_subclass_http_exception():
    for cls in (
        ProcureAIException,
        DocumentIngestionError,
        AgentExecutionError,
        NotFoundError,
        ValidationError,
    ):
        assert issubclass(cls, HTTPException)


def test_not_found_default():
    exc = NotFoundError()
    assert exc.status_code == 404
    assert "not found" in exc.detail.lower()


def test_not_found_custom_detail():
    exc = NotFoundError(detail="Conversation not found")
    assert exc.status_code == 404
    assert exc.detail == "Conversation not found"


def test_validation_error_default():
    exc = ValidationError()
    assert exc.status_code == 400


def test_validation_error_custom_detail():
    exc = ValidationError(detail="Message cannot be empty")
    assert exc.status_code == 400
    assert exc.detail == "Message cannot be empty"
