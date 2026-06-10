from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check_returns_expected_payload(monkeypatch) -> None:
    monkeypatch.setattr("app.api.routes.health.check_database_connection", lambda: True)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "llm-evalops-backend",
        "version": "0.1.0",
        "database": "ok",
    }


def test_health_check_returns_degraded_payload_when_database_is_unavailable(monkeypatch) -> None:
    monkeypatch.setattr("app.api.routes.health.check_database_connection", lambda: False)

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {
        "status": "degraded",
        "service": "llm-evalops-backend",
        "version": "0.1.0",
        "database": "error",
    }
