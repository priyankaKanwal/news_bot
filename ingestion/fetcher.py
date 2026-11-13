"""Download RSS feeds. One broken feed must never stop the others."""

import logging
import time
from pathlib import Path

import feedparser
import requests
import yaml

logger = logging.getLogger(__name__)

FEEDS_FILE = Path(__file__).resolve().parent.parent / "feeds.yaml"

REQUEST_TIMEOUT = 15   # seconds
MAX_ATTEMPTS = 3
RETRY_DELAY = 2        # seconds, doubled after each failed attempt

# Identify ourselves politely; some publishers block the default
# python-requests agent.
HEADERS = {"User-Agent": "NewsBotRAG/1.0 (learning project; RSS reader)"}


def load_feed_config(path=FEEDS_FILE):
    with open(path, encoding="utf-8") as file:
        return yaml.safe_load(file)["feeds"]


def fetch_feed(feed_config):
    """Return a list of raw entries for one feed.

    Retries a few times on network errors. Raises the last error if
    every attempt fails - the caller decides what to do about it.
    """
    url = feed_config["url"]
    delay = RETRY_DELAY
    last_error = None

    for attempt in range(1, MAX_ATTEMPTS + 1):

        try:
            response = requests.get(
                url,
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()

            parsed = feedparser.parse(response.content)

            # bozo = feedparser flagged malformed XML. If we still got
            # entries it is usable; if not, treat it as a failure.
            if parsed.bozo and not parsed.entries:
                raise ValueError(f"unreadable feed: {parsed.bozo_exception}")

            return parsed.entries

        except Exception as error:

            last_error = error

            logger.warning(
                "Feed %s attempt %d/%d failed: %s",
                url, attempt, MAX_ATTEMPTS, error
            )

            if attempt < MAX_ATTEMPTS:
                time.sleep(delay)
                delay *= 2

    raise last_error
