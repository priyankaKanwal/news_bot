from uuid import UUID

from fastapi import HTTPException, Response
from sqlalchemy.orm import Session

from backend.services.conversations_service import (
    delete_conversation as delete_conversation_record,
    get_conversation as find_conversation,
    list_conversations as find_conversations,
)


def list_conversations(db: Session):
    return find_conversations(db)


def get_conversation(conversation_id: UUID, db: Session):
    conversation = find_conversation(conversation_id, db)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return conversation


def delete_conversation(conversation_id: UUID, db: Session):
    if not delete_conversation_record(conversation_id, db):
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return Response(status_code=204)
