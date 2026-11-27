"""RAG settings. Keep VECTOR_SIZE aligned with the embedding model output."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Embeddings (Jina AI hosted API)
JINA_API_KEY = os.getenv("JINA_API_KEY", "")
EMBEDDING_MODEL = "jina-embeddings-v3"
VECTOR_SIZE = 1024   # Jina's `dimensions` parameter; also the Qdrant vector size.

# LLM (Google Gemini via langchain-google-genai)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-3.5-flash")
LLM_TEMPERATURE = 0
LLM_TIMEOUT = 120        # seconds

# Retrieval
RETRIEVE_TOP_K = int(os.getenv("RETRIEVE_TOP_K", "10"))

# Results below this relevance score, (cosine + 1) / 2, are discarded.
# Calibrated for jina-embeddings-v3: on-topic results scored ~0.61-0.77 and
# off-topic ones topped out at ~0.59, so 0.60 sits in the gap.
SCORE_THRESHOLD = float(os.getenv("SCORE_THRESHOLD", "0.60"))

# The cross-encoder ranks candidates; its score is not a relevance threshold.
RERANKER_MODEL = "BAAI/bge-reranker-base"
RERANK_TOP_N = int(os.getenv("RERANK_TOP_N", "3"))
USE_RERANKER = os.getenv("USE_RERANKER", "1") != "0"
# Raw cosine similarity at or above which two articles count as the same story.
# Calibrated for jina-embeddings-v3: reworded copies of one story scored ~0.93,
# different events on the same topic ~0.77, so 0.88 leaves margin on both sides.
NEAR_DUPLICATE_THRESHOLD = float(
    os.getenv("NEAR_DUPLICATE_THRESHOLD", "0.88")
)
if not 0.0 <= NEAR_DUPLICATE_THRESHOLD <= 1.0:
    raise ValueError("NEAR_DUPLICATE_THRESHOLD must be between 0 and 1.")

# Vector database
# Server mode supports multiple processes; local mode allows only one.
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_PATH = "qdrant_db"
COLLECTION_NAME = "news_articles"
