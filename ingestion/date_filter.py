"""Apply the 30-day publication window during ingestion."""

from collections import Counter
from datetime import datetime, timedelta, timezone

from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, FilterSelector, Range

from ingestion.cleaner import CleanedArticle

WINDOW_DAYS = 30
FUTURE_TOLERANCE = timedelta(days=1)
PUBLISHED_TS_KEY = "metadata.published_ts"


def cutoff_datetime(now: datetime | None = None) -> datetime:
    """Return the oldest included publication time in UTC."""
    return _now(now) - timedelta(days=WINDOW_DAYS)


def cutoff_timestamp(now: datetime | None = None) -> float:
    """Return the publication cutoff as a Unix timestamp."""
    return cutoff_datetime(now).timestamp()


def is_within_window(
    published_at: datetime,
    now: datetime | None = None,
) -> bool:
    """Check that a publication time is within the window."""
    if published_at.tzinfo is None or published_at.utcoffset() is None:
        raise ValueError("published_at must be timezone-aware.")

    published_utc = published_at.astimezone(timezone.utc)
    current = _now(now)
    return cutoff_datetime(current) <= published_utc <= current + FUTURE_TOLERANCE


def filter_articles(
    articles: list[CleanedArticle],
    now: datetime | None = None,
) -> tuple[list[CleanedArticle], Counter[str]]:
    """Return in-window articles and counts for skipped date categories."""
    current = _now(now)
    cutoff = cutoff_datetime(current)
    included = []
    skipped: Counter[str] = Counter()

    for article in articles:
        published_at = article["published_at"]
        in_window = is_within_window(published_at, current)
        if published_at < cutoff:
            skipped["older than 30 days"] += 1
        elif not in_window:
            skipped["published in the future"] += 1
        else:
            included.append(article)

    return included, skipped


def delete_expired_articles(
    client: QdrantClient,
    collection_name: str,
    now: datetime | None = None,
) -> int:
    """Delete expired article chunks from Qdrant and return the count."""
    expired = Filter(
        must=[
            FieldCondition(
                key=PUBLISHED_TS_KEY,
                range=Range(lt=cutoff_timestamp(now)),
            )
        ]
    )
    count = client.count(
        collection_name=collection_name,
        count_filter=expired,
        exact=True,
    ).count

    if count:
        client.delete(
            collection_name=collection_name,
            points_selector=FilterSelector(filter=expired),
        )

    return count


def _now(value: datetime | None) -> datetime:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None or current.utcoffset() is None:
        raise ValueError("now must be timezone-aware.")
    return current.astimezone(timezone.utc)
