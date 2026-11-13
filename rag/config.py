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

# ---------- Retrieval and reranking ----------
# Chunks fetched from Qdrant per question.
RETRIEVE_TOP_K = 10

# Minimum vector similarity for a chunk to count as relevant. If nothing
# reaches it, the bot says it has no information and the LLM is NOT called.
# Measured on 12 test questions (BGE-small, 30-day news):
#   answerable questions scored 0.838-0.929, unanswerable 0.738-0.802.
# Re-measure this when the amount or kind of news changes.
SCORE_THRESHOLD = 0.82

# A cross-encoder reads (question, chunk) together and orders the
# candidates better than vector similarity. It is used only for ORDERING:
# its absolute scores were too harsh on short RSS summaries to be a gate.
RERANKER_MODEL = "BAAI/bge-reranker-base"
RERANK_TOP_N = 3         # chunks passed to the LLM

# ---------- Vector database (Qdrant) ----------
QDRANT_PATH = "qdrant_db"
COLLECTION_NAME = "news_articles"
