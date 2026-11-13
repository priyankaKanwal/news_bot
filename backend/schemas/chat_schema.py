from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """What the frontend sends us."""

    # min_length / max_length: FastAPI rejects bad input automatically (422)
    question: str = Field(..., min_length=3, max_length=500)


class Source(BaseModel):
    """One news article used to build the answer."""

    title: str
    publisher: str
    published_at: str | None = None  # ISO 8601, UTC
    url: str | None = None
    score: float


class ChatResponse(BaseModel):
    """What we send back to the frontend."""

    answer: str
    sources: list[Source]
