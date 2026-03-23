"""Dataset endpoints"""
import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import Project
from app.repositories.tenant import ProjectRepository
from app.services.dataset import DatasetService
from app.schemas import (
    DatasetCreate, DatasetUpdate, DatasetResponse,
    DatasetVersionCreate, DatasetVersionUpdate, DatasetVersionResponse,
    DatasetImportRequest, DatasetValidateRequest, DatasetSplitRequest,
    PaginatedResponse,
    create_paginated_response,
)
from app.security import get_current_user, TokenPayload

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post("", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
async def create_dataset(
    data: DatasetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Create a new dataset"""
    # Verify project exists
    project_repo = ProjectRepository(db)
    project = await project_repo.get(data.project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    service = DatasetService(db)
    dataset = await service.create_dataset(
        project_id=data.project_id,
        name=data.name,
        data_format=data.data_format,
        description=data.description,
        schema=data.schema_,
    )
    return dataset


@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(
    dataset_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Get dataset by ID"""
    service = DatasetService(db)
    dataset = await service.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found",
        )
    return dataset


@router.get("", response_model=PaginatedResponse[DatasetResponse])
async def list_datasets(
    project_id: str,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """List datasets in project"""
    service = DatasetService(db)
    skip = (page - 1) * page_size
    datasets = await service.list_datasets(project_id, skip, page_size)
    total = await service.count_datasets(project_id)
    return create_paginated_response(
        [DatasetResponse.model_validate(d) for d in datasets],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.patch("/{dataset_id}", response_model=DatasetResponse)
async def update_dataset(
    dataset_id: str,
    data: DatasetUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Update dataset"""
    service = DatasetService(db)
    dataset = await service.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found",
        )

    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(dataset, key, value)

    await db.commit()
    await db.refresh(dataset)
    return dataset


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dataset(
    dataset_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Delete dataset"""
    service = DatasetService(db)
    deleted = await service.delete_dataset(dataset_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found",
        )


# File upload endpoints
@router.post("/{dataset_id}/upload")
async def upload_file(
    dataset_id: str,
    file: UploadFile = File(...),
    version: str = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Upload file to dataset"""
    service = DatasetService(db)

    # Check dataset exists
    dataset = await service.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found",
        )

    # Read file content
    content = await file.read()

    # Upload
    dataset_version = await service.upload_file(
        dataset_id=dataset_id,
        file_content=content,
        filename=file.filename,
        version=version,
    )

    return {
        "version_id": dataset_version.id,
        "version": dataset_version.version,
        "storage_prefix": dataset_version.storage_prefix,
        "size": dataset_version.file_size_bytes,
        "checksum": dataset_version.checksum,
    }


@router.post("/{dataset_id}/upload-url")
async def get_upload_url(
    dataset_id: str,
    filename: str = Form(...),
    content_type: str = Form(...),
    version: str = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Get presigned URL for direct upload"""
    service = DatasetService(db)

    # Check dataset exists
    dataset = await service.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found",
        )

    result = await service.get_presigned_upload_url(
        dataset_id=dataset_id,
        filename=filename,
        content_type=content_type,
        version=version,
    )

    return result


# Version endpoints
@router.post("/{dataset_id}/versions", response_model=DatasetVersionResponse, status_code=status.HTTP_201_CREATED)
async def create_version(
    dataset_id: str,
    source_version: str = Form(...),
    new_version: str = Form(...),
    description: str = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Create new version from existing version"""
    service = DatasetService(db)

    # Check dataset exists
    dataset = await service.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found",
        )

    version = await service.create_version(
        dataset_id=dataset_id,
        source_version=source_version,
        new_version=new_version,
        description=description,
    )

    return version


@router.get("/{dataset_id}/versions", response_model=List[DatasetVersionResponse])
async def list_versions(
    dataset_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """List all versions of dataset"""
    service = DatasetService(db)
    versions = await service.list_versions(dataset_id)
    return versions


@router.get("/versions/{version_id}", response_model=DatasetVersionResponse)
async def get_version(
    version_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Get specific version"""
    service = DatasetService(db)
    version = await service.get_version(version_id)
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found",
        )
    return version


@router.post("/versions/{version_id}/validate")
async def validate_version(
    version_id: str,
    data: DatasetValidateRequest = None,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Validate dataset version"""
    service = DatasetService(db)
    rules = data.validation_rules if data else None

    result = await service.validate_version(version_id, rules)
    return result


@router.post("/versions/{version_id}/splits")
async def create_splits(
    version_id: str,
    data: DatasetSplitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Create train/val/test splits"""
    # TODO: Implement split logic
    return {
        "message": "Splits feature not yet implemented",
        "version_id": version_id,
    }
