from sqlalchemy.dialects import postgresql, sqlite

from app.models import Base, EvalResult, GraderResult


def test_grader_result_model_is_exported_and_registered() -> None:
    assert GraderResult.__table__ is Base.metadata.tables["grader_results"]


def test_grader_result_columns_and_foreign_key() -> None:
    table = GraderResult.__table__
    foreign_key = next(iter(table.c.eval_result_id.foreign_keys))
    indexed_columns = {tuple(index.columns.keys()) for index in table.indexes}

    assert foreign_key.target_fullname == "eval_results.id"
    assert foreign_key.ondelete == "CASCADE"
    assert ("eval_result_id",) in indexed_columns
    assert table.c.grader_name.type.length == 255
    assert table.c.grader_type.type.length == 100
    assert table.c.score.nullable
    assert table.c.passed.nullable
    assert table.c.feedback.nullable
    assert table.c.raw_output.nullable
    assert table.c.error.nullable
    assert not table.c.failure_modes.nullable
    assert not table.c.rubric_scores.nullable
    assert not table.c.created_at.nullable
    assert table.c.created_at.type.timezone


def test_grader_result_json_columns_are_portable() -> None:
    table = GraderResult.__table__

    for column_name in ("failure_modes", "rubric_scores", "raw_output"):
        column_type = table.c[column_name].type
        assert column_type.compile(dialect=postgresql.dialect()) == "JSONB"
        assert column_type.compile(dialect=sqlite.dialect()) == "JSON"


def test_eval_result_grader_relationship_cascades_deletes() -> None:
    result_graders = EvalResult.__mapper__.relationships["grader_results"]
    grader_result = GraderResult.__mapper__.relationships["eval_result"]

    assert result_graders.back_populates == "eval_result"
    assert result_graders.passive_deletes
    assert result_graders.cascade.delete
    assert result_graders.cascade.delete_orphan
    assert grader_result.back_populates == "grader_results"
