import logging
from collections.abc import Iterator
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from backend.db.models import ChatMessage, Conversation
from backend.schemas.chat import ChatRequest
from rag.answer_generator import generate_answer, stream_answer

logger = logging.getLogger(__name__)


class ConversationNotFoundError(Exception):
    pass


class ChatGenerationError(Exception):
    def __init__(self, conversation_id: UUID):
        super().__init__("Could not generate an answer.")
        self.conversation_id = conversation_id


def _get_or_create_conversation(
    request: ChatRequest,
    db: Session,
) -> Conversation:
    if request.conversation_id is not None:
        conversation = db.get(Conversation, request.conversation_id)
        if conversation is None:
            raise ConversationNotFoundError
        return conversation

    title = request.question.strip()
    if len(title) > 117:
        title = title[:117].rstrip() + "..."
    conversation = Conversation(title=title)
    db.add(conversation)
    db.flush()
    return conversation


def _save_user_message(conversation: Conversation, question: str, db: Session) -> None:
    db.add(
        ChatMessage(
            conversation_id=conversation.id,
            role="user",
            content=question,
        )
    )
    conversation.updated_at = datetime.now(timezone.utc)
    db.commit()


def _save_assistant_message(
    conversation: Conversation,
    answer: str,
    sources: list[dict],
    db: Session,
) -> None:
    db.add(
        ChatMessage(
            conversation_id=conversation.id,
            role="assistant",
            content=answer,
            sources=sources,
        )
    )
    conversation.updated_at = datetime.now(timezone.utc)
    db.commit()


def _sources_from_results(results) -> list[dict]:
    """Return one best-scoring source per article."""
    articles = {}
    for document, score in results:
        meta = document.metadata
        key = meta.get("article_id") or meta.get("article_url") or meta.get("title")
        if key not in articles or score > articles[key]["score"]:
            articles[key] = {
                "title": meta.get("title", "Untitled"),
                "publisher": meta.get("publisher", "Unknown"),
                "published_at": meta.get("published_at"),
                "url": meta.get("article_url"),
                "score": float(score),
            }
    return sorted(articles.values(), key=lambda source: source["score"], reverse=True)


def create_chat_response(request: ChatRequest, db: Session) -> dict:
    conversation = _get_or_create_conversation(request, db)
    _save_user_message(conversation, request.question, db)

    try:
        answer, results = generate_answer(request.question, top_k=7)
    except Exception as error:
        logger.exception("Chat answer generation failed.")
        raise ChatGenerationError(conversation.id) from error

    sources = _sources_from_results(results)
    _save_assistant_message(conversation, answer, sources, db)
    return {
        "conversation_id": conversation.id,
        "answer": answer,
        "sources": sources,
    }


def stream_chat_response(
    request: ChatRequest,
    db: Session,
) -> tuple[UUID, Iterator[dict]]:
    conversation = _get_or_create_conversation(request, db)
    _save_user_message(conversation, request.question, db)

    def events() -> Iterator[dict]:
        try:
            for event in stream_answer(request.question, top_k=7):
                if event["type"] == "done":
                    sources = _sources_from_results(event["results"])
                    event = {
                        "type": "done",
                        "answer": event["answer"],
                        "sources": sources,
                    }
                    _save_assistant_message(
                        conversation,
                        event["answer"],
                        sources,
                        db,
                    )
                yield event
        except Exception:
            logger.exception("Streaming chat answer generation failed.")
            yield {
                "type": "error",
                "message": "Could not generate an answer. Please try again.",
            }

    return conversation.id, events()
