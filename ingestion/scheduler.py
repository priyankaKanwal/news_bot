"""Run RSS ingestion on a daily schedule."""

import logging
import os
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

from ingestion.ingestion_service import print_report, run_ingestion

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TIMEZONE = "Asia/Kolkata"
DEFAULT_HOUR = 2
DEFAULT_MINUTE = 0

logger = logging.getLogger(__name__)


def _schedule_time() -> tuple[int, int, str]:
    """Read and validate the daily schedule from environment variables."""
    try:
        hour = int(os.getenv("INGESTION_SCHEDULE_HOUR", str(DEFAULT_HOUR)))
        minute = int(os.getenv("INGESTION_SCHEDULE_MINUTE", str(DEFAULT_MINUTE)))
    except ValueError as error:
        raise ValueError(
            "INGESTION_SCHEDULE_HOUR and INGESTION_SCHEDULE_MINUTE must be integers."
        ) from error

    if not 0 <= hour <= 23:
        raise ValueError("INGESTION_SCHEDULE_HOUR must be between 0 and 23.")
    if not 0 <= minute <= 59:
        raise ValueError("INGESTION_SCHEDULE_MINUTE must be between 0 and 59.")

    timezone = os.getenv("INGESTION_TIMEZONE", DEFAULT_TIMEZONE).strip()
    if not timezone:
        raise ValueError("INGESTION_TIMEZONE must not be empty.")

    return hour, minute, timezone


def _run_scheduled_ingestion() -> None:
    """Run ingestion without allowing a failed run to stop future schedules."""
    logger.info("Starting scheduled ingestion.")
    try:
        report = run_ingestion()
    except Exception:
        logger.exception("Scheduled ingestion failed.")
        return

    print_report(report)
    logger.info(
        "Scheduled ingestion completed: %d feed(s) failed, %d article(s) stored, "
        "%d chunk(s) stored.",
        report["failed_feeds"],
        report["stored_articles"],
        report["stored_chunks"],
    )


def main() -> None:
    """Start the blocking scheduler; the first run occurs at the next schedule."""
    load_dotenv(PROJECT_ROOT / ".env")
    hour, minute, timezone = _schedule_time()
    scheduler = BlockingScheduler(timezone=timezone)
    scheduler.add_job(
        _run_scheduled_ingestion,
        trigger=CronTrigger(hour=hour, minute=minute, timezone=timezone),
        id="daily_news_ingestion",
        name="Daily news ingestion",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,
    )

    logger.info(
        "Daily ingestion scheduled for %02d:%02d (%s). Press Ctrl+C to stop.",
        hour,
        minute,
        timezone,
    )
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Ingestion scheduler stopped.")
        scheduler.shutdown(wait=False)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    main()
