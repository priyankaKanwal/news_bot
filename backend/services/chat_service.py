from rag.answer_generator import generate_answer


def process_chat(question: str):
    # Step 1: Call our existing RAG function
    answer, results = generate_answer(question, top_k=7)

    # Step 2: Collapse chunks into one entry per article.
    # Several chunks can come from the same article; keep the best score.
    articles = {}

    for document, score in results:
        meta = document.metadata

        key = meta.get("article_id") or meta.get("article_url") or meta.get("title")

        if key not in articles or score > articles[key]["score"]:
            articles[key] = {
                "title": meta.get("title", "Untitled"),
                "publisher": meta.get("publisher", "Unknown"),
                "published_at": meta.get("published_at"),
                "url": meta.get("article_url"),
                "score": float(score),
            }

    # Step 3: Best-matching articles first
    sources = sorted(
        articles.values(),
        key=lambda source: source["score"],
        reverse=True
    )

    # Step 4: Return answer and sources
    return {
        "answer": answer,
        "sources": sources
    }
