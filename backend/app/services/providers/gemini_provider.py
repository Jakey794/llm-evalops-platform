from __future__ import annotations

import json
from time import perf_counter
from typing import Any

from google import genai
from google.genai import types
from httpx import TimeoutException

from app.config import get_settings
from app.services.providers.base import LLMRequest, LLMResponse


class _ProviderConfigurationError(ValueError):
    pass


class GeminiProvider:
    """Optional Gemini generation provider isolated behind the shared LLMProvider protocol."""

    def __init__(
        self,
        client: Any | None = None,
        *,
        api_key: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        settings = get_settings()
        self._client = client
        self._api_key = settings.gemini_api_key if api_key is None else api_key
        self._timeout_seconds = (
            settings.llm_judge_timeout_seconds if timeout_seconds is None else timeout_seconds
        )

    def generate(self, request: LLMRequest) -> LLMResponse:
        started_at = perf_counter()
        try:
            client = self._get_client()
            config_kwargs: dict[str, Any] = {
                "http_options": types.HttpOptions(timeout=round(self._timeout_seconds * 1000)),
            }
            if request.temperature is not None:
                config_kwargs["temperature"] = request.temperature
            if request.max_output_tokens is not None:
                config_kwargs["max_output_tokens"] = request.max_output_tokens
            if request.response_format is not None:
                config_kwargs["response_mime_type"] = "application/json"

            response = client.models.generate_content(
                model=request.model_name,
                contents=request.prompt,
                config=types.GenerateContentConfig(**config_kwargs),
            )
            latency_ms = _elapsed_milliseconds(started_at)
        except (TimeoutError, TimeoutException) as exc:
            return _error_response(
                request=request,
                latency_ms=_elapsed_milliseconds(started_at),
                error=f"Gemini request timed out: {exc}",
            )
        except (_ProviderConfigurationError, Exception) as exc:
            return _error_response(
                request=request,
                latency_ms=_elapsed_milliseconds(started_at),
                error=str(exc),
            )

        text = getattr(response, "text", None)
        usage = getattr(response, "usage_metadata", None)
        parsed_json: dict[str, Any] | list[Any] | None = None
        error: str | None = None
        if request.response_format is not None:
            parsed_json, error = _parse_structured_output(text)

        return LLMResponse(
            text=text,
            parsed_json=parsed_json,
            latency_ms=latency_ms,
            input_tokens=getattr(usage, "prompt_token_count", None),
            output_tokens=getattr(usage, "candidates_token_count", None),
            model_name=request.model_name,
            raw_response=_raw_response(response),
            error=error,
        )

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        if not self._api_key:
            raise _ProviderConfigurationError("GEMINI_API_KEY is not configured")
        self._client = genai.Client(api_key=self._api_key)
        return self._client


def _parse_structured_output(
    text: str | None,
) -> tuple[dict[str, Any] | list[Any] | None, str | None]:
    if text is None or not text.strip():
        return None, "Gemini returned empty structured output"
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, f"Gemini returned invalid JSON: {exc.msg}"
    if isinstance(parsed, (dict, list)):
        return parsed, None
    return None, "Gemini structured output must be a JSON object or array"


def _raw_response(response: Any) -> dict[str, Any] | None:
    dump = getattr(response, "model_dump", None)
    if callable(dump):
        try:
            payload = dump(mode="json")
        except TypeError:
            payload = dump()
        return payload if isinstance(payload, dict) else {"value": payload}
    return {"text": getattr(response, "text", None)}


def _error_response(*, request: LLMRequest, latency_ms: int, error: str) -> LLMResponse:
    return LLMResponse(
        text=None,
        parsed_json=None,
        latency_ms=latency_ms,
        input_tokens=None,
        output_tokens=None,
        model_name=request.model_name,
        raw_response=None,
        error=error,
    )


def _elapsed_milliseconds(started_at: float) -> int:
    return max(0, round((perf_counter() - started_at) * 1000))
