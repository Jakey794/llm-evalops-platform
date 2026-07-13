from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "LLM EvalOps Backend"
    service_name: str = "llm-evalops-backend"
    version: str = "0.1.0"
    backend_cors_origins: str = "http://localhost:3000"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/evalops"
    openai_api_key: str | None = None
    openai_timeout_seconds: float = Field(default=30.0, gt=0)
    llm_judge_provider: str = Field(default="gemini", min_length=1)
    llm_judge_enabled: bool = False
    gemini_api_key: str | None = None
    llm_judge_model: str = Field(default="gemini-2.5-flash-lite", min_length=1)
    llm_judge_timeout_seconds: float = Field(default=30.0, gt=0)

    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
