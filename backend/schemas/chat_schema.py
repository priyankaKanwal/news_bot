from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    """Chat request payload."""

    question: str = Field(..., min_length=3, max_length=500)
    conversation_id: UUID | None = None


class Source(BaseModel):
    """News source returned with an answer."""

    title: str
    publisher: str
    published_at: str | None = None 
    url: str | None = None
    score: float


class ChatResponse(BaseModel):
    """Chat response payload."""

    conversation_id: UUID
    answer: str
    sources: list[Source]


class StoredMessage(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: Literal["user", "assistant"]
    content: str
    sources: list[Source]
    created_at: datetime


class ConversationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationDetail(ConversationSummary):
    messages: list[StoredMessage]
