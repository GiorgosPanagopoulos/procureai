import uuid

import sentry_sdk
import structlog
from agent.executor import run_agent
from agent.tools import document_qa
from auth.dependencies import get_current_user
from db import db
from exceptions import AgentExecutionError, DocumentIngestionError, NotFoundError, ValidationError
from fastapi import APIRouter, Depends, File, Request, UploadFile
from middleware.rate_limit import limiter
from rag.ingest import ingest_pdf
from schemas.chat import ChatRequest

log = structlog.get_logger()

router = APIRouter()


@router.post("/chat")
@limiter.limit("10/minute")
async def chat(
    request: Request,
    payload: ChatRequest,
    current_user: dict = Depends(get_current_user),
):
    if not payload.message.strip():
        raise ValidationError("Message cannot be empty")
    cid = payload.conversation_id or str(uuid.uuid4())
    try:
        result = await run_agent(payload.message, cid)
    except AgentExecutionError:
        raise
    if not result.get("response"):
        raise AgentExecutionError("Agent returned empty response")
    return {
        "response": result["response"],
        "tool_used": result.get("tool_used"),
        "conversation_id": cid,
        "usage": result.get("usage"),
        "trace": result.get("trace"),
    }


@router.post("/upload")
@limiter.limit("30/minute")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    if file.content_type != "application/pdf":
        raise ValidationError("Only PDF uploads are supported")
    content = await file.read()
    try:
        chunks = ingest_pdf(file.filename or "uploaded.pdf", content)
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
    log.info("pdf_uploaded", file=file.filename, chunks=chunks)
    return {
        "message": "PDF ingested successfully",
        "chunks": chunks,
        "file": file.filename,
    }


@router.post("/doc_qa")
@limiter.limit("30/minute")
async def qna(request: Request, question: str, current_user: dict = Depends(get_current_user)):
    return {"answer": document_qa.invoke(question), "question": question}


@router.get("/conversations/{conversation_id}/trace")
async def get_trace(conversation_id: str, current_user: dict = Depends(get_current_user)):
    doc = await db.conversations.find_one({"conversation_id": conversation_id})
    if not doc:
        raise NotFoundError("Conversation not found")
    return {"conversation_id": conversation_id, "trace": doc.get("trace", [])}
