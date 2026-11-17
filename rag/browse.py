"""Fetch recent articles for broad news questions that vector search may miss."""

import re

from langchain_core.documents import Document

from rag.config import COLLECTION_NAME
from rag.vector_store import build_recency_filter, get_client

BROWSE_PATTERN = re.compile(
    r"\b(latest|top|today|todays|today's|trending|recent|recently|"
    r"headlines?|top stories|breaking|what'?s new|what is new|"
    r"happening|happened|this week|news)\b",
    re.IGNORECASE,
)

# Query keywords mapped to stored article categories.
CATEGORY_WORDS = {
    "World News": ("world", "global", "international"),
    "Technology": ("tech", "technology", "ai"),
    "Business & Finance": ("business", "finance", "economy", "economic", "market"),
}

BROWSE_MAX_ARTICLES = 6


def is_browse_question(question):
    return bool(BROWSE_PATTERN.search(question))


def _category_for_question(question):
    words = set(re.findall(r"[a-z]+", question.lower()))
    for category, keywords in CATEGORY_WORDS.items():
        if words & set(keywords):
            return category

    return None


def _publisher_for_question(question, points):
    words = set(re.findall(r"[a-z]+", question.lower()))
    publishers = {
        point.payload["metadata"].get("publisher")
        for point in points
        if point.payload and point.payload.get("metadata", {}).get("publisher")
    }

    for publisher in sorted(publishers, key=len, reverse=True):
        publisher_words = set(re.findall(r"[a-z]+", publisher.lower()))
        publisher_words -= {"and", "of", "the", "news"}

        if publisher.lower() in question.lower() or words & publisher_words:
            return publisher

    return None


def fetch_latest_articles(question, limit=BROWSE_MAX_ARTICLES):
    """Return the newest unique articles, optionally filtered.

    Results use a placeholder score because they are ordered by recency.
    """
    client = get_client()

    try:
        points, _ = client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=build_recency_filter(),
            limit=1000,
            with_payload=True,
        )

        category = _category_for_question(question)
        publisher = _publisher_for_question(question, points)
        filtered_points = [
            point for point in points
            if (category is None or point.payload["metadata"].get("category") == category)
            and (publisher is None or point.payload["metadata"].get("publisher") == publisher)
        ]
        if filtered_points:
            points = filtered_points

        points.sort(
            key=lambda p: p.payload["metadata"].get("published_ts") or 0,
            reverse=True,
        )

        seen = set()
        results = []

        for point in points:
            meta = point.payload["metadata"]
            key = meta.get("article_id") or meta.get("article_url")

            if key in seen:
                continue

            seen.add(key)
            results.append((
                Document(
                    page_content=point.payload.get("page_content", ""),
                    metadata=meta,
                ),
                1.0,
            ))

            if len(results) >= limit:
                break

        return results

    finally:
        client.close()
