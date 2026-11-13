"""Central settings for the RAG pipeline.

Change models here - nothing else needs editing.

IMPORTANT: VECTOR_SIZE must match EMBEDDING_MODEL's output size.
If you switch the embedding model, update VECTOR_SIZE and delete
the qdrant_db/ folder so the data is re-embedded with the new model.
Vectors from different models cannot be mixed.
"""

# ---------- Embedding model (Hugging Face, runs locally) ----------
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
VECTOR_SIZE = 384

# BGE models work best when search queries start with this instruction.
# It is NOT added to the documents, only to the user's question.
EMBEDDING_QUERY_INSTRUCTION = (
    "Represent this sentence for searching relevant passages: "
)

# ---------- LLM (Ollama, runs locally) ----------
LLM_MODEL = "llama3.2"
OLLAMA_URL = "http://localhost:11434"
LLM_TEMPERATURE = 0      # 0 = most factual, least creative
LLM_TIMEOUT = 120        # seconds; local models on CPU can be slow

# ---------- Vector database (Qdrant) ----------
QDRANT_PATH = "qdrant_db"
COLLECTION_NAME = "news_articles"
