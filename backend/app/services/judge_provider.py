from __future__ import annotations

from copy import deepcopy
from time import perf_counter
from typing import Any

from google import genai
from google.genai import types
from httpx import TimeoutException
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.config import get_settings
from app.graders.judge_prompts import build_llm_judge_prompt
from app.schemas.llm_judge import LLMJudgeOutput


class JudgeUsage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)


class JudgeProviderResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    judge_output: LLMJudgeOutput | None
    usage: JudgeUsage | None
    latency_ms: int = Field(ge=0)
    model_name: str = Field(min_length=1)
    raw_output: dict[str, Any] | None
    error: str | None


def judge_output(
    workflow_type: str,
    input_json: dict[str, Any],
    expected_output_json: dict[str, Any],
    model_output: Any,
    deterministic_summary: dict[str, Any] | str | None = None,
    *,
    client: Any | None = None,
    provider: str | None = None,
    api_key: str | None = None,
    model_name: str | None = None,
    timeout_seconds: float | None = None,
) -> JudgeProviderResult:
    """Route a judge request through the configured provider without raising provider errors."""
    settings = get_settings()
    resolved_provider = (provider or settings.llm_judge_provider).strip().lower()
    if resolved_provider != "gemini":
        started_at = perf_counter()
        resolved_model = model_name or settings.llm_judge_model
        return _error_result(
            model_name=resolved_model,
            started_at=started_at,
            error=f"Unsupported LLM judge provider: {resolved_provider}",
        )

    return judge_output_with_gemini(
        workflow_type,
        input_json,
        expected_output_json,
        model_output,
        deterministic_summary,
        client=client,
        api_key=api_key,
        model_name=model_name,
        timeout_seconds=timeout_seconds,
    )


def judge_output_with_gemini(
    workflow_type: str,
    input_json: dict[str, Any],
    expected_output_json: dict[str, Any],
    model_output: Any,
    deterministic_summary: dict[str, Any] | str | None = None,
    *,
    client: Any | None = None,
    api_key: str | None = None,
    model_name: str | None = None,
    timeout_seconds: float | None = None,
) -> JudgeProviderResult:
    """Judge one output with Gemini and return failures as data rather than exceptions."""
    started_at = perf_counter()
    settings = get_settings()
    resolved_model = model_name or settings.llm_judge_model
    resolved_api_key = settings.gemini_api_key if api_key is None else api_key
    resolved_timeout = (
        settings.llm_judge_timeout_seconds if timeout_seconds is None else timeout_seconds
    )

    if client is None and not resolved_api_key:
        return _error_result(
            model_name=resolved_model,
            started_at=started_at,
            error="GEMINI_API_KEY is not configured",
        )

    prompt = build_llm_judge_prompt(
        workflow_type,
        input_json,
        expected_output_json,
        model_output,
        deterministic_summary,
    )
    request_config = types.GenerateContentConfig(
        response_mime_type="application/json",
        # Gemini does not accept JSON Schema's ``additionalProperties`` for
        # arbitrary dictionaries. Keep the public Pydantic schema unchanged,
        # then validate the parsed response locally below.
        response_schema=_gemini_response_schema(),
        http_options=types.HttpOptions(timeout=round(resolved_timeout * 1000)),
    )

    try:
        gemini_client = client or genai.Client(api_key=resolved_api_key)
        response = gemini_client.models.generate_content(
            model=resolved_model,
            contents=prompt,
            config=request_config,
        )
    except (TimeoutError, TimeoutException):
        return _error_result(
            model_name=resolved_model,
            started_at=started_at,
            error="Gemini judge request timed out",
        )
    except Exception as exc:
        # The judge is optional evaluation evidence; provider failures must not abort an eval run.
        return _error_result(
            model_name=resolved_model,
            started_at=started_at,
            error=f"Gemini judge provider error: {exc}",
        )

    raw_output = _raw_response(response)
    usage = _usage_metadata(getattr(response, "usage_metadata", None))
    blocked_reason = _blocked_reason(response)
    if blocked_reason is not None:
        return _error_result(
            model_name=resolved_model,
            started_at=started_at,
            error=f"Gemini judge response was blocked: {blocked_reason}",
            usage=usage,
            raw_output=raw_output,
        )

    parsed = getattr(response, "parsed", None)
    if parsed is None:
        return _error_result(
            model_name=resolved_model,
            started_at=started_at,
            error="Gemini judge response did not contain parsed structured output",
            usage=usage,
            raw_output=raw_output,
        )

    try:
        judge_result = LLMJudgeOutput.model_validate(parsed)
    except ValidationError as exc:
        return _error_result(
            model_name=resolved_model,
            started_at=started_at,
            error=f"Gemini judge returned invalid structured output: {exc}",
            usage=usage,
            raw_output=raw_output,
        )

    return JudgeProviderResult(
        judge_output=judge_result,
        usage=usage,
        latency_ms=_elapsed_milliseconds(started_at),
        model_name=resolved_model,
        raw_output=raw_output,
        error=None,
    )


def _blocked_reason(response: Any) -> str | None:
    prompt_feedback = getattr(response, "prompt_feedback", None)
    block_reason = getattr(prompt_feedback, "block_reason", None)
    if block_reason is not None:
        return _enum_value(block_reason)

    blocked_finish_reasons = {
        "BLOCKLIST",
        "IMAGE_SAFETY",
        "PROHIBITED_CONTENT",
        "RECITATION",
        "SAFETY",
        "SPII",
    }
    for candidate in getattr(response, "candidates", None) or ():
        finish_reason = getattr(candidate, "finish_reason", None)
        if finish_reason is not None and _enum_value(finish_reason) in blocked_finish_reasons:
            return _enum_value(finish_reason)
    return None


def _gemini_response_schema() -> dict[str, Any]:
    """Return the judge schema with Gemini-incompatible map constraints removed."""
    schema = deepcopy(LLMJudgeOutput.model_json_schema())
    _remove_map_constraints(schema)
    return schema


def _remove_map_constraints(value: Any) -> None:
    if isinstance(value, dict):
        if "additionalProperties" in value:
            value.pop("additionalProperties")
        for child in value.values():
            _remove_map_constraints(child)
    elif isinstance(value, list):
        for child in value:
            _remove_map_constraints(child)


def _enum_value(value: Any) -> str:
    return str(getattr(value, "value", value))


def _usage_metadata(usage: Any) -> JudgeUsage | None:
    if usage is None:
        return None
    return JudgeUsage(
        input_tokens=getattr(usage, "prompt_token_count", None),
        output_tokens=getattr(usage, "candidates_token_count", None),
        total_tokens=getattr(usage, "total_token_count", None),
    )


def _raw_response(response: Any) -> dict[str, Any] | None:
    model_dump = getattr(response, "model_dump", None)
    if not callable(model_dump):
        return None
    raw = model_dump(mode="json")
    return raw if isinstance(raw, dict) else None


def _elapsed_milliseconds(started_at: float) -> int:
    return max(0, round((perf_counter() - started_at) * 1000))


def _error_result(
    *,
    model_name: str,
    started_at: float,
    error: str,
    usage: JudgeUsage | None = None,
    raw_output: dict[str, Any] | None = None,
) -> JudgeProviderResult:
    return JudgeProviderResult(
        judge_output=None,
        usage=usage,
        latency_ms=_elapsed_milliseconds(started_at),
        model_name=model_name,
        raw_output=raw_output,
        error=error,
    )
