from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.db.models import Conversation


def list_conversations(db: Session) -> list[Conversation]:
    statement = select(Conversation).order_by(Conversation.updated_at.desc())
    return list(db.scalars(statement).all())


def get_conversation(
    conversation_id: UUID,
    db: Session,
) -> Conversation | None:
    statement = (
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == conversation_id)
    )
    return db.scalar(statement)


def delete_conversation(conversation_id: UUID, db: Session) -> bool:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None:
        return False

    db.delete(conversation)
    db.commit()
    return True
