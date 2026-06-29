import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Dataset, TestCase
from app.schemas.datasets import (
    DatasetDetailResponse,
    DatasetImportRequest,
    DatasetImportResponse,
    DatasetListItem,
)
from app.schemas.test_cases import TestCaseResponse
from app.services.jsonl_importer import parse_jsonl_test_cases

router = APIRouter(prefix="/datasets", tags=["datasets"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/import-jsonl",
    response_model=DatasetImportResponse,
    status_code=status.HTTP_201_CREATED,
)
def import_dataset_jsonl(
    request: DatasetImportRequest,
    response: Response,
    db: DbSession,
) -> DatasetImportResponse:
    parsed = parse_jsonl_test_cases(
        request.jsonl_content,
        expected_workflow_type=request.workflow_type,
    )
    if parsed.errors:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return DatasetImportResponse(
            dataset_id=None,
            imported_count=0,
            rejected_count=parsed.rejected_count,
            errors=parsed.errors,
        )

    dataset = Dataset(
        name=request.name,
        description=request.description,
        workflow_type=request.workflow_type,
        source_filename=request.source_filename,
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
        with db.begin():
            db.add(dataset)
            db.flush()
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Dataset import failed",
        ) from exc

    return DatasetImportResponse(
        dataset_id=dataset.id,
        imported_count=parsed.imported_count,
        rejected_count=0,
        errors=[],
    )


@router.get("", response_model=list[DatasetListItem])
def list_datasets(db: DbSession) -> list[DatasetListItem]:
    count = _test_case_count_subquery()
    rows = db.execute(
        select(Dataset, count.label("test_case_count")).order_by(
            Dataset.created_at.desc(), Dataset.id
        )
    ).all()

    return [
        DatasetListItem(
            id=dataset.id,
            name=dataset.name,
            workflow_type=dataset.workflow_type,
            source_filename=dataset.source_filename,
            created_at=dataset.created_at,
            test_case_count=test_case_count,
        )
        for dataset, test_case_count in rows
    ]


@router.get("/{dataset_id}", response_model=DatasetDetailResponse)
def get_dataset(dataset_id: uuid.UUID, db: DbSession) -> DatasetDetailResponse:
    count = _test_case_count_subquery()
    row = db.execute(
        select(Dataset, count.label("test_case_count")).where(Dataset.id == dataset_id)
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    dataset, test_case_count = row
    return DatasetDetailResponse(
        id=dataset.id,
        name=dataset.name,
        description=dataset.description,
        workflow_type=dataset.workflow_type,
        source_filename=dataset.source_filename,
        created_at=dataset.created_at,
        test_case_count=test_case_count,
    )


@router.get("/{dataset_id}/test-cases", response_model=list[TestCaseResponse])
def list_dataset_test_cases(
    dataset_id: uuid.UUID,
    db: DbSession,
) -> list[TestCase]:
    if db.get(Dataset, dataset_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    return list(
        db.scalars(
            select(TestCase)
            .where(TestCase.dataset_id == dataset_id)
            .order_by(TestCase.created_at, TestCase.id)
        )
    )


def _test_case_count_subquery():
    return (
        select(func.count(TestCase.id))
        .where(TestCase.dataset_id == Dataset.id)
        .correlate(Dataset)
        .scalar_subquery()
    )
