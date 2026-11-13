"""The ONE place that defines the "last 30 days" rule.

Search filtering and the cleanup job must both import from here,
so they can never disagree about which articles are recent.

Rule: an article is recent if its ORIGINAL publication time is
within the last 30 x 24 hours (UTC). Ingestion time is never used.
"""

from datetime import datetime, timedelta, timezone

WINDOW_DAYS = 30

# Feeds sometimes have clocks slightly ahead; allow a small margin
# but reject dates that are clearly in the future (bad data).
FUTURE_TOLERANCE = timedelta(days=1)


def _now(now=None):
    return now or datetime.now(timezone.utc)


def cutoff_datetime(now=None):
    """Oldest publication time we still keep."""
    return _now(now) - timedelta(days=WINDOW_DAYS)


def cutoff_timestamp(now=None):
    """Same cutoff as a UTC Unix timestamp (seconds).

    Store published_at in Qdrant as this kind of number so the
    vector DB can filter with a simple range query.
    """
    return cutoff_datetime(now).timestamp()


def is_within_window(published_at, now=None):
    """True if published_at falls inside the rolling 30-day window."""
    if published_at is None:
        return False

    current = _now(now)

    return (
        cutoff_datetime(current)
        <= published_at
        <= current + FUTURE_TOLERANCE
    )
