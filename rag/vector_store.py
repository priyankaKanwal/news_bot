
from uuid import uuid5, NAMESPACE_URL

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from rag.config import (
    COLLECTION_NAME,
    EMBEDDING_MODEL,
    EMBEDDING_QUERY_INSTRUCTION,
    QDRANT_PATH,
    VECTOR_SIZE,
)
from rag.text_splitter import split_news_documents


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


def create_vector_store():

    # Step 2: Create Qdrant client
    client = QdrantClient(path=QDRANT_PATH)

    # Step 3: Create collection if it doesn't exist
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

    # Step 4: Initialize the local embedding model
    embedding_model = get_embedding_model()

    # Step 5: Connect LangChain with Qdrant
    vector_store = QdrantVectorStore(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding=embedding_model
    )

    # Step 6: Add documents only if collection is empty
    existing_count = client.count(
        collection_name=COLLECTION_NAME
    ).count

    if existing_count == 0:

        # Load and split documents only when they need to be stored
        chunks = split_news_documents()

        print("Total chunks:", len(chunks))

        # Generate stable IDs to identify each chunk
        ids = [
            str(uuid5(
                NAMESPACE_URL,
                f"{chunk.metadata.get('source')}:{chunk.metadata.get('start_index')}:{chunk.page_content}"
            ))
            for chunk in chunks
        ]

        vector_store.add_documents(
            documents=chunks,
            ids=ids
        )

        print("News chunks stored in Qdrant!")

    else:
        print("Collection already contains", existing_count, "chunks.")
        print("Skipping document insertion.")

    print("Total vectors in Qdrant:", client.count(
        collection_name=COLLECTION_NAME
    ).count)

    return vector_store, client


if __name__ == "__main__":

    vector_store, client = create_vector_store()

    # Step 7: Ask a question
    question = input("\nAsk a question about the news: ")

    # Step 8: Search for similar news chunks
    results = vector_store.similarity_search_with_score(
        question,
        k=7
    )

    print("\nRelevant news chunks:\n")

    for index, (document, score) in enumerate(results):

        print(f"\nResult {index + 1}")
        print("Similarity score:", round(score, 4))
        print("Source:", document.metadata.get("source"))
        print("Content:", document.page_content)
        print("-" * 60)

    client.close()
