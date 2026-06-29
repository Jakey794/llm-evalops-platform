import json
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_db
from app.main import create_app
from app.models import Base


def make_test_case(**overrides: object) -> dict[str, object]:
    test_case: dict[str, object] = {
        "id": "support_001",
        "workflow_type": "support_classification",
        "input": {"ticket": "I was charged twice."},
        "expected_output": {"category": "billing"},
        "required_citations": [],
        "tags": ["billing"],
        "difficulty": "easy",
        "metadata": {"source": "seed"},
    }
    test_case.update(overrides)
    return test_case


def make_import_payload(*rows: dict[str, object]) -> dict[str, object]:
    return {
        "name": "Support Classification Smoke",
        "description": "Seed support ticket classification cases",
        "workflow_type": "support_classification",
        "source_filename": "support_classification.jsonl",
        "jsonl_content": "\n".join(json.dumps(row) for row in rows),
    }


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
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

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_import_valid_jsonl(client: TestClient) -> None:
    response = client.post("/datasets/import-jsonl", json=make_import_payload(make_test_case()))

    assert response.status_code == 201
    assert response.json()["dataset_id"]
    assert response.json()["imported_count"] == 1
    assert response.json()["rejected_count"] == 0
    assert response.json()["errors"] == []


def test_invalid_jsonl_returns_400_without_writing_dataset(client: TestClient) -> None:
    payload = make_import_payload(make_test_case())
    payload["jsonl_content"] = '{"id": "broken"'

    response = client.post("/datasets/import-jsonl", json=payload)

    assert response.status_code == 400
    assert response.json()["dataset_id"] is None
    assert response.json()["imported_count"] == 0
    assert response.json()["rejected_count"] == 1
    assert response.json()["errors"][0]["line_number"] == 1
    assert client.get("/datasets").json() == []


def test_imported_dataset_appears_in_list_and_detail(client: TestClient) -> None:
    import_response = client.post(
        "/datasets/import-jsonl",
        json=make_import_payload(make_test_case()),
    )
    dataset_id = import_response.json()["dataset_id"]

    list_response = client.get("/datasets")
    detail_response = client.get(f"/datasets/{dataset_id}")

    assert list_response.status_code == 200
    assert list_response.json() == [
        {
            "id": dataset_id,
            "name": "Support Classification Smoke",
            "workflow_type": "support_classification",
            "source_filename": "support_classification.jsonl",
            "created_at": list_response.json()[0]["created_at"],
            "test_case_count": 1,
        }
    ]
    assert detail_response.status_code == 200
    assert detail_response.json()["description"] == "Seed support ticket classification cases"
    assert detail_response.json()["test_case_count"] == 1


def test_imported_test_cases_appear_for_dataset(client: TestClient) -> None:
    import_response = client.post(
        "/datasets/import-jsonl",
        json=make_import_payload(make_test_case()),
    )
    dataset_id = import_response.json()["dataset_id"]

    response = client.get(f"/datasets/{dataset_id}/test-cases")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["dataset_id"] == dataset_id
    assert response.json()[0]["external_id"] == "support_001"
    assert response.json()[0]["input"] == {"ticket": "I was charged twice."}
    assert response.json()[0]["expected_output"] == {"category": "billing"}
    assert response.json()[0]["metadata"] == {"source": "seed"}


def test_duplicate_test_case_id_fails_before_database_write(client: TestClient) -> None:
    payload = make_import_payload(
        make_test_case(),
        make_test_case(input={"ticket": "Different ticket"}),
    )

    response = client.post("/datasets/import-jsonl", json=payload)

    assert response.status_code == 400
    assert response.json()["dataset_id"] is None
    assert response.json()["imported_count"] == 0
    assert response.json()["rejected_count"] == 1
    assert response.json()["errors"] == [
        {
            "line_number": 2,
            "message": "Duplicate id 'support_001'; first seen on line 1",
        }
    ]
    assert client.get("/datasets").json() == []


def test_empty_jsonl_fails_before_database_write(client: TestClient) -> None:
    payload = make_import_payload()
    payload["jsonl_content"] = "\n  \n"

    response = client.post("/datasets/import-jsonl", json=payload)

    assert response.status_code == 400
    assert response.json()["errors"] == [
        {"line_number": 1, "message": "JSONL content contains no test cases"}
    ]
    assert client.get("/datasets").json() == []


def test_mixed_workflow_import_fails_before_database_write(client: TestClient) -> None:
    payload = make_import_payload(make_test_case(workflow_type="incident_triage"))

    response = client.post("/datasets/import-jsonl", json=payload)

    assert response.status_code == 400
    assert response.json()["errors"] == [
        {
            "line_number": 1,
            "message": ("workflow_type must be 'support_classification', got 'incident_triage'"),
        }
    ]
    assert client.get("/datasets").json() == []


@pytest.mark.parametrize("path", ["/datasets/not-a-uuid", "/datasets/not-a-uuid/test-cases"])
def test_invalid_dataset_id_returns_validation_error(client: TestClient, path: str) -> None:
    response = client.get(path)

    assert response.status_code == 422


def test_blank_dataset_name_is_rejected(client: TestClient) -> None:
    payload = make_import_payload(make_test_case())
    payload["name"] = "   "

    response = client.post("/datasets/import-jsonl", json=payload)

    assert response.status_code == 422
    assert client.get("/datasets").json() == []
