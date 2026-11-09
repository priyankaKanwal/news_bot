
import numpy as np
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from rag.embedding import generate_embeddings

load_dotenv()


def retrieve_relevant_chunks(question, top_k=3):

    # Step 1: Load existing chunks and their embeddings
    chunks, document_vectors = generate_embeddings()

    # Step 2: Create embedding for the user's question
    embedding_model = GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-001",
        task_type="RETRIEVAL_QUERY"
    )

    question_vector = embedding_model.embed_query(question)

    # Step 3: Calculate cosine similarity
    scores = []

    for index, document_vector in enumerate(document_vectors):

        similarity = np.dot(question_vector, document_vector) / (
            np.linalg.norm(question_vector) *
            np.linalg.norm(document_vector)
        )

        scores.append((similarity, index))

    # Step 4: Sort by similarity (highest first)
    scores.sort(reverse=True)

    # Step 5: Return the top matching chunks
    results = []

    for similarity, index in scores[:top_k]:

        results.append({
            "score": float(similarity),
            "content": chunks[index].page_content,
            "metadata": chunks[index].metadata
        })

    return results


if __name__ == "__main__":

    question = input("Ask a question: ")

    results = retrieve_relevant_chunks(question)

    print("\nRelevant news chunks:\n")

    for index, result in enumerate(results):

        print(f"\nResult {index + 1}")
        print("Similarity:", round(result["score"], 4))
        print("Source:", result["metadata"].get("source"))
        print("Content:", result["content"])
        print("-" * 60)
