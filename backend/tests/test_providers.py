from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

import app.services.providers.openai_provider as openai_provider_module
from app.services.providers import LLMProvider, LLMRequest, LLMResponse, OpenAIProvider


class FakeResponse:
    def __init__(
        self,
        *,
        output_text: str | None,
        model: str = "gpt-4o-mini-2024-07-18",
        input_tokens: int | None = 12,
        output_tokens: int | None = 4,
    ) -> None:
        self.output_text = output_text
        self.model = model
        self.usage = SimpleNamespace(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    def model_dump(self, *, mode: str) -> dict[str, Any]:
        assert mode == "json"
        return {
            "id": "resp_123",
            "model": self.model,
            "output_text": self.output_text,
        }


def make_client(*, response: FakeResponse | None = None, error: Exception | None = None) -> Any:
    responses = Mock()
    if error is not None:
        responses.create.side_effect = error
    else:
        responses.create.return_value = response
    return SimpleNamespace(responses=responses)


def make_request(**overrides: Any) -> LLMRequest:
    values: dict[str, Any] = {
        "prompt": "Classify this ticket.",
        "model_name": "gpt-4o-mini",
        "temperature": None,
        "max_output_tokens": None,
        "response_format": None,
        "metadata": None,
    }
    values.update(overrides)
    return LLMRequest(**values)


def set_elapsed_time(monkeypatch: pytest.MonkeyPatch, milliseconds: float) -> None:
    values = iter([10.0, 10.0 + milliseconds / 1000])
    monkeypatch.setattr(openai_provider_module, "perf_counter", lambda: next(values))


def test_provider_models_validate_and_protocol_is_runtime_checkable() -> None:
    provider = OpenAIProvider(client=make_client(response=FakeResponse(output_text="ok")))

    assert isinstance(provider, LLMProvider)
    with pytest.raises(ValidationError):
        make_request(prompt="   ")
    with pytest.raises(ValidationError):
        make_request(temperature=2.1)
    with pytest.raises(ValidationError):
        make_request(max_output_tokens=0)
    with pytest.raises(ValidationError):
        LLMResponse(
            text=None,
            parsed_json=None,
            latency_ms=-1,
            input_tokens=None,
            output_tokens=None,
            model_name="gpt-4o-mini",
            raw_response=None,
            error=None,
        )


def test_openai_provider_returns_normalized_plain_text_response(monkeypatch) -> None:
    client = make_client(response=FakeResponse(output_text="billing"))
    set_elapsed_time(monkeypatch, 125.4)

    result = OpenAIProvider(client=client).generate(make_request())

    assert result == LLMResponse(
        text="billing",
        parsed_json=None,
        latency_ms=125,
        input_tokens=12,
        output_tokens=4,
        model_name="gpt-4o-mini-2024-07-18",
        raw_response={
            "id": "resp_123",
            "model": "gpt-4o-mini-2024-07-18",
            "output_text": "billing",
        },
        error=None,
    )
    client.responses.create.assert_called_once_with(
        model="gpt-4o-mini",
        input="Classify this ticket.",
    )


@pytest.mark.parametrize(
    ("output_text", "expected"),
    [
        ('{"category":"billing"}', {"category": "billing"}),
        ('[{"category":"billing"}]', [{"category": "billing"}]),
    ],
)
def test_openai_provider_parses_structured_object_or_array(
    monkeypatch,
    output_text: str,
    expected: dict[str, Any] | list[Any],
) -> None:
    client = make_client(response=FakeResponse(output_text=output_text))
    set_elapsed_time(monkeypatch, 10)
    response_format = {
        "type": "json_schema",
        "name": "classification",
        "schema": {"type": "object"},
        "strict": True,
    }

    result = OpenAIProvider(client=client).generate(
        make_request(
            temperature=0.2,
            max_output_tokens=256,
            response_format=response_format,
            metadata={"run_id": "run-1", "attempt": 1, "tags": ["smoke", "support"]},
        )
    )

    assert result.parsed_json == expected
    assert result.error is None
    client.responses.create.assert_called_once_with(
        model="gpt-4o-mini",
        input="Classify this ticket.",
        temperature=0.2,
        max_output_tokens=256,
        text={"format": response_format},
        metadata={
            "run_id": "run-1",
            "attempt": "1",
            "tags": '["smoke","support"]',
        },
    )


def test_openai_provider_configures_client_timeout_key_and_retries(monkeypatch) -> None:
    client = make_client(response=FakeResponse(output_text="ok"))
    client_factory = Mock(return_value=client)
    monkeypatch.setattr(openai_provider_module, "OpenAI", client_factory)
    set_elapsed_time(monkeypatch, 20)

    result = OpenAIProvider(api_key="test-key", timeout_seconds=12.5).generate(make_request())

    assert result.error is None
    client_factory.assert_called_once_with(
        api_key="test-key",
        timeout=12.5,
        max_retries=0,
    )


def test_openai_provider_uses_api_key_and_timeout_from_settings(monkeypatch) -> None:
    client = make_client(response=FakeResponse(output_text="ok"))
    client_factory = Mock(return_value=client)
    monkeypatch.setattr(openai_provider_module, "OpenAI", client_factory)
    monkeypatch.setattr(
        openai_provider_module,
        "get_settings",
        lambda: SimpleNamespace(
            openai_api_key="settings-key",
            openai_timeout_seconds=7.5,
        ),
    )
    set_elapsed_time(monkeypatch, 5)

    result = OpenAIProvider().generate(make_request())

    assert result.error is None
    client_factory.assert_called_once_with(
        api_key="settings-key",
        timeout=7.5,
        max_retries=0,
    )


def test_openai_provider_returns_missing_key_as_error(monkeypatch) -> None:
    set_elapsed_time(monkeypatch, 1)

    result = OpenAIProvider(api_key="").generate(make_request())

    assert result.error == "OPENAI_API_KEY is not configured"
    assert result.text is None
    assert result.raw_response is None
    assert result.model_name == "gpt-4o-mini"


def test_openai_provider_returns_sdk_failure_as_error(monkeypatch) -> None:
    class FakeOpenAIError(Exception):
        pass

    monkeypatch.setattr(openai_provider_module, "OpenAIError", FakeOpenAIError)
    client = make_client(error=FakeOpenAIError("provider unavailable"))
    set_elapsed_time(monkeypatch, 80)

    result = OpenAIProvider(client=client).generate(make_request())

    assert result.error == "provider unavailable"
    assert result.latency_ms == 80
    assert result.input_tokens is None
    assert result.output_tokens is None


@pytest.mark.parametrize(
    ("output_text", "expected_error"),
    [
        ("not-json", "Structured response was not valid JSON"),
        ("42", "Structured response must be a JSON object or array"),
        (None, "Structured response did not contain text"),
    ],
)
def test_openai_provider_returns_structured_parse_failures(
    monkeypatch,
    output_text: str | None,
    expected_error: str,
) -> None:
    client = make_client(response=FakeResponse(output_text=output_text))
    set_elapsed_time(monkeypatch, 15)

    result = OpenAIProvider(client=client).generate(
        make_request(response_format={"type": "json_object"})
    )

    assert result.text == output_text
    assert result.parsed_json is None
    assert result.error is not None
    assert result.error.startswith(expected_error)
    assert result.raw_response is not None
    assert result.input_tokens == 12
    assert result.output_tokens == 4


def test_openai_provider_returns_invalid_metadata_as_error(monkeypatch) -> None:
    client = make_client(response=FakeResponse(output_text="ok"))
    set_elapsed_time(monkeypatch, 2)

    result = OpenAIProvider(client=client).generate(make_request(metadata={"invalid": object()}))

    assert result.error == "OpenAI metadata value is not JSON serializable: invalid"
    client.responses.create.assert_not_called()
