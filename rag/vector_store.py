from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    Range,
    VectorParams,
)

from ingestion.filters import cutoff_timestamp
from rag.config import (
    COLLECTION_NAME,
    EMBEDDING_MODEL,
    EMBEDDING_QUERY_INSTRUCTION,
    QDRANT_PATH,
    VECTOR_SIZE,
)

# LangChain stores chunk metadata under the "metadata" key in the
# Qdrant payload, so a metadata field is filtered as "metadata.<name>".
PUBLISHED_TS_KEY = "metadata.published_ts"


def get_embedding_model():
    """Local Hugging Face embedding model (no API key needed).

    normalize_embeddings=True makes every vector length 1, so
    cosine similarity scores are clean and comparable.
    """
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        encode_kwargs={"normalize_embeddings": True},
        query_encode_kwargs={
            "normalize_embeddings": True,
            "prompt": EMBEDDING_QUERY_INSTRUCTION,
        },
    )


def build_recency_filter(extra_conditions=None):
    """Qdrant filter: only articles published in the last 30 days.

    Used on every search. The cleanup job reuses the same cutoff
    (ingestion.filters) so both always agree on what is "recent".
    """
    conditions = [
        FieldCondition(
            key=PUBLISHED_TS_KEY,
            range=Range(gte=cutoff_timestamp())
        )
    ]

    if extra_conditions:
        conditions.extend(extra_conditions)

    return Filter(must=conditions)


def create_vector_store():
    """Connect to Qdrant (creating the collection if needed).

    This does NOT load any documents. Articles are added by
    `python -m ingestion.ingest`.
    """

    # Step 1: Create Qdrant client
    client = QdrantClient(path=QDRANT_PATH)

    # Step 2: Create collection if it doesn't exist
    if client.collection_exists(COLLECTION_NAME):

        # Guard: vectors from a different embedding model can't be mixed
        stored_size = client.get_collection(
            COLLECTION_NAME
        ).config.params.vectors.size

        if stored_size != VECTOR_SIZE:

            client.close()

            raise RuntimeError(
                f"Collection '{COLLECTION_NAME}' stores {stored_size}-dim "
                f"vectors but the current embedding model produces "
                f"{VECTOR_SIZE}-dim vectors. Delete the '{QDRANT_PATH}' "
                f"folder and run again to re-embed with the new model."
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

    # Step 3: Initialize the local embedding model
    embedding_model = get_embedding_model()

    # Step 4: Connect LangChain with Qdrant
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

    # Search only news from the last 30 days
    results = vector_store.similarity_search_with_score(
        question,
        k=7,
        filter=build_recency_filter()
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
