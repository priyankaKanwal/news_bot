"""Run RSS ingestion from feeds to Qdrant."""

import logging
from collections import Counter
from datetime import datetime, timezone
from uuid import NAMESPACE_URL, uuid5

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert as postgresql_insert

from backend.db.models import Article
from backend.db.postgres import Base, SessionLocal, engine
from ingestion.cleaner import CleanedArticle, clean_article
from ingestion.config_loader import FeedConfig, load_feeds
from ingestion.date_filter import (
    cutoff_datetime,
    delete_expired_articles,
    filter_articles,
)
from ingestion.deduplicator import deduplicate_articles, detect_near_duplicates
from ingestion.fetcher import FeedFetchError, fetch_feed
from ingestion.normalizer import normalize_entry
from rag.config import COLLECTION_NAME, NEAR_DUPLICATE_THRESHOLD
from rag.vector_store import create_vector_store, get_embedding_model

logger = logging.getLogger(__name__)

splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=100,
    add_start_index=True,
)


def build_documents(
    article: CleanedArticle,
) -> tuple[list[Document], list[str]]:
    """Build chunks with retrieval metadata and stable Qdrant IDs."""
    text = f"{article['title']}\n\n{article['content']}"
    published_at = article["published_at"]
    metadata = {
        "article_id": article["article_id"],
        "title": article["title"],
        "publisher": article["publisher"],
        "category": article["category"],
        "article_url": article["url"],
        "source": article["url"],
        "author": article["author"],
        "image_url": article["image_url"],
        "published_at": published_at.isoformat(),
        "published_ts": published_at.timestamp(),
    }
    documents = splitter.create_documents([text], metadatas=[metadata])

    ids = []
    for index, document in enumerate(documents):
        document.metadata["chunk_index"] = index
        ids.append(
            str(uuid5(NAMESPACE_URL, f"{article['article_id']}:{index}"))
        )

    return documents, ids


def _known_article_ids(client) -> set[str]:
    """Load stored article IDs so reruns skip already embedded articles."""
    article_ids = set()
    offset = None

    while True:
        points, offset = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=256,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        for point in points:
            metadata = (point.payload or {}).get("metadata", {})
            article_id = metadata.get("article_id")
            if article_id:
                article_ids.add(article_id)

        if offset is None:
            return article_ids


def _known_article_context(client) -> list[dict]:
    """Load stored chunk vectors and publication dates for duplicate checks.

    Reusing the stored vectors avoids re-embedding every known chunk through
    the Jina API on each ingestion run.
    """
    articles = []
    offset = None

    while True:
        points, offset = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=256,
            offset=offset,
            with_payload=True,
            with_vectors=True,
        )
        for point in points:
            payload = point.payload or {}
            metadata = payload.get("metadata", {})
            published_ts = metadata.get("published_ts")
            if published_ts is None:
                continue

            articles.append({
                "title": metadata.get("title", ""),
                "content": payload.get("page_content", ""),
                "vector": point.vector,
                "published_at": datetime.fromtimestamp(
                    float(published_ts),
                    tz=timezone.utc,
                ),
            })

        if offset is None:
            return articles


def _process_feed(feed: FeedConfig, now: datetime) -> tuple[list[CleanedArticle], dict]:
    """Fetch and validate one feed, keeping its failures in the report."""
    stats = {
        "feed": feed["name"],
        "url": feed["url"],
        "fetched": 0,
        "kept": 0,
        "skipped": Counter(),
        "error": None,
    }

    try:
        entries = fetch_feed(feed)
    except FeedFetchError as error:
        stats["error"] = str(error)
        logger.error("Feed failed: %s - %s", feed["url"], error)
        return [], stats

    stats["fetched"] = len(entries)
    cleaned_articles = []

    for entry in entries:
        normalized = normalize_entry(entry, feed)
        article, reason = clean_article(normalized)
        if article is None:
            stats["skipped"][reason] += 1
        else:
            cleaned_articles.append(article)

    recent_articles, skipped_dates = filter_articles(cleaned_articles, now)
    stats["skipped"].update(skipped_dates)
    stats["kept"] = len(recent_articles)
    return recent_articles, stats


def _store_articles(articles: list[CleanedArticle]) -> int:
    """Save articles without failing when a previous run already inserted them."""
    if not articles:
        return 0

    rows = [
        {
            "article_id": article["article_id"],
            "title": article["title"],
            "content": article["content"],
            "url": article["url"],
            "publisher": article["publisher"],
            "category": article["category"],
            "published_at": article["published_at"],
            "guid": article["guid"],
            "author": article["author"],
            "image_url": article["image_url"],
            "ingested_at": datetime.now(timezone.utc),
        }
        for article in articles
    ]

    with SessionLocal.begin() as db:
        result = db.execute(
            postgresql_insert(Article).values(rows).on_conflict_do_nothing()
        )
        return result.rowcount or 0


def run_ingestion() -> dict:
    """Fetch, clean, filter, deduplicate, and store the configured feeds."""
    Base.metadata.create_all(bind=engine)
    feeds = load_feeds()
    now = datetime.now(timezone.utc)
    vector_store, client = create_vector_store()

    try:
        deleted_chunks = delete_expired_articles(client, COLLECTION_NAME, now)
        with SessionLocal.begin() as db:
            deleted_articles = db.execute(
                delete(Article).where(Article.published_at < cutoff_datetime(now))
            ).rowcount
        known_ids = _known_article_ids(client)
        known_articles = _known_article_context(client)

        articles = []
        feed_reports = []
        failed_feeds = 0

        for feed in feeds:
            feed_articles, stats = _process_feed(feed, now)
            articles.extend(feed_articles)
            feed_reports.append(stats)
            failed_feeds += stats["error"] is not None

        unique_articles, duplicates_removed = deduplicate_articles(
            articles,
            known_article_ids=known_ids.copy(),
        )
        unique_articles, near_duplicates_removed = detect_near_duplicates(
            unique_articles,
            get_embedding_model(),
            threshold=NEAR_DUPLICATE_THRESHOLD,
            known_articles=known_articles,
        )
        duplicates_removed += near_duplicates_removed
        articles_saved = _store_articles(unique_articles)

        documents = []
        document_ids = []
        for article in unique_articles:
            chunks, chunk_ids = build_documents(article)
            documents.extend(chunks)
            document_ids.extend(chunk_ids)

        if documents:
            vector_store.add_documents(documents=documents, ids=document_ids)

        return {
            "feeds": feed_reports,
            "failed_feeds": failed_feeds,
            "duplicates_removed": duplicates_removed,
            "expired_articles_deleted": deleted_articles or 0,
            "expired_chunks_deleted": deleted_chunks,
            "articles_saved": articles_saved,
            "stored_articles": len(unique_articles),
            "stored_chunks": len(documents),
        }
    finally:
        client.close()


def print_report(report: dict) -> None:
    """Print a concise summary of an ingestion run."""
    print("\nINGESTION REPORT")
    for feed in report["feeds"]:
        print(f"\n{feed['feed']} ({feed['url']})")
        if feed["error"]:
            print(f"  failed: {feed['error']}")
            continue

        print(f"  fetched: {feed['fetched']}  kept: {feed['kept']}")
        for reason, count in sorted(feed["skipped"].items()):
            print(f"  skipped ({reason}): {count}")

    print("\nSUMMARY")
    print(f"  failed feeds: {report['failed_feeds']}")
    print(f"  duplicate articles skipped: {report['duplicates_removed']}")
    print(f"  expired articles deleted: {report['expired_articles_deleted']}")
    print(f"  expired chunks deleted: {report['expired_chunks_deleted']}")
    print(f"  articles saved to PostgreSQL: {report['articles_saved']}")
    print(f"  new articles indexed in Qdrant: {report['stored_articles']}")
    print(f"  chunks stored: {report['stored_chunks']}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    print_report(run_ingestion())
