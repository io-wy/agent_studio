"""Training and Model Registry endpoints"""
import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.training import TrainingService
from app.schemas import (
    TrainingJobCreate, TrainingJobUpdate, TrainingJobResponse, TrainingJobCancelRequest,
    ModelCreate, ModelUpdate, ModelResponse,
    ModelVersionResponse, ModelVersionPromoteRequest,
)
from app.security import get_current_user, TokenPayload

router = APIRouter(prefix="/training-jobs", tags=["training"])


@router.post("", response_model=TrainingJobResponse, status_code=status.HTTP_201_CREATED)
async def create_training_job(
    data: TrainingJobCreate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Create a new training job"""
    service = TrainingService(db)
    job = await service.create_training_job(
        project_id=data.project_id,
        name=data.name,
        base_model=data.base_model,
        training_type=data.training_type,
        dataset_version_id=data.dataset_version_id,
        description=data.description,
        config_yaml=data.config_yaml,
        created_by=current_user.sub,
    )
    return job


@router.get("/{job_id}", response_model=TrainingJobResponse)
async def get_training_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Get training job by ID"""
    service = TrainingService(db)
    job = await service.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Training job not found",
        )
    return job


@router.get("", response_model=List[TrainingJobResponse])
async def list_training_jobs(
    project_id: str,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """List training jobs in project"""
    service = TrainingService(db)
    jobs = await service.list_jobs(project_id, skip, limit)
    return jobs


@router.post("/{job_id}/submit")
async def submit_training_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Submit training job to Kubernetes"""
    service = TrainingService(db)
    job = await service.submit_job(job_id)
    return {
        "job_id": job.id,
        "status": job.status.value if hasattr(job.status, 'value') else str(job.status),
        "k8s_job_name": job.k8s_job_name,
        "k8s_namespace": job.k8s_namespace,
    }


@router.post("/{job_id}/cancel", response_model=TrainingJobResponse)
async def cancel_training_job(
    job_id: str,
    data: TrainingJobCancelRequest = None,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Cancel training job"""
    service = TrainingService(db)
    job = await service.cancel_job(job_id)
    return job


@router.get("/{job_id}/logs")
async def get_training_job_logs(
    job_id: str,
    tail_lines: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Get training job logs"""
    service = TrainingService(db)
    logs = await service.get_job_logs(job_id, tail_lines)
    return {"job_id": job_id, "logs": logs}


@router.get("/{job_id}/metrics")
async def get_training_job_metrics(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Get training job metrics"""
    service = TrainingService(db)
    metrics = await service.get_job_metrics(job_id)
    return metrics


# Model Registry endpoints
model_router = APIRouter(prefix="/models", tags=["models"])


@model_router.post("", response_model=ModelResponse, status_code=status.HTTP_201_CREATED)
async def create_model(
    data: ModelCreate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Create a new model"""
    from app.repositories.training import ModelRepository
    import uuid

    repo = ModelRepository(db)
    model = await repo.create(
        project_id=data.project_id,
        name=data.name,
        base_model=data.base_model,
        description=data.description,
    )
    return model


@model_router.get("/{model_id}", response_model=ModelResponse)
async def get_model(
    model_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Get model by ID"""
    from app.repositories.training import ModelRepository

    repo = ModelRepository(db)
    model = await repo.get(model_id)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )
    return model


@model_router.get("", response_model=List[ModelResponse])
async def list_models(
    project_id: str,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """List models in project"""
    from app.repositories.training import ModelRepository

    repo = ModelRepository(db)
    models = await repo.list_by_project(project_id, skip, limit)
    return models


@model_router.get("/{model_id}/versions", response_model=List[ModelVersionResponse])
async def list_model_versions(
    model_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """List versions of a model"""
    from app.repositories.training import ModelVersionRepository

    repo = ModelVersionRepository(db)
    versions = await repo.list_by_model(model_id)
    return versions


@model_router.get("/versions/{version_id}", response_model=ModelVersionResponse)
async def get_model_version(
    version_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Get model version by ID"""
    from app.repositories.training import ModelVersionRepository

    repo = ModelVersionRepository(db)
    version = await repo.get(version_id)
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model version not found",
        )
    return version


@model_router.post("/versions/{version_id}/promote")
async def promote_model_version(
    version_id: str,
    data: ModelVersionPromoteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Promote model version to next stage"""
    from app.models import ModelVersionStatus

    from app.repositories.training import ModelVersionRepository

    repo = ModelVersionRepository(db)
    version = await repo.get(version_id)
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model version not found",
        )

    # Update status
    status_map = {
        "validated": ModelVersionStatus.VALIDATED,
        "staged": ModelVersionStatus.STAGED,
        "production": ModelVersionStatus.PRODUCTION,
        "deprecated": ModelVersionStatus.DEPRECATED,
    }

    new_status = status_map.get(data.target_status)
    if not new_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid target status",
        )

    version = await repo.update(version, status=new_status)
    return {"version_id": version_id, "status": version.status.value}


@model_router.get("/versions/{version_id}/lineage")
async def get_model_lineage(
    version_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Get model version lineage"""
    from app.repositories.training import ModelVersionRepository
    from app.repositories.dataset import DatasetVersionRepository
    from app.repositories.training import TrainingJobRepository

    version_repo = ModelVersionRepository(db)
    version = await version_repo.get(version_id)
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model version not found",
        )

    lineage = {
        "model_version_id": version.id,
        "model_version": version.version,
    }

    # Add dataset version if exists
    if version.dataset_version_id:
        dv_repo = DatasetVersionRepository(db)
        dv = await dv_repo.get(version.dataset_version_id)
        if dv:
            lineage["dataset_version"] = {
                "id": dv.id,
                "version": dv.version,
            }

    # Add training job if exists
    if version.training_job_id:
        tj_repo = TrainingJobRepository(db)
        tj = await tj_repo.get(version.training_job_id)
        if tj:
            lineage["training_job"] = {
                "id": tj.id,
                "name": tj.name,
                "base_model": tj.base_model,
            }

    return lineage
