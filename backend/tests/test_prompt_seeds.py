from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.seed.load_seed_data as seed_loader
from app.models import Base, PromptVersion
from app.services.prompt_renderer import render_prompt


def test_seed_prompt_templates_render_existing_workflow_inputs() -> None:
    definitions = {
        definition.workflow_type: definition for definition in seed_loader.PROMPT_SEED_DEFINITIONS
    }

    incident_prompt = render_prompt(
        definitions["incident_triage"].template,
        {
            "title": "Checkout unavailable",
            "symptoms": ["100% of checkout requests return 503"],
            "started_at": "2026-05-04T14:02:00Z",
        },
    )
    support_prompt = render_prompt(
        definitions["support_classification"].template,
        {"ticket": "I was charged twice."},
    )

    assert "Checkout unavailable" in incident_prompt
    assert '["100% of checkout requests return 503"]' in incident_prompt
    assert "2026-05-04T14:02:00Z" in incident_prompt
    assert "I was charged twice." in support_prompt
    assert "summary" in incident_prompt
    assert "priority" in support_prompt
    assert "routed_team" in support_prompt
    assert "{{" not in incident_prompt
    assert "{{" not in support_prompt


def test_prompt_seed_loader_imports_two_versions_once(monkeypatch) -> None:
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

    assert [
        (summary.prompt_name, summary.version_label, summary.status) for summary in first_run
    ] == [
        ("incident_triage_baseline", "v1", "imported"),
        ("support_classification_baseline", "v1", "imported"),
    ]
    assert [summary.status for summary in second_run] == ["skipped", "skipped"]

    with session_factory() as db:
        assert db.scalar(select(func.count(PromptVersion.id))) == 2
        prompts = list(db.scalars(select(PromptVersion).order_by(PromptVersion.name)))

    assert [(prompt.name, prompt.workflow_type, prompt.version_label) for prompt in prompts] == [
        ("incident_triage_baseline", "incident_triage", "v1"),
        ("support_classification_baseline", "support_classification", "v1"),
    ]

    engine.dispose()
