from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

import pytest

import app.services.judge_provider as judge_provider_module
from app.config import Settings
from app.schemas import LLMJudgeOutput
from app.services.judge_provider import JudgeUsage, judge_output


class FakeResponse:
    def __init__(
        self,
        *,
        parsed: Any,
        prompt_feedback: Any | None = None,
        candidates: list[Any] | None = None,
    ) -> None:
        self.parsed = parsed
        self.prompt_feedback = prompt_feedback
        self.candidates = candidates or []
        self.usage_metadata = SimpleNamespace(
            prompt_token_count=20,
            candidates_token_count=10,
            total_token_count=30,
        )

    def model_dump(self, *, mode: str) -> dict[str, Any]:
        assert mode == "json"
        return {"response_id": "gemini-judge-123"}


def make_client(*, response: FakeResponse | None = None, error: Exception | None = None) -> Any:
    generate_content = Mock()
    if error is not None:
        generate_content.side_effect = error
    else:
        generate_content.return_value = response
    return SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))


def valid_judge_output() -> LLMJudgeOutput:
    return LLMJudgeOutput(
        score=0.9,
        passed=True,
        reason="The classification matches the expected route.",
        failure_modes=[],
        rubric_scores={
            "category_accuracy": 1.0,
            "priority_accuracy": 0.8,
            "routing_accuracy": 1.0,
            "classification_relevance": 0.8,
        },
    )


@pytest.fixture(autouse=True)
def mock_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        judge_provider_module,
        "get_settings",
        lambda: SimpleNamespace(
            llm_judge_provider="gemini",
            gemini_api_key="test-gemini-key",
            llm_judge_model="gemini-3.1-flash-lite",
            llm_judge_timeout_seconds=30.0,
        ),
    )


def judge(client: Any | None = None, **overrides: Any):
    values: dict[str, Any] = {
        "workflow_type": "support_classification",
        "input_json": {"ticket": "I cannot sign in"},
        "expected_output_json": {"category": "account_access"},
        "model_output": {"category": "account_access"},
        "client": client,
    }
    values.update(overrides)
    return judge_output(**values)


def set_elapsed_time(monkeypatch: pytest.MonkeyPatch, milliseconds: float) -> None:
    values = iter([10.0, 10.0 + milliseconds / 1000])
    monkeypatch.setattr(judge_provider_module, "perf_counter", lambda: next(values))


def test_judge_settings_default_to_gemini_and_read_gemini_key(monkeypatch) -> None:
    monkeypatch.delenv("LLM_JUDGE_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_JUDGE_MODEL", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")

    settings = Settings(_env_file=None)

    assert settings.llm_judge_provider == "gemini"
    assert settings.gemini_api_key == "test-gemini-key"
    assert settings.llm_judge_model == "gemini-3.1-flash-lite"


def test_gemini_is_default_and_returns_validated_structured_result(monkeypatch) -> None:
    response = FakeResponse(parsed=valid_judge_output())
    client = make_client(response=response)
    set_elapsed_time(monkeypatch, 125)

    result = judge(client, deterministic_summary={"score": 1.0})

    assert result.judge_output == valid_judge_output()
    assert result.usage == JudgeUsage(input_tokens=20, output_tokens=10, total_tokens=30)
    assert result.latency_ms == 125
    assert result.model_name == "gemini-3.1-flash-lite"
    assert result.raw_output == {"response_id": "gemini-judge-123"}
    assert result.error is None
    call = client.models.generate_content.call_args.kwargs
    assert call["model"] == "gemini-3.1-flash-lite"
    assert '"score": 1.0' in call["contents"]
    assert call["config"].response_mime_type == "application/json"
    response_schema = call["config"].response_schema
    assert response_schema["properties"]["score"]["$ref"] == "#/$defs/UnitInterval"
    assert "additionalProperties" not in response_schema
    assert "additionalProperties" not in response_schema["properties"]["rubric_scores"]
    assert call["config"].http_options.timeout == 30_000


def test_gemini_judge_returns_missing_api_key_as_error(monkeypatch) -> None:
    set_elapsed_time(monkeypatch, 1)

    result = judge(None, api_key="")

    assert result.judge_output is None
    assert result.error == "GEMINI_API_KEY is not configured"
    assert result.raw_output is None


def test_gemini_judge_returns_provider_exception_as_error(monkeypatch) -> None:
    client = make_client(error=RuntimeError("provider unavailable"))
    set_elapsed_time(monkeypatch, 80)

    result = judge(client)

    assert result.judge_output is None
    assert result.error == "Gemini judge provider error: provider unavailable"
    assert result.latency_ms == 80


def test_gemini_judge_returns_invalid_parsed_response_as_error(monkeypatch) -> None:
    response = FakeResponse(
        parsed={
            "score": 2.0,
            "passed": True,
            "reason": "Invalid score.",
            "failure_modes": [],
            "rubric_scores": {},
        }
    )
    set_elapsed_time(monkeypatch, 15)

    result = judge(make_client(response=response))

    assert result.judge_output is None
    assert result.error is not None
    assert result.error.startswith("Gemini judge returned invalid structured output")
    assert result.raw_output is not None


def test_gemini_judge_returns_timeout_as_error(monkeypatch) -> None:
    class FakeTimeoutError(Exception):
        pass

    monkeypatch.setattr(judge_provider_module, "TimeoutException", FakeTimeoutError)
    set_elapsed_time(monkeypatch, 30_000)

    result = judge(make_client(error=FakeTimeoutError()))

    assert result.judge_output is None
    assert result.error == "Gemini judge request timed out"
    assert result.latency_ms == 30_000


def test_gemini_judge_returns_blocked_response_as_error(monkeypatch) -> None:
    feedback = SimpleNamespace(block_reason="SAFETY")
    response = FakeResponse(parsed=None, prompt_feedback=feedback)
    set_elapsed_time(monkeypatch, 5)

    result = judge(make_client(response=response))

    assert result.judge_output is None
    assert result.error == "Gemini judge response was blocked: SAFETY"
    assert result.usage == JudgeUsage(input_tokens=20, output_tokens=10, total_tokens=30)


def test_unsupported_judge_provider_returns_error(monkeypatch) -> None:
    set_elapsed_time(monkeypatch, 1)

    result = judge(
        make_client(response=FakeResponse(parsed=valid_judge_output())),
        provider="other",
    )

    assert result.judge_output is None
    assert result.error == "Unsupported LLM judge provider: other"
