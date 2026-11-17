"""Remove duplicate articles from an ingestion batch."""

import hashlib
import re
from collections.abc import Iterable

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
