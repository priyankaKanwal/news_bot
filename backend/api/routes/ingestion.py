from threading import Lock

from fastapi import APIRouter, HTTPException

from ingestion.ingestion_service import run_ingestion

router = APIRouter()
ingestion_lock = Lock()


@router.post("/ingestion/run")
def start_ingestion():
    """Run one ingestion pass for the feeds configured in feeds.yaml."""
    if not ingestion_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Feed ingestion is already running.")

    try:
        return run_ingestion()
    finally:
        ingestion_lock.release()
