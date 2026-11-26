from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import articles, chat, conversations, health, ingestion
from backend.core.config import CORS_ORIGINS
from backend.core.logging import configure_logging
from backend.db.models import Article, ChatMessage, Conversation
from backend.db.postgres import Base, engine


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


configure_logging()

app = FastAPI(
    title="AI News Intelligence API",
    description="Backend APIs for our RAG chatbot",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Conversation-ID"],
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(articles.router)
api_router.include_router(ingestion.router)
api_router.include_router(conversations.router)
api_router.include_router(chat.router)
app.include_router(api_router, prefix="/api")
