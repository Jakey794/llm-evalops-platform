from fastapi import APIRouter
from pydantic import BaseModel

from app.config import get_settings


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    settings = get_settings()

    return HealthResponse(
        status="ok",
        service=settings.service_name,
        version=settings.version,
    )
