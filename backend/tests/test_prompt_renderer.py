import pytest

from app.services.prompt_renderer import (
    MissingPromptVariableError,
    PromptRenderError,
    render_prompt,
)


def test_render_prompt_renders_flat_variables() -> None:
    rendered = render_prompt(
        "Ticket: {{ ticket }}",
        {"ticket": "I was charged twice."},
    )

    assert rendered == "Ticket: I was charged twice."


def test_render_prompt_renders_nested_variables() -> None:
    rendered = render_prompt(
        "Customer tier: {{ customer.tier }}",
        {"customer": {"tier": "enterprise"}},
    )

    assert rendered == "Customer tier: enterprise"


def test_render_prompt_fails_cleanly_on_missing_variable() -> None:
    with pytest.raises(MissingPromptVariableError) as exc_info:
        render_prompt(
            "Customer tier: {{ customer.tier }}",
            {"customer": {}},
        )

    assert exc_info.value.variable_path == "customer.tier"
    assert str(exc_info.value) == "Missing required prompt variable: customer.tier"


def test_render_prompt_ignores_unrelated_fields() -> None:
    rendered = render_prompt(
        "Ticket: {{ ticket }}",
        {
            "ticket": "Reset my password.",
            "internal_note": "Do not expose this value.",
            "customer": {"tier": "enterprise"},
        },
    )

    assert rendered == "Ticket: Reset my password."
    assert "internal_note" not in rendered
    assert "enterprise" not in rendered


def test_render_prompt_serializes_non_string_values_predictably() -> None:
    rendered = render_prompt(
        (
            "count={{ count }} active={{ active }} missing={{ missing }} "
            "tags={{ tags }} metadata={{ metadata }} ratio={{ ratio }}"
        ),
        {
            "count": 3,
            "active": True,
            "missing": None,
            "tags": ["urgent", "billing"],
            "metadata": {"z": 2, "a": "é"},
            "ratio": 1.5,
        },
    )

    assert rendered == (
        'count=3 active=true missing=null tags=["urgent","billing"] '
        'metadata={"a":"é","z":2} ratio=1.5'
    )


@pytest.mark.parametrize(
    "template",
    [
        "{{ customer[0] }}",
        "{{ customer | upper }}",
        "{{ customer.name",
    ],
)
def test_render_prompt_rejects_malformed_or_unsafe_expressions(template: str) -> None:
    with pytest.raises(PromptRenderError):
        render_prompt(template, {"customer": {"name": "Ada"}})


@pytest.mark.parametrize("value", [object(), float("nan")])
def test_render_prompt_rejects_non_json_values(value: object) -> None:
    with pytest.raises(PromptRenderError, match="not JSON serializable"):
        render_prompt("Value: {{ value }}", {"value": value})
