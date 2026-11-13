from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """What the frontend sends us."""

    # min_length / max_length: FastAPI rejects bad input automatically (422)
    question: str = Field(..., min_length=3, max_length=500)


class Source(BaseModel):
    """One source document used to build the answer."""

    name: str
    score: float


class ChatResponse(BaseModel):
    """What we send back to the frontend."""

    answer: str
    sources: list[Source]
