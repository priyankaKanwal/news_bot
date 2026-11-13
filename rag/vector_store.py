
from uuid import uuid5, NAMESPACE_URL

from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from rag.text_splitter import split_news_documents

load_dotenv()

# Qdrant configuration
COLLECTION_NAME = "news_articles"
QDRANT_PATH = "qdrant_db"
VECTOR_SIZE = 3072


def create_vector_store():

    # Step 2: Create Qdrant client
    client = QdrantClient(path=QDRANT_PATH)

    # Step 3: Create collection if it doesn't exist
    if not client.collection_exists(COLLECTION_NAME):

        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=VECTOR_SIZE,
                distance=Distance.COSINE
            )
        )

        print("Qdrant collection created!")

    # Step 4: Initialize Gemini embedding model
    # Leave task_type unset:
    # LangChain's Google integration defaults to
    # RETRIEVAL_DOCUMENT for documents and
    # RETRIEVAL_QUERY for queries.
    embedding_model = GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-001"
    )

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
