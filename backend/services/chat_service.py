
from pathlib import Path

from rag.answer_generator import generate_answer


def process_chat(question: str):
    # Step 1: Call our existing RAG function
    answer, results = generate_answer(question, top_k=7)

    # Step 2: Prepare unique source documents
    source_scores = {}

    for document, score in results:
        source_path = document.metadata.get("source", "Unknown")

        # Extract only the filename
        source_name = Path(source_path).name

        # Keep the highest score for each source
        if (
            source_name not in source_scores
            or score > source_scores[source_name]
        ):
            source_scores[source_name] = float(score)

    # Step 3: Convert source information into a list
    sources = [
        {
            "name": name,
            "score": score
        }
        for name, score in source_scores.items()
    ]

    # Step 4: Return answer and sources
    return {
        "answer": answer,
        "sources": sources
    }
