from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_db
from app.main import create_app
from app.models import Base, ModelConfig


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    with testing_session() as db:
        db.add_all(
            [
                ModelConfig(
                    provider="gemini",
                    model_name="gemini-3.1-flash-lite",
                    temperature=0.0,
                    max_output_tokens=512,
                    response_format={"type": "json_object"},
                ),
                ModelConfig(
                    provider="openai",
                    model_name="gpt-4o-mini",
                    temperature=0.0,
                    max_output_tokens=256,
                    response_format=None,
                ),
            ]
        )
        db.commit()

    def override_get_db() -> Generator[Session, None, None]:
        with testing_session() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_list_model_configs(client: TestClient) -> None:
    response = client.get("/model-configs")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert {item["provider"] for item in body} == {"gemini", "openai"}
    assert all("id" in item and "model_name" in item for item in body)
    assert all("response_format" not in item for item in body)


def test_get_model_config(client: TestClient) -> None:
    listed = client.get("/model-configs").json()
    model_id = listed[0]["id"]

    response = client.get(f"/model-configs/{model_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == model_id
    assert "response_format" in body
    assert body["max_output_tokens"] > 0


def test_get_model_config_not_found(client: TestClient) -> None:
    response = client.get("/model-configs/00000000-0000-0000-0000-000000000099")
    assert response.status_code == 404
    assert response.json()["detail"] == "Model config not found"
