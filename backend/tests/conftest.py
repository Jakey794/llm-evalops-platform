from collections.abc import Generator

import pytest

from app.config import get_settings
from app.security import rate_limiter

VIEWER_TOKEN = "test-viewer-token-00000000000000000001"
OPERATOR_TOKEN = "test-operator-token-000000000000000001"
OPERATOR_HEADERS = {"Authorization": f"Bearer {OPERATOR_TOKEN}"}
VIEWER_HEADERS = {"Authorization": f"Bearer {VIEWER_TOKEN}"}


@pytest.fixture(autouse=True)
def configure_security(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("BACKEND_VIEWER_TOKEN", VIEWER_TOKEN)
    monkeypatch.setenv("BACKEND_OPERATOR_TOKEN", OPERATOR_TOKEN)
    monkeypatch.setenv("RATE_LIMIT_READ_REQUESTS", "1000")
    monkeypatch.setenv("RATE_LIMIT_WRITE_REQUESTS", "1000")
    get_settings.cache_clear()
    rate_limiter.clear()
    yield
    get_settings.cache_clear()
    rate_limiter.clear()
