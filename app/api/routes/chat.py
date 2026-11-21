"""Question answering and conversation history endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from openai import APIConnectionError, APIStatusError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.chat import ChatRequest, ChatResponse, ConversationResponse
from app.services.chat_service import chat, get_conversation, list_conversations

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def ask_question(request: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    """Ask a question about uploaded documents and persist the exchange."""
    try:
        return chat(request, db)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except APIConnectionError as error:
        raise HTTPException(
            status_code=503,
            detail="Cannot reach the selected AI provider. Check your internet connection and try again.",
        ) from error
    except APIStatusError as error:
        if error.status_code == 402:
            detail = "The selected AI provider has no available inference credits. Add credits or choose a provider with available usage."
        elif error.status_code in {401, 403}:
            detail = "The AI provider rejected the API key or project access. Check the key, provider, and model configuration."
        elif error.status_code == 429:
            detail = "The AI provider is rate limiting requests. Wait briefly and try again."
        else:
            detail = f"The AI provider returned HTTP {error.status_code}. Check the selected model and provider settings."
        raise HTTPException(status_code=502, detail=detail) from error
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Could not generate an answer: {error}") from error


@router.get("/conversations", response_model=list[dict[str, str]])
def get_conversations(db: Session = Depends(get_db)) -> list[dict[str, str]]:
    """List saved conversations."""
    return list_conversations(db)


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
def conversation_history(conversation_id: str, db: Session = Depends(get_db)) -> ConversationResponse:
    """Read all messages in a saved conversation."""
    result = get_conversation(conversation_id, db)
    if result is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return result
