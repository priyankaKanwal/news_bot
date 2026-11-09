
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from rag.text_splitter import split_news_documents


# Load API key from .env
load_dotenv()


def generate_embeddings():

    # Step 1: Get document chunks
    chunks = split_news_documents()

    print("Total chunks:", len(chunks))

    # Step 2: Initialize Gemini embedding model
    embeddings = GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-001",
        task_type="RETRIEVAL_DOCUMENT"
    )

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
