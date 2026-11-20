from contextlib import asynccontextmanager
from datetime import datetime, timezone
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import json
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.database import Base, engine, get_db
from backend.models import Article, ChatMessage, Conversation
from backend.schemas.article_schema import RecentArticle
from backend.schemas.chat_schema import (
    ChatRequest,
    ChatResponse,
    ConversationDetail,
    ConversationSummary,
)
from backend.services.chat_service import process_chat, process_chat_stream
from ingestion.ingestion_service import run_ingestion


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="AI News Intelligence API",
    description="Backend APIs for our RAG chatbot",
    version="1.0.0",
    lifespan=lifespan,
)

origins = [
    "http://localhost:5173"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Conversation-ID"],
)


@app.get("/api/health")
def health_check():
    return {
        "status": "success",
        "message": "AI News Intelligence backend is running!"
    }


@app.get("/api/articles/recent", response_model=list[RecentArticle])
def list_recent_articles(
    limit: int = Query(default=6, ge=1, le=12),
    db: Session = Depends(get_db),
):
    statement = (
        select(Article)
        .where(Article.url != "")
        .order_by(Article.published_at.desc())
        .limit(limit)
    )
    return db.scalars(statement).all()


@app.post("/api/ingestion/run")
def start_ingestion():
    """Run one ingestion pass for the feeds configured in feeds.yaml."""
    return run_ingestion()


@app.get("/api/conversations", response_model=list[ConversationSummary])
def list_conversations(db: Session = Depends(get_db)):
    statement = select(Conversation).order_by(Conversation.updated_at.desc())
    return db.scalars(statement).all()


@app.get(
    "/api/conversations/{conversation_id}",
    response_model=ConversationDetail,
)
def get_conversation(conversation_id: UUID, db: Session = Depends(get_db)):
    statement = (
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == conversation_id)
    )
    conversation = db.scalar(statement)

    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    return conversation


@app.delete("/api/conversations/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: UUID, db: Session = Depends(get_db)):
    conversation = db.get(Conversation, conversation_id)

    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    db.delete(conversation)
    db.commit()
    return Response(status_code=204)


# Keep this synchronous so FastAPI runs blocking RAG work in its thread pool.
@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    conversation = None

    if request.conversation_id is not None:
        conversation = db.get(Conversation, request.conversation_id)

        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found.")

    if conversation is None:
        title = request.question.strip()
        if len(title) > 117:
            title = title[:117].rstrip() + "..."
        conversation = Conversation(title=title)
        db.add(conversation)
        db.flush()

    conversation_id = conversation.id
    db.add(
        ChatMessage(
            conversation_id=conversation_id,
            role="user",
            content=request.question,
        )
    )
    conversation.updated_at = datetime.now(timezone.utc)
    db.commit()

    try:
        result = process_chat(request.question)
    except Exception as error:
        print("Chat error:", repr(error), flush=True)
        raise HTTPException(
            status_code=502,
            detail="Could not generate an answer. Please try again.",
            headers={"X-Conversation-ID": str(conversation_id)},
        ) from error

    db.add(
        ChatMessage(
            conversation_id=conversation_id,
            role="assistant",
            content=result["answer"],
            sources=result["sources"],
        )
    )
    conversation.updated_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "conversation_id": conversation_id,
        **result,
    }


def _new_conversation(request: ChatRequest, db: Session) -> Conversation:
    if request.conversation_id is not None:
        conversation = db.get(Conversation, request.conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found.")
        return conversation

    title = request.question.strip()
    if len(title) > 117:
        title = title[:117].rstrip() + "..."
    conversation = Conversation(title=title)
    db.add(conversation)
    db.flush()
    return conversation


@app.post("/api/chat/stream")
def stream_chat(request: ChatRequest, db: Session = Depends(get_db)):
    conversation = _new_conversation(request, db)
    conversation_id = conversation.id

    db.add(
        ChatMessage(
            conversation_id=conversation_id,
            role="user",
            content=request.question,
        )
    )
    conversation.updated_at = datetime.now(timezone.utc)
    db.commit()

    def events():
        answer = ""
        sources = []

        try:
            for event in process_chat_stream(request.question):
                if event["type"] == "done":
                    answer = event["answer"]
                    sources = event["sources"]

                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

            db.add(
                ChatMessage(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=answer,
                    sources=sources,
                )
            )
            conversation.updated_at = datetime.now(timezone.utc)
            db.commit()

        except Exception as error:
            print("Streaming chat error:", repr(error), flush=True)
            yield f"data: {json.dumps({'type': 'error', 'message': 'Could not generate an answer. Please try again.'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Conversation-ID": str(conversation_id),
        },
    )
