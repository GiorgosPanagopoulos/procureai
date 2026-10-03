import uuid
from typing import Optional

import sentry_sdk
import structlog
from agent.executor import run_agent
from agent.tools import document_qa
from core.audit import AuditEntry
from core.demo import (
    conversation_expiry,
    enforce_demo_quota,
    forbid_demo,
    is_demo_user,
    require_chat_access,
)
from core.rbac import UserRole, require_procurement_officer, require_viewer
from core.tenant import _current_user_id
from db import db
from exceptions import AgentExecutionError, DocumentIngestionError, NotFoundError, ValidationError
from fastapi import APIRouter, Depends, File, Request, UploadFile
from middleware.audit_middleware import audit_interaction
from middleware.rate_limit import limiter
from rag.ingest import ingest_pdf
from rag.vectorstore import delete_chunks
from schemas.chat import ChatRequest

log = structlog.get_logger()

router = APIRouter()

_SOURCES_MARKER = "\n\nSources: "


def _extract_sources(text: str) -> list[str]:
    """Parse source filenames appended by document_qa, e.g. '\n\nSources: a.pdf, b.pdf'."""
    if _SOURCES_MARKER not in text:
        return []
    return [s.strip() for s in text.split(_SOURCES_MARKER, 1)[1].split(",") if s.strip()]


def _client_ip(request: Request) -> Optional[str]:
    return request.client.host if request.client else None


def _can_read_conversation(user: dict, doc: dict) -> bool:
    # The demo login is shared by every visitor, so "owner" would mean all of them.
    if is_demo_user(user):
        return False
    return user.get("role") == UserRole.ADMIN or doc.get("user_id") == str(user["_id"])


async def _owns_or_new(conversation_id: str, user_id: str) -> bool:
    doc = await db.conversations.find_one({"conversation_id": conversation_id})
    return doc is None or doc.get("user_id") == user_id


@router.post("/chat")
@limiter.limit("10/minute")
async def chat(
    request: Request,
    payload: ChatRequest,
    current_user: dict = Depends(require_chat_access),
    _quota: None = Depends(enforce_demo_quota),
):
    if not payload.message.strip():
        raise ValidationError("Message cannot be empty")
    user_id = str(current_user["_id"])
    cid = payload.conversation_id or str(uuid.uuid4())
    # Someone else's id would overwrite their trace; start a fresh conversation instead.
    if payload.conversation_id and not await _owns_or_new(cid, user_id):
        cid = str(uuid.uuid4())
    token = _current_user_id.set(user_id)
    try:
        result = await run_agent(
            payload.message, cid, user_id=user_id, expires_at=conversation_expiry(current_user)
        )
    except AgentExecutionError:
        raise
    finally:
        _current_user_id.reset(token)
    if not result.get("response"):
        raise AgentExecutionError("Agent returned empty response")

    response_text: str = result["response"]
    audit_interaction(
        db,
        AuditEntry(
            user_id=user_id,
            user_role=str(current_user.get("role", "viewer")),
            action="chat",
            query=payload.message[:500],
            response_summary=response_text[:500],
            sources_used=_extract_sources(response_text),
            endpoint="/chat",
            ip_address=_client_ip(request),
        ),
    )

    return {
        "response": response_text,
        "tool_used": result.get("tool_used"),
        "conversation_id": cid,
        "usage": result.get("usage"),
        "trace": result.get("trace"),
    }


@router.post("/upload", dependencies=[Depends(forbid_demo)])
@limiter.limit("30/minute")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    current_user: dict = Depends(require_procurement_officer),
):
    if file.content_type != "application/pdf":
        raise ValidationError("Only PDF uploads are supported")
    content = await file.read()
    user_id = str(current_user["_id"])
    filename = file.filename or "uploaded.pdf"
    try:
        chunks = ingest_pdf(filename, content, user_id)
    except DocumentIngestionError:
        raise
    except Exception as e:
        sentry_sdk.set_context(
            "document",
            {
                "filename": file.filename,
                "content_type": file.content_type,
                "size_bytes": len(content),
            },
        )
        sentry_sdk.capture_exception(e)
        raise DocumentIngestionError(detail=f"Unexpected error: {e}")
    if chunks == 0:
        raise DocumentIngestionError("PDF had no extractable text")

    log.info("pdf_uploaded", file=filename, chunks=chunks)
    audit_interaction(
        db,
        AuditEntry(
            user_id=user_id,
            user_role=str(current_user.get("role", "viewer")),
            action="upload",
            sources_used=[filename],
            endpoint="/upload",
            ip_address=_client_ip(request),
        ),
    )
    return {
        "message": "PDF ingested successfully",
        "chunks": chunks,
        "file": filename,
    }


@router.post("/doc_qa")
@limiter.limit("30/minute")
async def qna(
    request: Request,
    question: str,
    current_user: dict = Depends(require_chat_access),
    _quota: None = Depends(enforce_demo_quota),
):
    user_id = str(current_user["_id"])
    token = _current_user_id.set(user_id)
    try:
        answer = await document_qa.ainvoke(question)
    finally:
        _current_user_id.reset(token)

    audit_interaction(
        db,
        AuditEntry(
            user_id=user_id,
            user_role=str(current_user.get("role", "viewer")),
            action="doc_qa",
            query=question[:500],
            response_summary=answer[:500],
            sources_used=_extract_sources(answer),
            endpoint="/doc_qa",
            ip_address=_client_ip(request),
        ),
    )
    return {"answer": answer, "question": question}


@router.delete("/documents", dependencies=[Depends(forbid_demo)])
@limiter.limit("30/minute")
async def delete_documents(
    request: Request,
    source: str,
    current_user: dict = Depends(require_procurement_officer),
):
    user_id = str(current_user["_id"])
    try:
        delete_chunks({"user_id": user_id, "source": source})
    except Exception as e:
        log.error("vector_delete_failed", error=str(e), user_id=user_id, source=source)
        raise DocumentIngestionError(detail=f"Failed to delete documents: {e}")

    log.info("documents_deleted", user_id=user_id, source=source)
    audit_interaction(
        db,
        AuditEntry(
            user_id=user_id,
            user_role=str(current_user.get("role", "viewer")),
            action="delete_document",
            sources_used=[source],
            endpoint="/documents",
            ip_address=_client_ip(request),
        ),
    )
    return {"message": "Documents deleted", "source": source}


@router.get("/conversations/{conversation_id}/trace")
async def get_trace(conversation_id: str, current_user: dict = Depends(require_viewer)):
    doc = await db.conversations.find_one({"conversation_id": conversation_id})
    # 404 rather than 403 so ids belonging to other users aren't confirmed to exist.
    if not doc or not _can_read_conversation(current_user, doc):
        raise NotFoundError("Conversation not found")
    return {"conversation_id": conversation_id, "trace": doc.get("trace", [])}
