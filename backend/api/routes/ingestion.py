from fastapi import APIRouter

from ingestion.ingestion_service import run_ingestion

router = APIRouter()


@router.post("/ingestion/run")
def start_ingestion():
    """Run one ingestion pass for the feeds configured in feeds.yaml."""
    return run_ingestion()
