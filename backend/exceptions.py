from fastapi import HTTPException, status


class ProcureAIException(HTTPException):
    """Base exception for ProcureAI."""

    def __init__(self, status_code: int = 500, detail: str = "Internal server error"):
        super().__init__(status_code=status_code, detail=detail)


class DocumentIngestionError(ProcureAIException):
    def __init__(self, detail: str = "Failed to ingest document"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class AgentExecutionError(ProcureAIException):
    def __init__(self, detail: str = "Agent execution failed"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)
