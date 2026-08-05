from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.seed.load_seed_data as seed_loader
from app.models import Base, ModelConfig, PromptVersion
from app.services.prompt_renderer import render_prompt


def test_seed_prompt_templates_render_existing_workflow_inputs() -> None:
    definitions = {
        definition.name: definition for definition in seed_loader.PROMPT_SEED_DEFINITIONS
    }

    incident_prompt = render_prompt(
        definitions["incident_triage_baseline"].template,
        {
            "title": "Checkout unavailable",
            "symptoms": ["100% of checkout requests return 503"],
            "started_at": "2026-05-04T14:02:00Z",
        },
    )
    support_prompt = render_prompt(
        definitions["support_classification_baseline"].template,
        {"ticket": "I was charged twice."},
    )
    rag_prompt = render_prompt(
        definitions["rag_qa_baseline"].template,
        {
            "question": "How long is the refund window?",
            "documents": [{"id": "refund-policy", "content": "30 days"}],
        },
    )

    assert "Checkout unavailable" in incident_prompt
    assert '["100% of checkout requests return 503"]' in incident_prompt
    assert "2026-05-04T14:02:00Z" in incident_prompt
    assert "I was charged twice." in support_prompt
    assert "summary" in incident_prompt
    assert "priority" in support_prompt
    assert "routed_team" in support_prompt
    assert "refund-policy" in rag_prompt
    assert "citations" in rag_prompt
    assert "{{" not in incident_prompt
    assert "{{" not in support_prompt
    assert "{{" not in rag_prompt


def test_prompt_seed_loader_imports_baseline_and_degraded_once(monkeypatch) -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(seed_loader, "get_session_factory", lambda: session_factory)

    first_run = seed_loader.load_prompt_versions()
    second_run = seed_loader.load_prompt_versions()

    assert len(first_run) == 6
    assert all(summary.status == "imported" for summary in first_run)
    assert all(summary.status == "skipped" for summary in second_run)

    with session_factory() as db:
        assert db.scalar(select(func.count(PromptVersion.id))) == 6
        names = set(db.scalars(select(PromptVersion.name)))

    assert "rag_qa_baseline" in names
    assert "rag_qa_degraded" in names
    assert "support_classification_degraded" in names
    assert "incident_triage_degraded" in names

    engine.dispose()


def test_model_seed_loader_imports_gemini_and_openai_once(monkeypatch) -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(seed_loader, "get_session_factory", lambda: session_factory)

    first_run = seed_loader.load_model_configs()
    second_run = seed_loader.load_model_configs()

    assert [(summary.provider, summary.model_name, summary.status) for summary in first_run] == [
        ("gemini", "gemini-3.1-flash-lite", "imported"),
        ("openai", "gpt-4o-mini", "imported"),
    ]
    assert [summary.status for summary in second_run] == ["skipped", "skipped"]

    with session_factory() as db:
        assert db.scalar(select(func.count(ModelConfig.id))) == 2

    engine.dispose()
