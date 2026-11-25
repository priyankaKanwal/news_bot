from functools import lru_cache

from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    PayloadSchemaType,
    Range,
    VectorParams,
)

from ingestion.date_filter import cutoff_timestamp
from rag.config import (
    COLLECTION_NAME,
    EMBEDDING_MODEL,
    JINA_API_KEY,
    QDRANT_PATH,
    QDRANT_URL,
    VECTOR_SIZE,
)
from rag.jina_embeddings import JinaEmbeddings


PUBLISHED_TS_KEY = "metadata.published_ts"


def get_client():
    """Connect to Qdrant in server or local-file mode."""
    if QDRANT_URL:
        return QdrantClient(url=QDRANT_URL)

    return QdrantClient(path=QDRANT_PATH)


@lru_cache(maxsize=1)
def get_embedding_model():
    """Return a cached Jina embedding client (normalized vectors)."""
    return JinaEmbeddings(
        api_key=JINA_API_KEY,
        model=EMBEDDING_MODEL,
        dimensions=VECTOR_SIZE,
    )


def build_recency_filter(extra_conditions=None):
    """Filter Qdrant results to articles in ingestion's 30-day window."""
    conditions = [
        FieldCondition(
            key=PUBLISHED_TS_KEY,
            range=Range(gte=cutoff_timestamp()),
        )
    ]
    if extra_conditions:
        conditions.extend(extra_conditions)

    return Filter(must=conditions)


def create_vector_store():
    """Connect to Qdrant and create the collection if needed."""
    client = get_client()

    if client.collection_exists(COLLECTION_NAME):

        stored_size = client.get_collection(
            COLLECTION_NAME
        ).config.params.vectors.size

        if stored_size != VECTOR_SIZE:

            client.close()

            raise RuntimeError(
                f"Collection '{COLLECTION_NAME}' stores {stored_size}-dim "
                f"vectors but the current embedding model produces "
                f"{VECTOR_SIZE}-dim vectors. Delete the collection "
                f"(or the '{QDRANT_PATH}' folder in local mode) and "
                f"repopulate the collection with the current model."
            )

    else:

        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=VECTOR_SIZE,
                distance=Distance.COSINE
            )
        )

        print("Qdrant collection created!")

    if QDRANT_URL:
        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name=PUBLISHED_TS_KEY,
            field_schema=PayloadSchemaType.FLOAT,
        )

    embedding_model = get_embedding_model()

    vector_store = QdrantVectorStore(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding=embedding_model
    )

    return vector_store, client


if __name__ == "__main__":

    vector_store, client = create_vector_store()

    print("Chunks in Qdrant:", client.count(COLLECTION_NAME).count)

    question = input("\nAsk a question about the news: ")

    results = vector_store.similarity_search_with_score(
        question,
        k=7,
        filter=build_recency_filter(),
    )

    print("\nRelevant news chunks:\n")

    for index, (document, score) in enumerate(results):

        meta = document.metadata

        print(f"\nResult {index + 1}")
        print("Similarity score:", round(score, 4))
        print("Title:", meta.get("title"))
        print("Publisher:", meta.get("publisher"), "|", meta.get("published_at"))
        print("URL:", meta.get("article_url"))
        print("-" * 60)

    client.close()
