"""Remove duplicate articles from an ingestion batch."""

import hashlib
import re
from collections.abc import Iterable
from datetime import timedelta
from math import sqrt

from ingestion.cleaner import CleanedArticle


def _content_key(article: CleanedArticle) -> str:
    text = f"{article['title']} {article['content']}".casefold()
    normalized = re.sub(r"[^a-z0-9]+", " ", text).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def deduplicate_articles(
    articles: Iterable[CleanedArticle],
    known_article_ids: set[str] | None = None,
) -> tuple[list[CleanedArticle], int]:
    """Return unique new articles and the number removed.

    Existing article IDs, URL, publisher-scoped feed GUID, and normalized
    content are checked in order. The first occurrence is kept.
    """
    seen_urls: set[str] = set()
    seen_guids: set[tuple[str, str]] = set()
    seen_content: set[str] = set()
    known_ids = known_article_ids or set()
    unique = []
    removed = 0

    for article in articles:
        article_id = article["article_id"]
        url = article["url"]
        guid = article["guid"]
        guid_key = (article["publisher"].casefold(), guid) if guid else None
        content_key = _content_key(article)

        if (
            article_id in known_ids
            or url in seen_urls
            or (guid_key is not None and guid_key in seen_guids)
            or content_key in seen_content
        ):
            removed += 1
            continue

        unique.append(article)
        known_ids.add(article_id)
        seen_urls.add(url)
        seen_content.add(content_key)
        if guid_key is not None:
            seen_guids.add(guid_key)

    return unique, removed


def _normalized_title(article: CleanedArticle) -> str:
    text = article["title"].casefold()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _embedding_similarity(left: list[float], right: list[float]) -> float:
    """Compute cosine similarity between normalized or unnormalized vectors."""
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = sqrt(sum(value * value for value in left))
    right_norm = sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def detect_near_duplicates(
    articles: Iterable[CleanedArticle],
    embedding_model,
    threshold: float = 0.88,
    time_window: timedelta = timedelta(days=7),
    known_articles: Iterable[dict] | None = None,
) -> tuple[list[CleanedArticle], int]:
    """Remove semantically near-identical articles before embedding them.

    Short titles are not enough for this check, so each article uses title plus
    cleaned content. Candidates are limited to a publication-time window and
    lower-quality title-only matches are not used by themselves.

    Known articles should carry their stored Qdrant vector under "vector" so
    they are not re-embedded (and re-billed) on every run; any without one
    are embedded here.
    """
    article_list = list(articles)
    known_article_list = list(known_articles or [])
    if not article_list or (len(article_list) < 2 and not known_article_list):
        return article_list, 0

    texts = [
        f"{_normalized_title(article)}\n\n{article['content']}".strip()
        for article in article_list
    ]
    missing = [
        article for article in known_article_list if not article.get("vector")
    ]
    missing_texts = [
        f"{article.get('title', '')}\n\n{article.get('content', '')}".strip()
        for article in missing
    ]
    vectors = embedding_model.embed_documents(texts + missing_texts)
    article_vectors = vectors[:len(article_list)]
    for article, vector in zip(missing, vectors[len(article_list):]):
        article["vector"] = vector
    known_vectors = [article["vector"] for article in known_article_list]

    kept: list[CleanedArticle] = []
    kept_vectors: list[list[float]] = []
    removed = 0

    for article, vector in zip(article_list, article_vectors):
        duplicate = False
        candidates = list(zip(kept, kept_vectors))
        candidates.extend(zip(known_article_list, known_vectors))

        for candidate, candidate_vector in candidates:
            time_distance = abs(
                article["published_at"] - candidate["published_at"]
            )
            if time_distance > time_window:
                continue

            if _embedding_similarity(vector, candidate_vector) >= threshold:
                duplicate = True
                break

        if duplicate:
            removed += 1
            continue

        kept.append(article)
        kept_vectors.append(vector)

    return kept, removed
