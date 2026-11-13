"""Daily news ingestion + 30-day cleanup (PRD Modules 4 and 5).

Run the scheduler (keeps running, fires once a day at INGEST_HOUR_UTC):
    python -m ingestion.scheduler

Run the daily job once, right now, then exit (good for testing):
    python -m ingestion.scheduler --once

Needs the Qdrant server (docker compose up -d) when the chat server is
running at the same time. See rag/config.py.
"""

import argparse
import logging
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from ingestion.cleanup import delete_expired
from ingestion.ingest import ingest
from rag.config import (
    INGEST_HOUR_UTC,
    INGEST_MAX_ATTEMPTS,
    INGEST_MINUTE_UTC,
    INGEST_RETRY_DELAY,
    LOG_FILE,
)
from rag.vector_store import create_vector_store

logger = logging.getLogger("news_bot.scheduler")


def setup_logging():
    """Log to the console and to a rotating file (1 MB x 5 files)."""
    log_path = Path(LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)-7s %(name)s: %(message)s"
    )

    file_handler = RotatingFileHandler(
        log_path, maxBytes=1_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers = [file_handler, console_handler]

    # These libraries log every HTTP request at INFO; keep the log readable.
    for noisy in ("httpx", "httpcore", "sentence_transformers", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def run_with_retries(name, function):
    """Run function(); on failure wait and try again (delay doubles).

    Returns the function's result, or None if every attempt failed.
    A failure is logged with its traceback but never raised, so one
    broken step cannot stop the next one.
    """
    delay = INGEST_RETRY_DELAY

    for attempt in range(1, INGEST_MAX_ATTEMPTS + 1):

        try:
            return function()

        except Exception:
            logger.exception(
                "%s failed (attempt %d/%d)",
                name, attempt, INGEST_MAX_ATTEMPTS
            )

            if attempt < INGEST_MAX_ATTEMPTS:
                logger.info("Retrying %s in %d seconds", name, delay)
                time.sleep(delay)
                delay *= 2

    logger.error("%s gave up after %d attempts", name, INGEST_MAX_ATTEMPTS)

    return None


def run_cleanup():
    _store, client = create_vector_store()

    try:
        return delete_expired(client)
    finally:
        client.close()


def daily_job():
    """Ingest new articles, then delete expired ones."""
    started = time.time()

    logger.info("===== Daily job started =====")

    report = run_with_retries("Ingestion", ingest)

    if report is None:
        logger.error("Ingestion FAILED - see traceback above")
    else:
        for feed in report["feeds"]:
            if feed["error"]:
                logger.warning(
                    "Feed unavailable: %s (%s)", feed["url"], feed["error"]
                )

        logger.info(
            "Ingestion OK: feeds_failed=%d duplicates_skipped=%d "
            "new_articles=%d new_chunks=%d",
            report["failed_feeds"],
            report["duplicates_removed"],
            report.get("stored_articles", 0),
            report.get("stored_chunks", 0),
        )

    # Cleanup runs even if ingestion failed
    deleted = run_with_retries("Cleanup", run_cleanup)

    if deleted is None:
        logger.error("Cleanup FAILED - see traceback above")
    else:
        logger.info("Cleanup OK: expired_chunks_deleted=%d", deleted)

    logger.info(
        "===== Daily job finished in %.1fs =====", time.time() - started
    )


def main():
    parser = argparse.ArgumentParser(description="Daily news ingestion job")
    parser.add_argument(
        "--once",
        action="store_true",
        help="run the daily job once now and exit"
    )
    args = parser.parse_args()

    setup_logging()

    if args.once:
        daily_job()
        return

    scheduler = BlockingScheduler(timezone="UTC")

    scheduler.add_job(
        daily_job,
        CronTrigger(hour=INGEST_HOUR_UTC, minute=INGEST_MINUTE_UTC),
        id="daily_news_job",
        max_instances=1,          # never run two at once
        coalesce=True,            # if several runs were missed, run once
        misfire_grace_time=3600,  # still run if the PC woke up within 1 h
    )

    logger.info(
        "Scheduler started. Daily job at %02d:%02d UTC. Ctrl+C to stop.",
        INGEST_HOUR_UTC, INGEST_MINUTE_UTC
    )

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")


if __name__ == "__main__":
    main()
