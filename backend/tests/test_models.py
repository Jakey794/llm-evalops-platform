from sqlalchemy import JSON, Uuid

from app.models import Dataset
from app.models import TestCase as CaseModel


def test_dataset_table_metadata() -> None:
    table = Dataset.__table__

    assert isinstance(table.c.id.type, Uuid)
    assert table.c.id.primary_key
    assert table.c.description.nullable
    assert table.c.source_filename.nullable
    assert not table.c.name.nullable
    assert not table.c.workflow_type.nullable
    assert not table.c.created_at.nullable
    assert any(index.columns.keys() == ["workflow_type"] for index in table.indexes)


def test_test_case_table_constraints_and_indexes() -> None:
    table = CaseModel.__table__
    foreign_key = next(iter(table.c.dataset_id.foreign_keys))
    unique_constraint = next(
        constraint
        for constraint in table.constraints
        if constraint.name == "uq_test_cases_dataset_id_external_id"
    )
    indexed_columns = {tuple(index.columns.keys()) for index in table.indexes}

    assert isinstance(table.c.id.type, Uuid)
    assert foreign_key.target_fullname == "datasets.id"
    assert foreign_key.ondelete == "CASCADE"
    assert tuple(unique_constraint.columns.keys()) == ("dataset_id", "external_id")
    assert {("dataset_id",), ("workflow_type",), ("difficulty",)} <= indexed_columns
    assert all(
        isinstance(table.c[column_name].type, JSON)
        for column_name in (
            "input_json",
            "expected_output_json",
            "required_citations",
            "tags",
            "metadata_json",
        )
    )
    assert all(not column.nullable for column in table.columns)


def test_dataset_test_case_relationship_cascades_deletes() -> None:
    dataset_relationship = Dataset.__mapper__.relationships["test_cases"]
    test_case_relationship = CaseModel.__mapper__.relationships["dataset"]

    assert dataset_relationship.back_populates == "dataset"
    assert dataset_relationship.passive_deletes
    assert dataset_relationship.cascade.delete
    assert dataset_relationship.cascade.delete_orphan
    assert test_case_relationship.back_populates == "test_cases"
