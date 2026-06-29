import json
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class Difficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class JsonlTestCase(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    external_id: str = Field(validation_alias="id", min_length=1, max_length=255)
    workflow_type: str = Field(min_length=1, max_length=100)
    input: dict[str, Any]
    expected_output: dict[str, Any]
    required_citations: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    difficulty: Difficulty
    metadata: dict[str, Any] = Field(default_factory=dict)


class JsonlImportError(BaseModel):
    line_number: int
    message: str


class JsonlImportResult(BaseModel):
    valid_cases: list[JsonlTestCase]
    errors: list[JsonlImportError]
    imported_count: int
    rejected_count: int


def parse_jsonl_test_cases(
    raw_jsonl: str,
    *,
    expected_workflow_type: str | None = None,
) -> JsonlImportResult:
    valid_cases: list[JsonlTestCase] = []
    errors: list[JsonlImportError] = []
    seen_ids: dict[str, int] = {}
    has_content = False

    for line_number, raw_line in enumerate(raw_jsonl.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        has_content = True

        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(
                JsonlImportError(
                    line_number=line_number,
                    message=f"Invalid JSON: {exc.msg} at column {exc.colno}",
                )
            )
            continue

        try:
            test_case = JsonlTestCase.model_validate(row)
        except ValidationError as exc:
            errors.append(
                JsonlImportError(
                    line_number=line_number,
                    message=f"Validation error: {_format_validation_error(exc)}",
                )
            )
            continue

        if expected_workflow_type is not None and test_case.workflow_type != expected_workflow_type:
            errors.append(
                JsonlImportError(
                    line_number=line_number,
                    message=(
                        f"workflow_type must be '{expected_workflow_type}', "
                        f"got '{test_case.workflow_type}'"
                    ),
                )
            )
            continue

        first_line = seen_ids.get(test_case.external_id)
        if first_line is not None:
            errors.append(
                JsonlImportError(
                    line_number=line_number,
                    message=(
                        f"Duplicate id '{test_case.external_id}'; first seen on line {first_line}"
                    ),
                )
            )
            continue

        seen_ids[test_case.external_id] = line_number
        valid_cases.append(test_case)

    if not has_content:
        errors.append(
            JsonlImportError(
                line_number=1,
                message="JSONL content contains no test cases",
            )
        )

    return JsonlImportResult(
        valid_cases=valid_cases,
        errors=errors,
        imported_count=len(valid_cases),
        rejected_count=len(errors),
    )


def _format_validation_error(exc: ValidationError) -> str:
    messages: list[str] = []
    for error in exc.errors(include_input=False, include_url=False):
        location = ".".join(str(part) for part in error["loc"])
        messages.append(f"{location}: {error['msg']}" if location else error["msg"])
    return "; ".join(messages)
