"""Fetch -> clean -> filter (30 days) -> deduplicate.

Run directly to see a per-feed report:
    python -m ingestion.pipeline
"""

import logging
from collections import Counter
from datetime import datetime, timezone

from ingestion.cleaner import entry_to_article
from ingestion.dedup import deduplicate
from ingestion.fetcher import fetch_feed, load_feed_config
from ingestion.filters import is_within_window

logger = logging.getLogger(__name__)


def run_ingestion(known_urls=None):
    """Return (articles, report).

    articles: clean, recent, unique Article objects, newest first.
    report: per-feed numbers + skip reasons (for logs and tests).
    """
    feeds = load_feed_config()
    ingested_at = datetime.now(timezone.utc)

    collected = []
    report = {"feeds": [], "failed_feeds": 0}

    for feed in feeds:

        stats = {
            "feed": f"{feed['name']} ({feed['category']})",
            "url": feed["url"],
            "fetched": 0,
            "kept": 0,
            "skipped": Counter(),
            "error": None,
        }

        try:
            entries = fetch_feed(feed)

        except Exception as error:
            # One bad feed must not stop the run
            stats["error"] = str(error)
            report["failed_feeds"] += 1
            report["feeds"].append(stats)
            logger.error("Feed failed: %s - %s", feed["url"], error)
            continue

        stats["fetched"] = len(entries)

        for entry in entries:

            article, reason = entry_to_article(entry, feed, ingested_at)

            if article is None:
                stats["skipped"][reason] += 1
                continue

            if not is_within_window(article.published_at):
                stats["skipped"]["older than 30 days"] += 1
                continue

            collected.append(article)
            stats["kept"] += 1

        report["feeds"].append(stats)

    unique, removed = deduplicate(collected, known_urls)

    unique.sort(key=lambda article: article.published_at, reverse=True)

    report["duplicates_removed"] = removed
    report["total_articles"] = len(unique)

    return unique, report


def print_report(report):
    print("\n" + "=" * 60)
    print("INGESTION REPORT")
    print("=" * 60)

    for stats in report["feeds"]:

        print(f"\n{stats['feed']}")
        print(f"  {stats['url']}")

        if stats["error"]:
            print(f"  FAILED: {stats['error']}")
            continue

        print(f"  fetched: {stats['fetched']}   kept: {stats['kept']}")

        for reason, count in stats["skipped"].items():
            print(f"  skipped ({reason}): {count}")

    print("\n" + "-" * 60)
    print("Failed feeds:      ", report["failed_feeds"])
    print("Duplicates removed:", report["duplicates_removed"])
    print("Final articles:    ", report["total_articles"])


if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)

    articles, report = run_ingestion()

    print_report(report)

    print("\nLatest 5 articles:\n")

    for article in articles[:5]:
        print(f"- [{article.published_at:%Y-%m-%d %H:%M} UTC] "
              f"{article.publisher}: {article.title}")
        print(f"  {article.article_url}")
