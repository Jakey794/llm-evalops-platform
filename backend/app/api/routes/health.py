from fastapi import APIRouter, Response, status
from pydantic import BaseModel

from app.config import get_settings
from app.db import check_database_connection


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    database: str


router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check(response: Response) -> HealthResponse:
    settings = get_settings()
    database_is_available = check_database_connection()

    if not database_is_available:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthResponse(
        status="ok" if database_is_available else "degraded",
        service=settings.service_name,
        version=settings.version,
        database="ok" if database_is_available else "error",
    )
