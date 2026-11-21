"""Conversation lifecycle, grounded responses, and message history."""

from sqlalchemy.orm import Session, selectinload

from app.ai.rag import answer_question
from app.core.config import get_settings
from app.models.conversation import Conversation, Message
from app.models.document import Document
from app.schemas.chat import ChatRequest, ChatResponse, ConversationResponse, MessageResponse


def chat(request: ChatRequest, db: Session) -> ChatResponse:
    """Answer from selected documents and save both sides of the exchange."""
    conversation = db.get(Conversation, request.conversation_id) if request.conversation_id else None
    if request.conversation_id and conversation is None:
        raise LookupError("Conversation not found.")
    if conversation is None:
        conversation = Conversation(title=request.question[:80])
        db.add(conversation)
        db.flush()

    document = db.get(Document, request.document_id)
    if document is None:
        raise LookupError("The selected document was not found. Upload a document before asking a question.")

    history = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.desc())
        .limit(4)
        .all()
    )
    history.reverse()
    # Earlier user questions help resolve short follow-ups. Past assistant text
    # may contain an unsupported answer, so it must not steer retrieval.
    prior = "\n".join(f"user: {item.content[:400]}" for item in history if item.role == "user")

    paths = [get_settings().index_dir / document.id]
    answer, sources = answer_question(request.question, paths, prior)
    db.add(Message(conversation_id=conversation.id, role="user", content=request.question))
    db.add(Message(conversation_id=conversation.id, role="assistant", content=answer))
    db.commit()
    return ChatResponse(conversation_id=conversation.id, answer=answer, sources=sources)


def get_conversation(conversation_id: str, db: Session) -> ConversationResponse | None:
    """Fetch one conversation and its full ordered message history."""
    record = (
        db.query(Conversation)
        .options(selectinload(Conversation.messages))
        .filter(Conversation.id == conversation_id)
        .first()
    )
    if record is None:
        return None
    messages = sorted(record.messages, key=lambda item: item.created_at)
    return ConversationResponse(
        id=record.id,
        title=record.title,
        created_at=record.created_at,
        messages=[MessageResponse(id=m.id, role=m.role, content=m.content, created_at=m.created_at) for m in messages],
    )


def list_conversations(db: Session) -> list[dict[str, str]]:
    """Return conversation identifiers and titles, newest first."""
    return [
        {"id": item.id, "title": item.title, "created_at": item.created_at.isoformat()}
        for item in db.query(Conversation).order_by(Conversation.created_at.desc()).all()
    ]
