from fastapi import APIRouter

from backend.controllers.health_controller import get_health

router = APIRouter()


@router.get("/health")
def health_check():
    return get_health()
