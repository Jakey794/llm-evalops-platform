import json
import logging
import time
import uuid

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.datasets import router as datasets_router
from app.api.routes.eval_runs import router as eval_runs_router
from app.api.routes.health import router as health_router
from app.api.routes.model_configs import router as model_configs_router
from app.api.routes.prompt_versions import router as prompt_versions_router
from app.config import get_settings
from app.security import enforce_rate_limit

audit_logger = logging.getLogger("uvicorn.error")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        docs_url="/docs" if settings.api_docs_enabled else None,
        redoc_url="/redoc" if settings.api_docs_enabled else None,
        openapi_url="/openapi.json" if settings.api_docs_enabled else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )

    @app.middleware("http")
    async def audit_request(request: Request, call_next):
        started = time.monotonic()
        supplied_request_id = request.headers.get("x-request-id", "")
        try:
            request_id = str(uuid.UUID(supplied_request_id))
        except ValueError:
            request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            principal = getattr(request.state, "principal", None)
            audit_logger.info(
                json.dumps(
                    {
                        "event": "http.request",
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "status": status_code,
                        "duration_ms": round((time.monotonic() - started) * 1000, 2),
                        "subject": getattr(principal, "subject", None),
                        "role": getattr(principal, "role", None),
                    },
                    separators=(",", ":"),
                )
            )

    app.include_router(health_router)
    protected = [Depends(enforce_rate_limit)]
    app.include_router(datasets_router, dependencies=protected)
    app.include_router(eval_runs_router, dependencies=protected)
    app.include_router(model_configs_router, dependencies=protected)
    app.include_router(prompt_versions_router, dependencies=protected)

    return app


app = create_app()
