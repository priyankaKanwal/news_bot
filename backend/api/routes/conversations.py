from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.api.dependencies import get_db
from backend.controllers.conversations_controller import (
    delete_conversation as remove_conversation,
    get_conversation as load_conversation,
    list_conversations as load_conversations,
)
from backend.schemas.chat import ConversationDetail, ConversationSummary

router = APIRouter()


@router.get("/conversations", response_model=list[ConversationSummary])
def list_conversations(db: Session = Depends(get_db)):
    return load_conversations(db)


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetail,
)
def get_conversation(conversation_id: UUID, db: Session = Depends(get_db)):
    return load_conversation(conversation_id, db)


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: UUID, db: Session = Depends(get_db)):
    return remove_conversation(conversation_id, db)
