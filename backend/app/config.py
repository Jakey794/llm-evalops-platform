from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "LLM EvalOps Backend"
    service_name: str = "llm-evalops-backend"
    version: str = "0.1.0"
    backend_cors_origins: str = "http://localhost:3000"
    backend_viewer_token: str | None = Field(default=None, min_length=32)
    backend_operator_token: str | None = Field(default=None, min_length=32)
    api_docs_enabled: bool = False
    rate_limit_window_seconds: int = Field(default=60, ge=1, le=3600)
    rate_limit_read_requests: int = Field(default=120, ge=1, le=10_000)
    rate_limit_write_requests: int = Field(default=10, ge=1, le=1000)
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/evalops"
    openai_api_key: str | None = None
    openai_timeout_seconds: float = Field(default=30.0, gt=0)
    llm_judge_provider: str = Field(default="gemini", min_length=1)
    llm_judge_enabled: bool = False
    gemini_api_key: str | None = None
    llm_judge_model: str = Field(default="gemini-3.1-flash-lite", min_length=1)
    llm_judge_timeout_seconds: float = Field(default=30.0, gt=0)

    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]

    @property
    def security_is_configured(self) -> bool:
        return bool(
            self.backend_viewer_token
            and self.backend_operator_token
            and self.backend_viewer_token != self.backend_operator_token
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
