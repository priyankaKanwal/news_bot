"""Standalone cleanup for expired news articles and vector chunks."""

import logging
from datetime import datetime, timezone

from backend.database import Base, SessionLocal, engine
from backend.models import Article
from ingestion.date_filter import cutoff_datetime, delete_expired_articles
from rag.config import COLLECTION_NAME
from rag.vector_store import get_client
from sqlalchemy import delete


logger = logging.getLogger(__name__)


def run_cleanup() -> dict:
    """Delete expired SQL articles and Qdrant chunks."""
    now = datetime.now(timezone.utc)
    cutoff = cutoff_datetime(now)
    client = None

    try:
        Base.metadata.create_all(bind=engine)
        client = get_client()
        deleted_chunks = delete_expired_articles(client, COLLECTION_NAME, now)

        with SessionLocal.begin() as db:
            deleted_articles = db.execute(
                delete(Article).where(Article.published_at < cutoff)
            ).rowcount

        report = {
            "status": "success",
            "cutoff": cutoff.isoformat(),
            "expired_articles_deleted": deleted_articles or 0,
            "expired_chunks_deleted": deleted_chunks,
        }
        logger.info(
            "Cleanup completed: %d article(s), %d chunk(s)",
            report["expired_articles_deleted"],
            report["expired_chunks_deleted"],
        )
        return report
    except Exception as error:
        logger.exception("Cleanup failed.")
        return {
            "status": "failed",
            "cutoff": cutoff_datetime().isoformat(),
            "expired_articles_deleted": 0,
            "expired_chunks_deleted": 0,
            "error": str(error),
        }
    finally:
        if client is not None:
            client.close()


def print_cleanup_report(report: dict) -> None:
    print("\nCLEANUP REPORT")
    print(f"  status: {report['status']}")
    print(f"  cutoff: {report['cutoff']}")
    print(
        "  expired articles deleted:"
        f" {report['expired_articles_deleted']}"
    )
    print(
        "  expired chunks deleted:"
        f" {report['expired_chunks_deleted']}"
    )
    if report.get("error"):
        print(f"  error: {report['error']}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    print_cleanup_report(run_cleanup())
