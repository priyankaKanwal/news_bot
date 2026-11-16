"""Fallback for broad "what's the latest news?" style questions.

Vector similarity is the wrong tool for these: "top world news today"
is not close to any single article, so every chunk scores below
SCORE_THRESHOLD and the bot refuses. Instead we simply return the newest
articles, optionally narrowed to a publisher or category named in the
question. The LLM still decides whether they answer it.
"""

import re
from pathlib import Path

import yaml
from langchain_core.documents import Document
from qdrant_client.models import FieldCondition, MatchValue

from rag.vector_store import build_recency_filter, get_client
from rag.config import COLLECTION_NAME

BROWSE_PATTERN = re.compile(
    r"\b(latest|top|today|todays|today's|trending|recent|recently|"
    r"headlines?|top stories|breaking|what'?s new|what is new|"
    r"happening|happened|this week|news)\b",
    re.IGNORECASE,
)

# Words in a question -> category stored by ingestion (see feeds.yaml)
CATEGORY_WORDS = {
    "World News": ("world", "global", "international"),
    "Technology": ("tech", "technology", "ai"),
    "Business & Finance": ("business", "finance", "economy", "economic", "market"),
}

FEEDS_FILE = Path(__file__).resolve().parent.parent / "feeds.yaml"

BROWSE_MAX_ARTICLES = 6


def is_browse_question(question):
    return bool(BROWSE_PATTERN.search(question))


def _publishers():
    with open(FEEDS_FILE, encoding="utf-8") as file:
        feeds = yaml.safe_load(file)["feeds"]

    return {feed["name"] for feed in feeds}


def _filter_conditions(question):
    """Narrow to a publisher / category if the question names one."""
    text = question.lower()
    words = set(re.findall(r"[a-z]+", text))
    conditions = []

    for publisher in _publishers():
        if publisher.lower() in text or (
            publisher.lower().split()[0] in {"bbc", "ndtv", "hindu"}
            and publisher.lower().split()[0] in words
        ):
            conditions.append(
                FieldCondition(
                    key="metadata.publisher",
                    match=MatchValue(value=publisher),
                )
            )
            break

    for category, keywords in CATEGORY_WORDS.items():
        if words & set(keywords):
            conditions.append(
                FieldCondition(
                    key="metadata.category",
                    match=MatchValue(value=category),
                )
            )
            break

    return conditions


def fetch_latest_articles(question, limit=BROWSE_MAX_ARTICLES):
    """Newest articles (one chunk each) as (Document, score) pairs.

    Falls back to the unnarrowed set if the publisher/category filter
    matches nothing. The score is a placeholder (1.0): these results
    were chosen by recency, not similarity.
    """
    client = get_client()

    try:
        for conditions in (_filter_conditions(question), []):
            points, _ = client.scroll(
                collection_name=COLLECTION_NAME,
                scroll_filter=build_recency_filter(conditions),
                limit=1000,
                with_payload=True,
            )

            if points:
                break

        # Newest first, one chunk per article
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
