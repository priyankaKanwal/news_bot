"""Delete articles older than 30 days (PRD Module 5).

Run:  python -m ingestion.cleanup

Deletes by FILTER on published_ts, so every chunk of an expired
article goes with it - not just a parent record. Uses the same
cutoff as the search filter (ingestion.filters).
"""

import logging

from qdrant_client.models import FieldCondition, Filter, FilterSelector, Range

from ingestion.filters import cutoff_datetime, cutoff_timestamp
from rag.config import COLLECTION_NAME
from rag.vector_store import PUBLISHED_TS_KEY, create_vector_store

logger = logging.getLogger(__name__)


def delete_expired(client):
    """Remove every chunk published before the cutoff. Returns the count."""

    expired = Filter(
        must=[
            FieldCondition(
                key=PUBLISHED_TS_KEY,
                range=Range(lt=cutoff_timestamp())
            )
        ]
    )

    count = client.count(
        collection_name=COLLECTION_NAME,
        count_filter=expired,
        exact=True
    ).count

    if count:
        client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=FilterSelector(filter=expired)
        )

    logger.info(
        "Cleanup: deleted %d chunks published before %s",
        count, cutoff_datetime().isoformat()
    )

    return count


if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)

    _store, client = create_vector_store()

    try:
        deleted = delete_expired(client)

        print(f"Deleted {deleted} expired chunks.")
        print("Chunks remaining:", client.count(COLLECTION_NAME).count)

    finally:
        client.close()
