import logging
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.db import get_db
from app.main import create_app
from app.models import Base
from app.security import rate_limiter
from tests.conftest import OPERATOR_HEADERS, VIEWER_HEADERS


@pytest.fixture
def app_client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db() -> Generator[Session, None, None]:
        with testing_session() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_protected_route_rejects_missing_and_invalid_tokens(app_client: TestClient) -> None:
    missing = app_client.get("/datasets")
    invalid = app_client.get("/datasets", headers={"Authorization": "Bearer invalid"})

    assert missing.status_code == 401
    assert missing.headers["www-authenticate"] == "Bearer"
    assert invalid.status_code == 401


def test_viewer_can_read_but_cannot_create(app_client: TestClient) -> None:
    assert app_client.get("/datasets", headers=VIEWER_HEADERS).status_code == 200
    denied = app_client.post("/datasets/import-jsonl", json={}, headers=VIEWER_HEADERS)

    assert denied.status_code == 403
    assert denied.json() == {"detail": "Operator role required"}


def test_operator_reaches_write_validation(app_client: TestClient) -> None:
    response = app_client.post("/datasets/import-jsonl", json={}, headers=OPERATOR_HEADERS)

    assert response.status_code == 422


def test_rate_limit_returns_retry_after(monkeypatch, app_client: TestClient) -> None:
    monkeypatch.setenv("RATE_LIMIT_READ_REQUESTS", "1")
    get_settings.cache_clear()
    rate_limiter.clear()
    assert app_client.get("/datasets", headers=VIEWER_HEADERS).status_code == 200
    limited = app_client.get("/datasets", headers=VIEWER_HEADERS)

    assert limited.status_code == 429
    assert int(limited.headers["retry-after"]) >= 1


def test_health_remains_public() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code in {200, 503}
    assert response.json()["service"] == "llm-evalops-backend"


def test_audit_log_excludes_authorization_secret(caplog, app_client: TestClient) -> None:
    caplog.set_level(logging.INFO, logger="uvicorn.error")
    app_client.get("/datasets", headers=VIEWER_HEADERS)

    messages = [record.getMessage() for record in caplog.records if record.name == "uvicorn.error"]
    assert any('"event":"http.request"' in message for message in messages)
    assert all(VIEWER_HEADERS["Authorization"] not in message for message in messages)
