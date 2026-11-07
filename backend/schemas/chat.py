from typing import Optional

from pydantic import UUID4, BaseModel


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[UUID4] = None
