from exceptions import AgentExecutionError, DocumentIngestionError, ProcureAIException
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
    for cls in (ProcureAIException, DocumentIngestionError, AgentExecutionError):
        assert issubclass(cls, HTTPException)
