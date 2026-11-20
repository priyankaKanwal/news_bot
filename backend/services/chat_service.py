from rag.answer_generator import generate_answer, stream_answer


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


def sources_from_results(results):
    """Convert retrieved document chunks into unique article sources."""
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

    return sorted(
        articles.values(),
        key=lambda source: source["score"],
        reverse=True,
    )


def process_chat_stream(question: str):
    """Yield streaming LLM events and the final response sources."""
    for event in stream_answer(question, top_k=7):
        if event["type"] == "done":
            yield {
                "type": "done",
                "answer": event["answer"],
                "sources": sources_from_results(event["results"]),
            }
        else:
            yield event
