import logging

from sqlalchemy import text

from backend.db.postgres import engine
from rag.config import GOOGLE_API_KEY, JINA_API_KEY
from rag.vector_store import get_client

logger = logging.getLogger(__name__)


def check_application_health() -> dict[str, object]:
    dependencies: dict[str, str] = {"api": "healthy"}

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        dependencies["postgres"] = "healthy"
    except Exception:
        logger.exception("PostgreSQL health check failed.")
        dependencies["postgres"] = "unavailable"

    client = None
    try:
        client = get_client()
        client.get_collections()
        dependencies["qdrant"] = "healthy"
    except Exception:
        logger.exception("Qdrant health check failed.")
        dependencies["qdrant"] = "unavailable"
    finally:
        if client is not None:
            client.close()

    dependencies["gemini"] = "configured" if GOOGLE_API_KEY else "missing_configuration"
    dependencies["jina"] = "configured" if JINA_API_KEY else "missing_configuration"

    healthy = all(
        status in {"healthy", "configured"}
        for status in dependencies.values()
    )
    return {
        "status": "healthy" if healthy else "unhealthy",
        "dependencies": dependencies,
    }
