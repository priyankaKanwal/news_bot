"""Remove duplicate articles.

Checks, cheapest first:
  1. canonical URL
  2. GUID from the feed
  3. hash of the normalised title + content (same story, different URL)

Do this BEFORE embedding so we never pay to embed a duplicate.
"""

import hashlib
import re


def content_hash(article):
    text = f"{article.title} {article.content}".lower()
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def deduplicate(articles, known_urls=None):
    """Return (unique_articles, number_removed).

    known_urls: URLs already stored (e.g. in Qdrant) - will be
    used later so daily runs only process NEW articles.
    """
    seen_urls = set(known_urls or [])
    seen_guids = set()
    seen_hashes = set()

    unique = []

    for article in articles:

        digest = content_hash(article)

        if (
            article.article_url in seen_urls
            or (article.guid and article.guid in seen_guids)
            or digest in seen_hashes
        ):
            continue

        seen_urls.add(article.article_url)
        seen_hashes.add(digest)

        if article.guid:
            seen_guids.add(article.guid)

        unique.append(article)

    return unique, len(articles) - len(unique)
