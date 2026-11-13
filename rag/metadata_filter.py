from pathlib import Path

from qdrant_client.models import (
    Filter,
    FieldCondition,
    MatchValue
)

from rag.document_loader import DOCUMENT_TYPES
from rag.vector_store import create_vector_store


def build_filter(source_file=None, document_type=None):

    conditions = []

    if source_file:
        conditions.append(
            FieldCondition(
                key="metadata.source",
                match=MatchValue(value=source_file)
            )
        )

    if document_type:
        conditions.append(
            FieldCondition(
                key="metadata.document_type",
                match=MatchValue(value=document_type)
            )
        )

    return Filter(must=conditions) if conditions else None


def search_by_source(question, source_file, document_type=None, top_k=5):

    print("\nConnecting to Qdrant...")

    vector_store, client = create_vector_store()

    try:
        metadata_filter = build_filter(source_file, document_type)

        print(f"Searching only in: {source_file}")

        # Search with metadata filtering
        results = vector_store.similarity_search_with_score(
            question,
            k=top_k,
            filter=metadata_filter
        )

        return results

    finally:
        client.close()


if __name__ == "__main__":

    question = input("\nEnter your question: ")

    print("\nSelect document:")
    print("1. Leave Policy")
    print("2. Employee Directory")
    print("3. Expense Policy")
    print("0. All documents")

    choice = input("\nEnter choice (0-3): ")

    # Path() uses the OS separator, matching how DirectoryLoader
    # stores the source (e.g. data\leave_policy.txt on Windows).
    source_files = {
        "0": None,
        "1": str(Path("data") / "leave_policy.txt"),
        "2": str(Path("data") / "employee_directory.txt"),
        "3": str(Path("data") / "expense_policy.txt")
    }

    if choice not in source_files:
        print("Invalid choice!")
    else:
        # Imported here to avoid a circular import at module load
        from rag.answer_generator import generate_answer

        source_file = source_files[choice]
        document_type = (
            DOCUMENT_TYPES.get(Path(source_file).name)
            if source_file else None
        )

        answer, results = generate_answer(
            question,
            top_k=5,
            source_file=source_file,
            document_type=document_type
        )

        print("\n" + "=" * 60)
        print("AI GENERATED ANSWER")
        print("=" * 60)
        print(answer)

        print("\nSources:")
        for source in sorted({d.metadata.get("source") for d, _ in results}):
            print("-", source)
