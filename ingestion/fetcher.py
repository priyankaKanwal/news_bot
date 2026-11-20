"""Fetch and parse RSS feeds."""

import logging
import time

import feedparser
import requests

from ingestion.config_loader import FeedConfig

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 15
MAX_ATTEMPTS = 3
RETRY_DELAY = 2
HEADERS = {"User-Agent": "NewsBotRAG/1.0 (RSS reader)"}


class FeedFetchError(RuntimeError):
    """Raised when a feed cannot be fetched or parsed."""


def fetch_feed(feed: FeedConfig) -> list[feedparser.FeedParserDict]:
    """Fetch one feed and return its parsed entries.

    Request failures are retried with exponential delays. Parsing errors are
    raised immediately because retrying the same response cannot fix them.
    """
    delay = RETRY_DELAY
    response = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = requests.get(
                feed["url"],
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            break
        except requests.RequestException as error:
            if attempt == MAX_ATTEMPTS:
                raise FeedFetchError(
                    f"Feed {feed['name']!r} ({feed['url']}) failed after "
                    f"{MAX_ATTEMPTS} attempts: {error}"
                ) from error

            logger.warning(
                "Feed %s attempt %d/%d failed: %s",
                feed["url"],
                attempt,
                MAX_ATTEMPTS,
                error,
            )
            time.sleep(delay)
            delay *= 2

    if response is None:
        raise FeedFetchError(
            f"Feed {feed['name']!r} ({feed['url']}) returned no response."
        )

    parsed = feedparser.parse(response.content)

    if parsed.bozo and not parsed.entries:
        raise FeedFetchError(
            f"Feed {feed['name']!r} ({feed['url']}) could not be parsed: "
            f"{parsed.bozo_exception}"
        )

    if parsed.bozo:
        logger.warning(
            "Feed %s had parse issues; keeping %d recovered entries: %s",
            feed["url"],
            len(parsed.entries),
            parsed.bozo_exception,
        )

    return parsed.entries
