"""Fetch news and store NEW articles in Qdrant.

Run:  python -m ingestion.ingest

Local Qdrant allows one process at a time, so stop the chat server
before running this.
"""

import logging
from uuid import NAMESPACE_URL, uuid5

from langchain_text_splitters import RecursiveCharacterTextSplitter

from ingestion.pipeline import print_report, run_ingestion
from rag.config import COLLECTION_NAME
from rag.vector_store import create_vector_store

logger = logging.getLogger(__name__)

# Same settings as rag/text_splitter.py. Most RSS items are shorter
# than 500 characters, so they stay as a single chunk.
splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=100,
    add_start_index=True
)


def article_to_chunks(article):
    """Split one Article into LangChain Documents + stable IDs.

    The title is part of the embedded text: many feeds give only a
    short summary, so the headline carries much of the meaning.
    Every chunk repeats the article metadata, so any chunk can be
    shown with its source link and date.
    """
    text = f"{article.title}\n\n{article.content}"

    metadata = {
        "article_id": article.article_id,
        "title": article.title,
        "publisher": article.publisher,
        "category": article.category,
        "article_url": article.article_url,
        "source": article.article_url,
        "author": article.author,
        "image_url": article.image_url,
        # ISO strings for display, number for Qdrant range filtering
        "published_at": article.published_at.isoformat(),
        "published_ts": article.published_at.timestamp(),
        "ingested_at": article.ingested_at.isoformat(),
    }

    documents = splitter.create_documents([text], metadatas=[metadata])

    ids = []

    for index, document in enumerate(documents):
        document.metadata["chunk_index"] = index
        # Same article + same chunk number -> same ID, so re-ingesting
        # overwrites instead of duplicating.
        ids.append(str(uuid5(NAMESPACE_URL, f"{article.article_id}:{index}")))

    return documents, ids


def get_known_urls(client):
    """URLs of every article already stored (to skip duplicates)."""
    urls = set()
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
            url = (point.payload or {}).get("metadata", {}).get("article_url")
            if url:
                urls.add(url)

        if offset is None:
            break

    return urls


def ingest():
    """Fetch -> clean -> dedupe (against Qdrant too) -> embed -> store."""

    vector_store, client = create_vector_store()

    try:
        known_urls = get_known_urls(client)

        print(f"Already stored: {len(known_urls)} articles")

        articles, report = run_ingestion(known_urls=known_urls)

        print_report(report)

        if not articles:
            print("\nNo new articles to store.")
            return report

        documents, ids = [], []

        for article in articles:
            chunk_docs, chunk_ids = article_to_chunks(article)
            documents.extend(chunk_docs)
            ids.extend(chunk_ids)

        print(f"\nEmbedding {len(documents)} chunks "
              f"from {len(articles)} new articles...")

        vector_store.add_documents(documents=documents, ids=ids)

        total = client.count(COLLECTION_NAME).count

        print(f"Stored. Chunks in Qdrant now: {total}")

        report["stored_articles"] = len(articles)
        report["stored_chunks"] = len(documents)

        return report

    finally:
        client.close()


if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)

    ingest()
