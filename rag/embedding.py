
from rag.text_splitter import split_news_documents
from rag.vector_store import get_embedding_model


def generate_embeddings():

    # Step 1: Get document chunks
    chunks = split_news_documents()

    print("Total chunks:", len(chunks))

    # Step 2: Initialize the local Hugging Face embedding model
    embeddings = get_embedding_model()

    # Step 3: Extract text from chunks
    texts = [chunk.page_content for chunk in chunks]

    # Step 4: Convert text into numerical vectors
    vectors = embeddings.embed_documents(texts)

    return chunks, vectors


if __name__ == "__main__":

    chunks, vectors = generate_embeddings()

    print("\nTotal embeddings generated:", len(vectors))

    for index, vector in enumerate(vectors):

        print("\n------------------------------")
        print("Chunk:", index + 1)
        print("Vector dimensions:", len(vector))
        print("First 5 vector values:", vector[:5])
