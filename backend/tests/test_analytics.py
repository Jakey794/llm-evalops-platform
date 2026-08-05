from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Base, Dataset, EvalResult, EvalRun, ModelConfig, PromptVersion, TestCase
from app.services.analytics import (
    build_compare_response,
    build_dashboard_overview,
    build_run_analytics,
)


def test_build_run_analytics_groups_tags_difficulty_and_workflow() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    with session_factory() as db:
        dataset = Dataset(name="Analytics DS", workflow_type="support_classification")
        prompt = PromptVersion(
            name="support_baseline",
            workflow_type="support_classification",
            version_label="v1",
            template="Classify {{ ticket }}",
        )
        model = ModelConfig(
            provider="openai",
            model_name="gpt-4o-mini",
            temperature=0,
            max_output_tokens=128,
        )
        db.add_all([dataset, prompt, model])
        db.flush()

        run = EvalRun(
            dataset_id=dataset.id,
            prompt_version_id=prompt.id,
            model_config_id=model.id,
            status="completed",
            total_cases=2,
            completed_cases=2,
            pass_rate=0.5,
            avg_score=0.75,
            total_cost_usd=Decimal("0.02"),
            avg_latency_ms=20,
            p95_latency_ms=30,
            failed_count=1,
        )
        db.add(run)
        db.flush()

        case_a = TestCase(
            dataset_id=dataset.id,
            external_id="a",
            input_json={"ticket": "a"},
            expected_output_json={"category": "billing"},
            required_citations=[],
            tags=["billing", "payments"],
            difficulty="easy",
            workflow_type="support_classification",
            metadata_json={},
        )
        case_b = TestCase(
            dataset_id=dataset.id,
            external_id="b",
            input_json={"ticket": "b"},
            expected_output_json={"category": "bug_report"},
            required_citations=[],
            tags=["crash"],
            difficulty="hard",
            workflow_type="support_classification",
            metadata_json={},
        )
        db.add_all([case_a, case_b])
        db.flush()

        db.add_all(
            [
                EvalResult(
                    eval_run_id=run.id,
                    test_case_id=case_a.id,
                    model_output="{}",
                    score=1.0,
                    passed=True,
                    latency_ms=10,
                    estimated_cost_usd=Decimal("0.01"),
                    grader_feedback="pass",
                    failure_modes=[],
                    grader_breakdown={},
                ),
                EvalResult(
                    eval_run_id=run.id,
                    test_case_id=case_b.id,
                    model_output="{}",
                    score=0.5,
                    passed=False,
                    latency_ms=30,
                    estimated_cost_usd=Decimal("0.01"),
                    grader_feedback="fail",
                    failure_modes=["incorrect_label"],
                    grader_breakdown={},
                ),
            ]
        )
        db.commit()

        analytics = build_run_analytics(db, run.id)
        overview = build_dashboard_overview(db)
        compare = build_compare_response(db, [run.id])

    assert {bucket.key for bucket in analytics.by_tag} == {"billing", "crash", "payments"}
    assert {bucket.key: bucket.pass_rate for bucket in analytics.by_difficulty} == {
        "easy": 1.0,
        "hard": 0.0,
    }
    assert analytics.by_workflow[0].key == "support_classification"
    assert overview.completed_run_count == 1
    assert overview.pass_rate == 0.5
    assert compare.runs[0].model_name == "gpt-4o-mini"
    assert compare.cost_quality[0]["cost"] == 0.02
    assert compare.latency_quality[0]["latency"] == 30

    engine.dispose()


def test_build_run_analytics_handles_empty_results() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with session_factory() as db:
        dataset = Dataset(name="Empty", workflow_type="support_classification")
        prompt = PromptVersion(
            name="p",
            workflow_type="support_classification",
            version_label="v1",
            template="x",
        )
        model = ModelConfig(provider="openai", model_name="m", max_output_tokens=16)
        db.add_all([dataset, prompt, model])
        db.flush()
        run = EvalRun(
            dataset_id=dataset.id,
            prompt_version_id=prompt.id,
            model_config_id=model.id,
            status="completed",
        )
        db.add(run)
        db.commit()
        analytics = build_run_analytics(db, run.id)

    assert analytics.by_tag == []
    assert analytics.by_difficulty == []
    assert analytics.has_partial_metrics is False
    engine.dispose()
