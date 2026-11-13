from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.schemas.chat_schema import ChatRequest, ChatResponse
from backend.services.chat_service import process_chat


# Create the FastAPI application
app = FastAPI(
    title="AI News Intelligence API",
    description="Backend APIs for our RAG chatbot",
    version="1.0.0"
)

# Allow our React frontend to communicate with this backend
origins = [
    "http://localhost:5173"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# Health check API
@app.get("/api/health")
def health_check():
    return {
        "status": "success",
        "message": "AI News Intelligence backend is running!"
    }


# Main chat API
# `def` (not `async def`) so FastAPI runs this blocking code in a thread
@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        return process_chat(request.question)
    except Exception as error:
        print("Chat error:", repr(error), flush=True)
        raise HTTPException(
            status_code=502,
            detail="Could not generate an answer. Please try again."
        )
