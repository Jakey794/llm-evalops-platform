import json
import re
from collections.abc import Mapping
from typing import Any

PLACEHOLDER_PATTERN = re.compile(r"{{(?P<expression>.*?)}}", re.DOTALL)
VARIABLE_PATH_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*")


class PromptRenderError(ValueError):
    """Raised when a prompt template cannot be rendered safely."""


class MissingPromptVariableError(PromptRenderError):
    """Raised when a required prompt variable is absent from the input mapping."""

    def __init__(self, variable_path: str) -> None:
        self.variable_path = variable_path
        super().__init__(f"Missing required prompt variable: {variable_path}")


def render_prompt(template: str, variables: Mapping[str, Any]) -> str:
    """Render double-curly variable paths from a JSON-compatible mapping."""

    unmatched_template = PLACEHOLDER_PATTERN.sub("", template)
    if "{{" in unmatched_template:
        raise PromptRenderError("Malformed prompt placeholder: missing closing braces")

    def replace_placeholder(match: re.Match[str]) -> str:
        variable_path = match.group("expression").strip()
        if VARIABLE_PATH_PATTERN.fullmatch(variable_path) is None:
            raise PromptRenderError(f"Invalid prompt variable expression: {variable_path!r}")

        value = _resolve_variable(variable_path, variables)
        return _serialize_value(variable_path, value)

    return PLACEHOLDER_PATTERN.sub(replace_placeholder, template)


def _resolve_variable(variable_path: str, variables: Mapping[str, Any]) -> Any:
    value: Any = variables
    for segment in variable_path.split("."):
        if not isinstance(value, Mapping) or segment not in value:
            raise MissingPromptVariableError(variable_path)
        value = value[segment]
    return value


def _serialize_value(variable_path: str, value: Any) -> str:
    if isinstance(value, str):
        return value

    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise PromptRenderError(
            f"Prompt variable is not JSON serializable: {variable_path}"
        ) from exc
