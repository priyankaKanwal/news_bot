from rag.answer_generator import generate_answer


def process_chat(question: str):
    answer, results = generate_answer(question, top_k=7)

    # Keep one source per article, using its best chunk score.
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

    sources = sorted(
        articles.values(),
        key=lambda source: source["score"],
        reverse=True
    )

    return {
        "answer": answer,
        "sources": sources
    }
