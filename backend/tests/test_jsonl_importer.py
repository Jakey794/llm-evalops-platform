import json

from app.services.jsonl_importer import Difficulty, parse_jsonl_test_cases


def make_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "id": "support_001",
        "workflow_type": "support_classification",
        "input": {"ticket": "I was charged twice."},
        "expected_output": {"category": "billing"},
        "required_citations": [],
        "tags": ["billing"],
        "difficulty": "easy",
        "metadata": {"source": "seed"},
    }
    row.update(overrides)
    return row


def test_valid_row_passes() -> None:
    result = parse_jsonl_test_cases(json.dumps(make_row()))

    assert result.imported_count == 1
    assert result.rejected_count == 0
    assert result.errors == []
    assert result.valid_cases[0].external_id == "support_001"
    assert result.valid_cases[0].difficulty is Difficulty.EASY


def test_nested_grader_config_is_preserved_in_metadata() -> None:
    grader_config = {
        "exact_match": {"exact_fields": ["category"]},
        "composite": {
            "graders": [{"name": "exact_match", "weight": 1.0}],
            "pass_threshold": 1.0,
        },
    }
    result = parse_jsonl_test_cases(
        json.dumps(make_row(metadata={"source": "seed", "grader_config": grader_config}))
    )

    assert result.imported_count == 1
    assert result.valid_cases[0].metadata["grader_config"] == grader_config


def test_missing_input_fails() -> None:
    row = make_row()
    del row["input"]

    result = parse_jsonl_test_cases(json.dumps(row))

    assert result.imported_count == 0
    assert result.rejected_count == 1
    assert result.errors[0].line_number == 1
    assert "input: Field required" in result.errors[0].message


def test_invalid_difficulty_fails() -> None:
    result = parse_jsonl_test_cases(json.dumps(make_row(difficulty="extreme")))

    assert result.imported_count == 0
    assert result.rejected_count == 1
    assert result.errors[0].line_number == 1
    assert "difficulty" in result.errors[0].message
    assert "easy" in result.errors[0].message


def test_malformed_jsonl_line_fails() -> None:
    raw_jsonl = f'{json.dumps(make_row())}\n{{"id": "broken"'

    result = parse_jsonl_test_cases(raw_jsonl)

    assert result.imported_count == 1
    assert result.rejected_count == 1
    assert result.errors[0].line_number == 2
    assert result.errors[0].message.startswith("Invalid JSON:")


def test_duplicate_external_id_fails_within_same_file() -> None:
    raw_jsonl = "\n".join(
        [
            json.dumps(make_row()),
            json.dumps(make_row(input={"ticket": "A different ticket"})),
        ]
    )

    result = parse_jsonl_test_cases(raw_jsonl)

    assert result.imported_count == 1
    assert result.rejected_count == 1
    assert result.errors[0].line_number == 2
    assert result.errors[0].message == "Duplicate id 'support_001'; first seen on line 1"


def test_blank_lines_are_ignored() -> None:
    raw_jsonl = f"\n  \n{json.dumps(make_row())}\n\t\n"

    result = parse_jsonl_test_cases(raw_jsonl)

    assert result.imported_count == 1
    assert result.rejected_count == 0
    assert result.valid_cases[0].external_id == "support_001"


def test_collection_defaults_are_independent() -> None:
    row_one = make_row(id="support_001")
    row_two = make_row(id="support_002")
    for row in (row_one, row_two):
        row.pop("required_citations")
        row.pop("tags")
        row.pop("metadata")

    result = parse_jsonl_test_cases(f"{json.dumps(row_one)}\n{json.dumps(row_two)}")

    assert result.imported_count == 2
    assert result.rejected_count == 0
    assert result.valid_cases[0].required_citations == []
    assert result.valid_cases[0].tags == []
    assert result.valid_cases[0].metadata == {}
    assert result.valid_cases[0].tags is not result.valid_cases[1].tags
    assert result.valid_cases[0].metadata is not result.valid_cases[1].metadata


def test_empty_jsonl_fails() -> None:
    result = parse_jsonl_test_cases("\n  \n\t")

    assert result.imported_count == 0
    assert result.rejected_count == 1
    assert result.errors[0].line_number == 1
    assert result.errors[0].message == "JSONL content contains no test cases"


def test_non_string_citation_fails() -> None:
    result = parse_jsonl_test_cases(json.dumps(make_row(required_citations=[{"page": 2}])))

    assert result.imported_count == 0
    assert result.rejected_count == 1
    assert "required_citations.0" in result.errors[0].message


def test_database_bound_string_lengths_are_validated() -> None:
    result = parse_jsonl_test_cases(json.dumps(make_row(id="x" * 256)))

    assert result.imported_count == 0
    assert result.rejected_count == 1
    assert "id" in result.errors[0].message
    assert "255 characters" in result.errors[0].message


def test_expected_workflow_type_is_enforced() -> None:
    result = parse_jsonl_test_cases(
        json.dumps(make_row(workflow_type="incident_triage")),
        expected_workflow_type="support_classification",
    )

    assert result.imported_count == 0
    assert result.rejected_count == 1
    assert result.errors[0].message == (
        "workflow_type must be 'support_classification', got 'incident_triage'"
    )
