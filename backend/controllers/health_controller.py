from fastapi.responses import JSONResponse

from backend.services.health_service import check_application_health


def get_health():
    health = check_application_health()
    status_code = 200 if health["status"] == "healthy" else 503
    return JSONResponse(status_code=status_code, content=health)
