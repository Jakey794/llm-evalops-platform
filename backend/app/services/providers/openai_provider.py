from __future__ import annotations

import json
from time import perf_counter
from typing import Any

from openai import OpenAI, OpenAIError

from app.config import get_settings
from app.services.providers.base import LLMRequest, LLMResponse


class _ProviderConfigurationError(ValueError):
    pass


class _ProviderRequestError(ValueError):
    pass


class OpenAIProvider:
    def __init__(
        self,
        client: Any | None = None,
        *,
        api_key: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        settings = get_settings()
        self._client = client
        self._api_key = settings.openai_api_key if api_key is None else api_key
        self._timeout_seconds = (
            settings.openai_timeout_seconds if timeout_seconds is None else timeout_seconds
        )

    def generate(self, request: LLMRequest) -> LLMResponse:
        started_at = perf_counter()

        try:
            client = self._get_client()
            request_params = self._build_request_params(request)
            response = client.responses.create(**request_params)
            latency_ms = _elapsed_milliseconds(started_at)
        except (OpenAIError, _ProviderConfigurationError, _ProviderRequestError) as exc:
            return _error_response(
                request=request,
                latency_ms=_elapsed_milliseconds(started_at),
                error=str(exc),
            )

        text = response.output_text
        raw_response = response.model_dump(mode="json")
        usage = response.usage
        parsed_json: dict[str, Any] | list[Any] | None = None
        error: str | None = None

        if request.response_format is not None:
            parsed_json, error = _parse_structured_output(text)

        return LLMResponse(
            text=text,
            parsed_json=parsed_json,
            latency_ms=latency_ms,
            input_tokens=getattr(usage, "input_tokens", None),
            output_tokens=getattr(usage, "output_tokens", None),
            model_name=str(response.model or request.model_name),
            raw_response=raw_response,
            error=error,
        )

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        if not self._api_key:
            raise _ProviderConfigurationError("OPENAI_API_KEY is not configured")

        self._client = OpenAI(
            api_key=self._api_key,
            timeout=self._timeout_seconds,
            max_retries=0,
        )
        return self._client

    @staticmethod
    def _build_request_params(request: LLMRequest) -> dict[str, Any]:
        params: dict[str, Any] = {
            "model": request.model_name,
            "input": request.prompt,
        }
        if request.temperature is not None:
            params["temperature"] = request.temperature
        if request.max_output_tokens is not None:
            params["max_output_tokens"] = request.max_output_tokens
        if request.response_format is not None:
            params["text"] = {"format": request.response_format}
        if request.metadata is not None:
            params["metadata"] = _normalize_metadata(request.metadata)
        return params


def _normalize_metadata(metadata: dict[str, Any]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in metadata.items():
        if isinstance(value, str):
            normalized[key] = value
            continue
        try:
            normalized[key] = json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        except (TypeError, ValueError) as exc:
            raise _ProviderRequestError(
                f"OpenAI metadata value is not JSON serializable: {key}"
            ) from exc
    return normalized


def _parse_structured_output(
    text: str | None,
) -> tuple[dict[str, Any] | list[Any] | None, str | None]:
    if not text:
        return None, "Structured response did not contain text"

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, f"Structured response was not valid JSON: {exc.msg}"

    if not isinstance(parsed, (dict, list)):
        return None, "Structured response must be a JSON object or array"
    return parsed, None


def _elapsed_milliseconds(started_at: float) -> int:
    return max(0, round((perf_counter() - started_at) * 1000))


def _error_response(request: LLMRequest, latency_ms: int, error: str) -> LLMResponse:
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
