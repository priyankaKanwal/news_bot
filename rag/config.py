"""RAG settings. Keep VECTOR_SIZE aligned with the embedding model output."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Embeddings
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
VECTOR_SIZE = 384

# Applied to queries, not document text.
EMBEDDING_QUERY_INSTRUCTION = (
    "Represent this sentence for searching relevant passages: "
)

# LLM
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.2")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
LLM_TEMPERATURE = 0
LLM_TIMEOUT = 120        # seconds

# Retrieval
RETRIEVE_TOP_K = int(os.getenv("RETRIEVE_TOP_K", "10"))

# Results below this similarity threshold are discarded.
SCORE_THRESHOLD = float(os.getenv("SCORE_THRESHOLD", "0.70"))

# The cross-encoder ranks candidates; its score is not a relevance threshold.
RERANKER_MODEL = "BAAI/bge-reranker-base"
RERANK_TOP_N = int(os.getenv("RERANK_TOP_N", "3"))
USE_RERANKER = os.getenv("USE_RERANKER", "1") != "0"

# Vector database
# Server mode supports multiple processes; local mode allows only one.
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_PATH = "qdrant_db"
COLLECTION_NAME = "news_articles"
