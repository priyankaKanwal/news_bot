import json

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.schemas.chat import ChatRequest
from backend.services.chat_service import (
    ChatGenerationError,
    ConversationNotFoundError,
    create_chat_response,
    stream_chat_response,
)


def create_chat(request: ChatRequest, db: Session):
    try:
        return create_chat_response(request, db)
    except ConversationNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        ) from error
    except ChatGenerationError as error:
        raise HTTPException(
            status_code=502,
            detail="Could not generate an answer. Please try again.",
            headers={"X-Conversation-ID": str(error.conversation_id)},
        ) from error


def stream_chat(request: ChatRequest, db: Session):
    try:
        conversation_id, events = stream_chat_response(request, db)
    except ConversationNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        ) from error

    def encoded_events():
        for event in events:
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        encoded_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Conversation-ID": str(conversation_id),
        },
    )
