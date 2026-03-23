"""Deployment endpoints"""
import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.deployment import DeploymentService
from app.schemas import (
    DeploymentCreate, DeploymentUpdate, DeploymentResponse,
    DeploymentScaleRequest, DeploymentTrafficShiftRequest, DeploymentRollbackRequest,
    DeploymentHealthResponse,
    PaginatedResponse,
    create_paginated_response,
)
from app.security import get_current_user, TokenPayload

router = APIRouter(prefix="/deployments", tags=["deployments"])


@router.post("", response_model=DeploymentResponse, status_code=status.HTTP_201_CREATED)
async def create_deployment(
    data: DeploymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Create a new deployment"""
    service = DeploymentService(db)
    deployment = await service.create_deployment(
        project_id=data.project_id,
        name=data.name,
        deployment_type=data.deployment_type,
        model_version_id=data.model_version_id,
        agent_revision_id=data.agent_revision_id,
        description=data.description,
        model_format=data.model_format,
        replicas=data.replicas,
        min_replicas=data.min_replicas,
        max_replicas=data.max_replicas,
        gpu_count=data.gpu_count,
        created_by=current_user.sub,
    )
    return deployment


@router.get("/{deployment_id}", response_model=DeploymentResponse)
async def get_deployment(
    deployment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Get deployment by ID"""
    service = DeploymentService(db)
    deployment = await service.get_deployment(deployment_id)
    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found",
        )
    return deployment


@router.get("", response_model=PaginatedResponse[DeploymentResponse])
async def list_deployments(
    project_id: str,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """List deployments in project"""
    service = DeploymentService(db)
    skip = (page - 1) * page_size
    deployments = await service.list_deployments(project_id, skip, page_size)
    total = await service.count_deployments(project_id)
    return create_paginated_response(
        [DeploymentResponse.model_validate(d) for d in deployments],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.patch("/{deployment_id}", response_model=DeploymentResponse)
async def update_deployment(
    deployment_id: str,
    data: DeploymentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Update deployment"""
    service = DeploymentService(db)
    deployment = await service.get_deployment(deployment_id)
    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found",
        )

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(deployment, key, value)

    await db.commit()
    await db.refresh(deployment)
    return deployment


@router.delete("/{deployment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_deployment(
    deployment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Delete deployment"""
    service = DeploymentService(db)
    deleted = await service.delete_deployment(deployment_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found",
        )


@router.post("/{deployment_id}/deploy")
async def deploy_model(
    deployment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Deploy model to Kubernetes"""
    service = DeploymentService(db)
    deployment = await service.deploy(deployment_id)
    return {
        "deployment_id": deployment.id,
        "status": deployment.status.value if hasattr(deployment.status, 'value') else str(deployment.status),
        "k8s_service_name": deployment.k8s_service_name,
    }


@router.post("/{deployment_id}/scale")
async def scale_deployment(
    deployment_id: str,
    data: DeploymentScaleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Scale deployment"""
    service = DeploymentService(db)
    deployment = await service.scale_deployment(
        deployment_id=deployment_id,
        replicas=data.replicas,
        min_replicas=data.min_replicas,
        max_replicas=data.max_replicas,
    )
    return {
        "deployment_id": deployment.id,
        "replicas": deployment.replicas,
        "min_replicas": deployment.min_replicas,
        "max_replicas": deployment.max_replicas,
    }


@router.post("/{deployment_id}/traffic-shift")
async def shift_traffic(
    deployment_id: str,
    data: DeploymentTrafficShiftRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Shift traffic between revisions"""
    service = DeploymentService(db)
    deployment = await service.traffic_shift(
        deployment_id=deployment_id,
        target_revision_id=data.target_revision_id,
        target_percentage=data.target_percentage,
    )
    return {
        "deployment_id": deployment.id,
        "traffic_percentage": deployment.traffic_percentage,
    }


@router.post("/{deployment_id}/rollback")
async def rollback_deployment(
    deployment_id: str,
    data: DeploymentRollbackRequest = None,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Rollback deployment"""
    service = DeploymentService(db)
    revision_id = data.revision_id if data else None
    deployment = await service.rollback_deployment(deployment_id, revision_id)
    return {
        "deployment_id": deployment.id,
        "traffic_percentage": deployment.traffic_percentage,
    }


@router.get("/{deployment_id}/health", response_model=DeploymentHealthResponse)
async def get_deployment_health(
    deployment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Get deployment health"""
    service = DeploymentService(db)
    health = await service.get_health(deployment_id)
    return health
