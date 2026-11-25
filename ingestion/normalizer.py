"""Map parsed RSS entries to a common article shape."""

from collections.abc import Mapping
from typing import TypedDict

from ingestion.config_loader import FeedConfig


class NormalizedArticle(TypedDict):
    title: str
    content: str
    url: str
    published_at: str | None
    publisher: str
    category: str
    guid: str | None
    author: str | None
    image_url: str | None


def _text(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _summary(entry: Mapping[str, object]) -> str:
    return _text(entry.get("summary")) or ""


def _first_image(entry: Mapping[str, object]) -> str | None:
    for field in ("media_content", "media_thumbnail"):
        items = entry.get(field)
        if isinstance(items, list):
            for item in items:
                if isinstance(item, Mapping):
                    image_url = _text(item.get("url"))
                    if image_url:
                        return image_url

    links = entry.get("links")
    if isinstance(links, list):
        for link in links:
            if isinstance(link, Mapping):
                link_type = _text(link.get("type")) or ""
                image_url = _text(link.get("href"))
                if link_type.lower().startswith("image") and image_url:
                    return image_url

    return None


def normalize_entry(
    entry: Mapping[str, object],
    feed: FeedConfig,
) -> NormalizedArticle:
    """Map feed-specific fields to the shared article shape.

    Text and dates remain raw here; the cleaner handles HTML and date parsing.
    """
    return {
        "title": _text(entry.get("title")) or "",
        "content": _summary(entry),
        "url": _text(entry.get("link")) or "",
        "published_at": (
            _text(entry.get("published")) or _text(entry.get("updated"))
        ),
        "publisher": feed["name"],
        "category": feed["category"],
        "guid": _text(entry.get("id")),
        "author": _text(entry.get("author")),
        "image_url": _first_image(entry),
    }
