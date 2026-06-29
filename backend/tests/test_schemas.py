import uuid
from datetime import UTC, datetime

from app.models import Dataset
from app.models import TestCase as CaseModel
from app.schemas import DatasetResponse
from app.schemas import TestCaseResponse as CaseResponseSchema


def test_dataset_response_validates_from_orm_model() -> None:
    dataset = Dataset(
        id=uuid.uuid4(),
        name="Support regression set",
        description=None,
        workflow_type="support",
        source_filename="support.jsonl",
        created_at=datetime.now(UTC),
    )

    response = DatasetResponse.model_validate(dataset)

    assert response.id == dataset.id
    assert response.name == dataset.name
    assert response.description is None
    assert response.workflow_type == "support"
    assert response.source_filename == "support.jsonl"


def test_test_case_response_uses_api_friendly_json_field_names() -> None:
    test_case = CaseModel(
        id=uuid.uuid4(),
        dataset_id=uuid.uuid4(),
        external_id="support-001",
        input_json={"message": "My account is locked"},
        expected_output_json={"category": "account_access"},
        required_citations=["account-access-policy"],
        tags=["authentication"],
        difficulty="medium",
        workflow_type="support",
        metadata_json={"language": "en"},
        created_at=datetime.now(UTC),
    )

    payload = CaseResponseSchema.model_validate(test_case).model_dump()

    assert payload["input"] == {"message": "My account is locked"}
    assert payload["expected_output"] == {"category": "account_access"}
    assert payload["metadata"] == {"language": "en"}
    assert "input_json" not in payload
    assert "expected_output_json" not in payload
    assert "metadata_json" not in payload
