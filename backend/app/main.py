from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.datasets import router as datasets_router
from app.api.routes.eval_runs import router as eval_runs_router
from app.api.routes.health import router as health_router
from app.api.routes.model_configs import router as model_configs_router
from app.api.routes.prompt_versions import router as prompt_versions_router
from app.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(datasets_router)
    app.include_router(eval_runs_router)
    app.include_router(model_configs_router)
    app.include_router(prompt_versions_router)

    return app


app = create_app()
