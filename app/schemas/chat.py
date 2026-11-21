"""Chat and conversation API schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    document_id: str = Field(min_length=36, max_length=36)
    conversation_id: str | None = None


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime


class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    sources: list[str]


class ConversationResponse(BaseModel):
    id: str
    title: str
    created_at: datetime
    messages: list[MessageResponse]
