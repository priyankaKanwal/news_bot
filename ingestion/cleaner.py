"""Clean and validate normalized RSS articles."""

import html
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import TypedDict
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import NAMESPACE_URL, uuid5

from bs4 import BeautifulSoup

from ingestion.normalizer import NormalizedArticle

TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "ocid",
    "at_medium",
    "at_campaign",
}

CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class CleanedArticle(TypedDict):
    article_id: str
    title: str
    content: str
    url: str
    published_at: datetime
    publisher: str
    category: str
    guid: str | None
    author: str | None
    image_url: str | None


def clean_text(raw: str) -> str:
    """Strip markup and normalize whitespace."""
    text = BeautifulSoup(raw, "html.parser").get_text(separator=" ")
    text = html.unescape(text).replace("\xa0", " ")
    text = CONTROL_CHARS.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


def canonical_url(url: str) -> str | None:
    """Remove tracking parameters and fragments from an article URL."""
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return None

    if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
        return None

    try:
        parts.port
    except ValueError:
        return None

    query = [
        (key, value)
        for key, value in parse_qsl(parts.query)
        if key.lower() not in TRACKING_PARAMS
    ]

    return urlunsplit((
        parts.scheme.lower(),
        parts.netloc.lower(),
        parts.path.rstrip("/") or "/",
        urlencode(query),
        "",
    ))


def parse_published_at(value: str | None) -> datetime | None:
    """Parse an RSS date and return an aware UTC datetime."""
    if not value:
        return None

    try:
        published_at = parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        try:
            published_at = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)

    return published_at.astimezone(timezone.utc)


def clean_article(
    article: NormalizedArticle,
) -> tuple[CleanedArticle | None, str | None]:
    """Return a cleaned article or a reason it should be skipped."""
    title = clean_text(article["title"])
    if not title:
        return None, "missing title"

    url = canonical_url(article["url"])
    if not url:
        return None, "missing or invalid url"

    published_at = parse_published_at(article["published_at"])
    if published_at is None:
        return None, "missing or invalid date"

    content = clean_text(article["content"]) or title

    author = clean_text(article["author"]) if article["author"] else None

    cleaned = CleanedArticle(
        article_id=str(uuid5(NAMESPACE_URL, url)),
        title=title,
        content=content,
        url=url,
        published_at=published_at,
        publisher=article["publisher"],
        category=article["category"],
        guid=article["guid"],
        author=author or None,
        image_url=article["image_url"],
    )

    return cleaned, None
