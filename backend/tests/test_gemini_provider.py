from types import SimpleNamespace
from unittest.mock import Mock

from app.services.providers import GeminiProvider, LLMRequest


def test_gemini_provider_returns_structured_json_without_api_key_when_client_injected() -> None:
    response = SimpleNamespace(
        text='{"answer":"ok","citations":["doc-1"]}',
        usage_metadata=SimpleNamespace(prompt_token_count=11, candidates_token_count=4),
        model_dump=lambda mode="json": {"text": '{"answer":"ok"}'},
    )
    client = SimpleNamespace(models=SimpleNamespace(generate_content=Mock(return_value=response)))
    provider = GeminiProvider(client=client, api_key=None)

    result = provider.generate(
        LLMRequest(
            prompt="Answer using documents.",
            model_name="gemini-3.1-flash-lite",
            temperature=0,
            max_output_tokens=128,
            response_format={"type": "json_object"},
        )
    )

    assert result.error is None
    assert result.parsed_json == {"answer": "ok", "citations": ["doc-1"]}
    assert result.input_tokens == 11
    assert result.output_tokens == 4


def test_gemini_provider_reports_missing_api_key() -> None:
    provider = GeminiProvider(api_key="")
    result = provider.generate(LLMRequest(prompt="Hello", model_name="gemini-3.1-flash-lite"))
    assert result.text is None
    assert result.error == "GEMINI_API_KEY is not configured"
