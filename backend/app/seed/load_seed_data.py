"""Load bundled seed datasets, skipping any dataset whose name already exists."""

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.db import get_session_factory
from app.models import Dataset, PromptVersion, TestCase
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


if __name__ == "__main__":
    load_seed_data()
    load_prompt_versions()
