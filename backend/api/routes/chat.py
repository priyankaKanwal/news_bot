from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.api.dependencies import get_db
from backend.controllers.chat_controller import (
    create_chat,
    stream_chat as create_chat_stream,
)
from backend.schemas.chat import ChatRequest, ChatResponse

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    return create_chat(request, db)


@router.post("/chat/stream")
def stream_chat(request: ChatRequest, db: Session = Depends(get_db)):
    return create_chat_stream(request, db)
