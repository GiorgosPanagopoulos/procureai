import uuid
from typing import Any

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Any) -> Any:
        cid = str(uuid.uuid4())
        structlog.contextvars.bind_contextvars(correlation_id=cid)
        try:
            response = await call_next(request)
            response.headers["X-Correlation-ID"] = cid
            return response
        finally:
            structlog.contextvars.unbind_contextvars("correlation_id")
