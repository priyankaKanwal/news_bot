"""Turn a raw feedparser entry into a clean Article (or None).

Cleaning steps (PRD Module 2):
  - strip HTML tags
  - decode HTML entities, remove control characters
  - normalise whitespace
  - parse the date into UTC (missing date -> updated time -> skip)
  - validate that the article has enough text
"""

import html
import re
from calendar import timegm
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from uuid import NAMESPACE_URL, uuid5

from bs4 import BeautifulSoup

from ingestion.models import Article

MIN_TEXT_LENGTH = 40  # title + content must have at least this many chars

# Query parameters that only track marketing, not identify the article
TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term",
    "utm_content", "fbclid", "gclid", "ocid", "at_medium", "at_campaign",
}

CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def clean_text(raw):
    """Remove HTML and tidy whitespace."""
    if not raw:
        return ""

    text = BeautifulSoup(raw, "html.parser").get_text(separator=" ")
    text = html.unescape(text)
    text = text.replace("\xa0", " ")
    text = CONTROL_CHARS.sub("", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def canonical_url(url):
    """Normalise a URL so the same article always gives the same string."""
    if not url:
        return ""

    parts = urlsplit(url.strip())

    query = [
        (key, value)
        for key, value in parse_qsl(parts.query)
        if key.lower() not in TRACKING_PARAMS
    ]

    path = parts.path.rstrip("/") or "/"

    return urlunsplit((
        parts.scheme.lower(),
        parts.netloc.lower(),
        path,
        urlencode(query),
        ""  # drop #fragment
    ))


def parse_published_at(entry):
    """Return a timezone-aware UTC datetime, or None.

    feedparser already converts dates to UTC time tuples.
    Order: published -> updated -> None (caller skips the article).
    """
    for field in ("published_parsed", "updated_parsed"):
        parsed = entry.get(field)

        if parsed:
            return datetime.fromtimestamp(timegm(parsed), tz=timezone.utc)

    return None


def _get_content(entry):
    """Prefer full content when the feed provides it, else the summary."""
    contents = entry.get("content")

    if contents:
        text = clean_text(contents[0].get("value", ""))
        if text:
            return text

    return clean_text(entry.get("summary", ""))


def _get_image(entry):
    for field in ("media_content", "media_thumbnail"):
        items = entry.get(field)
        if items and items[0].get("url"):
            return items[0]["url"]

    for link in entry.get("links", []):
        if link.get("type", "").startswith("image") and link.get("href"):
            return link["href"]

    return None


def entry_to_article(entry, feed_config, ingested_at=None):
    """Convert one feedparser entry into an Article.

    Returns (article, reason). If the entry is unusable,
    article is None and reason says why (for the ingestion log).
    """
    title = clean_text(entry.get("title", ""))
    url = canonical_url(entry.get("link", ""))

    if not title:
        return None, "missing title"

    if not url:
        return None, "missing url"

    published_at = parse_published_at(entry)

    if published_at is None:
        return None, "missing date"

    content = _get_content(entry)

    # Some feeds only give a headline; use it so the article isn't empty
    if not content:
        content = title

    if len(title) + len(content) < MIN_TEXT_LENGTH:
        return None, "too little text"

    article = Article(
        article_id=str(uuid5(NAMESPACE_URL, url)),
        title=title,
        content=content,
        publisher=feed_config["name"],
        published_at=published_at,
        category=feed_config.get("category", "General"),
        article_url=url,
        ingested_at=ingested_at or datetime.now(timezone.utc),
        guid=entry.get("id") or None,
        author=clean_text(entry.get("author", "")) or None,
        image_url=_get_image(entry),
    )

    return article, None
