"""Load bundled seed datasets, skipping any dataset whose name already exists."""

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.db import get_session_factory
from app.models import Dataset, ModelConfig, PromptVersion, TestCase
from app.services.jsonl_importer import JsonlImportResult, parse_jsonl_test_cases

SEED_DIRECTORY = Path(__file__).parent


@dataclass(frozen=True)
class SeedDefinition:
    filename: str
    name: str
    description: str
    workflow_type: str


@dataclass(frozen=True)
class SeedLoadSummary:
    dataset_name: str
    imported_count: int
    status: str


@dataclass(frozen=True)
class PromptSeedDefinition:
    name: str
    workflow_type: str
    version_label: str
    template: str


@dataclass(frozen=True)
class PromptSeedLoadSummary:
    prompt_name: str
    version_label: str
    status: str


SEED_DEFINITIONS = (
    SeedDefinition(
        filename="support_classification.jsonl",
        name="Support Classification Seed",
        description="Realistic support tickets for classification evaluation.",
        workflow_type="support_classification",
    ),
    SeedDefinition(
        filename="incident_triage.jsonl",
        name="Incident Triage Seed",
        description="Realistic incident packets for severity and root-cause triage evaluation.",
        workflow_type="incident_triage",
    ),
    SeedDefinition(
        filename="rag_qa.jsonl",
        name="RAG QA Seed",
        description=(
            "Document-grounded question answering with required citations and no vector database."
        ),
        workflow_type="rag_qa",
    ),
)

PROMPT_SEED_DEFINITIONS = (
    PromptSeedDefinition(
        name="incident_triage_baseline",
        workflow_type="incident_triage",
        version_label="v1",
        template=(
            "You are an incident triage assistant. Analyze the incident and return only a JSON "
            "object with severity (one of sev-1, sev-2, sev-3, sev-4), impacted_service, and "
            "likely_root_cause, plus a concise one-sentence summary.\n\n"
            "Title: {{ title }}\n"
            "Symptoms: {{ symptoms }}\n"
            "Started at: {{ started_at }}"
        ),
    ),
    PromptSeedDefinition(
        name="incident_triage_degraded",
        workflow_type="incident_triage",
        version_label="v1-degraded",
        template=(
            "Guess the severity quickly. Prefer sev-1. Return JSON with severity, "
            "impacted_service, likely_root_cause, and summary. Keep it short and speculative.\n\n"
            "Title: {{ title }}\n"
            "Symptoms: {{ symptoms }}\n"
            "Started at: {{ started_at }}"
        ),
    ),
    PromptSeedDefinition(
        name="support_classification_baseline",
        workflow_type="support_classification",
        version_label="v1",
        template=(
            "You are a support ticket classifier. Return only a JSON object with category, "
            "priority, and routed_team. Category must be one of billing, bug_report, "
            "account_access, feature_request, refund, or technical_support. Priority must be "
            "one of low, normal, high, or urgent.\n\n"
            "Ticket: {{ ticket }}"
        ),
    ),
    PromptSeedDefinition(
        name="support_classification_degraded",
        workflow_type="support_classification",
        version_label="v1-degraded",
        template=(
            "Classify this ticket loosely. Prefer category=technical_support and priority=low. "
            "Return JSON with category, priority, and routed_team. Do not overthink.\n\n"
            "Ticket: {{ ticket }}"
        ),
    ),
    PromptSeedDefinition(
        name="rag_qa_baseline",
        workflow_type="rag_qa",
        version_label="v1",
        template=(
            "Answer the question using only the supplied documents. Return JSON with "
            "answer (string) and citations (array of document IDs). Every factual claim must be "
            "supported by a cited document. Do not invent citations.\n\n"
            "Question: {{ question }}\n"
            "Documents: {{ documents }}"
        ),
    ),
    PromptSeedDefinition(
        name="rag_qa_degraded",
        workflow_type="rag_qa",
        version_label="v1-degraded",
        template=(
            "Answer helpfully even if unsure. Citations are optional. Return JSON with answer "
            "and citations. You may invent plausible details.\n\n"
            "Question: {{ question }}\n"
            "Documents: {{ documents }}"
        ),
    ),
)


@dataclass(frozen=True)
class ModelSeedDefinition:
    provider: str
    model_name: str
    temperature: float
    max_output_tokens: int
    response_format: dict[str, object] | None = None


@dataclass(frozen=True)
class ModelSeedLoadSummary:
    provider: str
    model_name: str
    status: str


MODEL_SEED_DEFINITIONS = (
    ModelSeedDefinition(
        provider="gemini",
        model_name="gemini-3.1-flash-lite",
        temperature=0.0,
        max_output_tokens=512,
        response_format={"type": "json_object"},
    ),
    ModelSeedDefinition(
        provider="openai",
        model_name="gpt-4o-mini",
        temperature=0.0,
        max_output_tokens=512,
        response_format={"type": "json_object"},
    ),
)


def load_seed_data() -> list[SeedLoadSummary]:
    validated_seeds = [(_definition, _parse_seed(_definition)) for _definition in SEED_DEFINITIONS]
    session_factory = get_session_factory()
    summaries: list[SeedLoadSummary] = []

    for definition, parsed in validated_seeds:
        with session_factory() as db:
            existing_id = db.scalar(select(Dataset.id).where(Dataset.name == definition.name))
            if existing_id is not None:
                summary = SeedLoadSummary(definition.name, imported_count=0, status="skipped")
                summaries.append(summary)
                _print_summary(summary)
                continue

            dataset = Dataset(
                name=definition.name,
                description=definition.description,
                workflow_type=definition.workflow_type,
                source_filename=definition.filename,
                test_cases=[
                    TestCase(
                        external_id=test_case.external_id,
                        input_json=test_case.input,
                        expected_output_json=test_case.expected_output,
                        required_citations=test_case.required_citations,
                        tags=test_case.tags,
                        difficulty=test_case.difficulty.value,
                        workflow_type=test_case.workflow_type,
                        metadata_json=test_case.metadata,
                    )
                    for test_case in parsed.valid_cases
                ],
            )

            try:
                db.add(dataset)
                db.commit()
            except SQLAlchemyError:
                db.rollback()
                raise

        summary = SeedLoadSummary(
            definition.name,
            imported_count=parsed.imported_count,
            status="imported",
        )
        summaries.append(summary)
        _print_summary(summary)

    return summaries


def load_prompt_versions() -> list[PromptSeedLoadSummary]:
    """Load bundled prompt versions, skipping versions that already exist."""

    session_factory = get_session_factory()
    summaries: list[PromptSeedLoadSummary] = []

    for definition in PROMPT_SEED_DEFINITIONS:
        with session_factory() as db:
            existing_id = db.scalar(
                select(PromptVersion.id).where(
                    PromptVersion.workflow_type == definition.workflow_type,
                    PromptVersion.name == definition.name,
                    PromptVersion.version_label == definition.version_label,
                )
            )
            if existing_id is not None:
                summary = PromptSeedLoadSummary(
                    prompt_name=definition.name,
                    version_label=definition.version_label,
                    status="skipped",
                )
                summaries.append(summary)
                _print_prompt_summary(summary)
                continue

            prompt_version = PromptVersion(
                name=definition.name,
                workflow_type=definition.workflow_type,
                version_label=definition.version_label,
                template=definition.template,
            )

            try:
                db.add(prompt_version)
                db.commit()
            except SQLAlchemyError:
                db.rollback()
                raise

        summary = PromptSeedLoadSummary(
            prompt_name=definition.name,
            version_label=definition.version_label,
            status="imported",
        )
        summaries.append(summary)
        _print_prompt_summary(summary)

    return summaries


def load_model_configs() -> list[ModelSeedLoadSummary]:
    """Load bundled model configs, skipping exact provider/model pairs that already exist."""

    session_factory = get_session_factory()
    summaries: list[ModelSeedLoadSummary] = []

    for definition in MODEL_SEED_DEFINITIONS:
        with session_factory() as db:
            existing_id = db.scalar(
                select(ModelConfig.id).where(
                    ModelConfig.provider == definition.provider,
                    ModelConfig.model_name == definition.model_name,
                )
            )
            if existing_id is not None:
                summary = ModelSeedLoadSummary(
                    provider=definition.provider,
                    model_name=definition.model_name,
                    status="skipped",
                )
                summaries.append(summary)
                _print_model_summary(summary)
                continue

            model_config = ModelConfig(
                provider=definition.provider,
                model_name=definition.model_name,
                temperature=definition.temperature,
                max_output_tokens=definition.max_output_tokens,
                response_format=definition.response_format,
            )
            try:
                db.add(model_config)
                db.commit()
            except SQLAlchemyError:
                db.rollback()
                raise

        summary = ModelSeedLoadSummary(
            provider=definition.provider,
            model_name=definition.model_name,
            status="imported",
        )
        summaries.append(summary)
        _print_model_summary(summary)

    return summaries


def _parse_seed(definition: SeedDefinition) -> JsonlImportResult:
    path = SEED_DIRECTORY / definition.filename
    parsed = parse_jsonl_test_cases(
        path.read_text(encoding="utf-8"),
        expected_workflow_type=definition.workflow_type,
    )
    if parsed.errors:
        details = "; ".join(f"line {error.line_number}: {error.message}" for error in parsed.errors)
        raise ValueError(f"Invalid seed file {definition.filename}: {details}")
    return parsed


def _print_summary(summary: SeedLoadSummary) -> None:
    print(
        f"{summary.dataset_name}: imported_count={summary.imported_count} status={summary.status}"
    )


def _print_prompt_summary(summary: PromptSeedLoadSummary) -> None:
    print(f"{summary.prompt_name}:{summary.version_label} status={summary.status}")


def _print_model_summary(summary: ModelSeedLoadSummary) -> None:
    print(f"{summary.provider}:{summary.model_name} status={summary.status}")


if __name__ == "__main__":
    load_seed_data()
    load_prompt_versions()
    load_model_configs()
