"""Tenant endpoints"""
import re
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import Tenant, Project, TenantStatus, ProjectStatus
from app.repositories.tenant import TenantRepository, ProjectRepository
from app.schemas import (
    TenantCreate, TenantUpdate, TenantResponse,
    ProjectCreate, ProjectUpdate, ProjectResponse,
    QuotaInfo, QuotaUpdate,
)
from app.security import get_current_user, TokenPayload

router = APIRouter(prefix="/tenants", tags=["tenants"])


def generate_namespace(tenant_name: str, project_name: str = None) -> str:
    """Generate valid K8s namespace"""
    base = tenant_name.lower().replace(" ", "-")
    if project_name:
        base += f"-{project_name.lower().replace(' ', '-')}"
    # K8s namespace must be 63 chars or less, lowercase, alphanumeric and hyphens
    return base[:63].strip("-")


@router.post("", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    data: TenantCreate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Create a new tenant"""
    repo = TenantRepository(db)

    # Check name uniqueness
    existing = await repo.get_by_name(data.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tenant with this name already exists",
        )

    tenant = await repo.create(
        name=data.name,
        quota_gpuHours=data.quota_gpuHours,
        quota_storage_gb=data.quota_storage_gb,
        quota_deployments=data.quota_deployments,
    )
    return tenant


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Get tenant by ID"""
    repo = TenantRepository(db)
    tenant = await repo.get(tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )
    return tenant


@router.get("", response_model=List[TenantResponse])
async def list_tenants(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """List all tenants"""
    repo = TenantRepository(db)
    tenants = await repo.list_(skip=skip, limit=limit)
    return tenants


@router.patch("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: str,
    data: TenantUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Update tenant"""
    repo = TenantRepository(db)
    tenant = await repo.get(tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    update_data = data.model_dump(exclude_unset=True)
    tenant = await repo.update(tenant, **update_data)
    return tenant


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Delete tenant"""
    repo = TenantRepository(db)
    tenant = await repo.get(tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )
    await repo.delete(tenant)


# Project endpoints
project_router = APIRouter(prefix="/projects", tags=["projects"])


@project_router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Create a new project"""
    tenant_repo = TenantRepository(db)
    tenant = await tenant_repo.get(data.tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    project_repo = ProjectRepository(db)
    namespace = generate_namespace(tenant.name, data.name)

    project = await project_repo.create(
        tenant_id=data.tenant_id,
        name=data.name,
        namespace=namespace,
        description=data.description,
        quota_gpuHours=data.quota_gpuHours,
        quota_storage_gb=data.quota_storage_gb,
        quota_deployments=data.quota_deployments,
    )
    return project


@project_router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Get project by ID"""
    repo = ProjectRepository(db)
    project = await repo.get(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return project


@project_router.get("", response_model=List[ProjectResponse])
async def list_projects(
    tenant_id: str,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """List projects by tenant"""
    repo = ProjectRepository(db)
    projects = await repo.list_by_tenant(tenant_id, skip=skip, limit=limit)
    return projects


@project_router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    data: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Update project"""
    repo = ProjectRepository(db)
    project = await repo.get(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    update_data = data.model_dump(exclude_unset=True)
    project = await repo.update(project, **update_data)
    return project


@project_router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Delete project"""
    repo = ProjectRepository(db)
    project = await repo.get(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    await repo.delete(project)


@project_router.post("/{project_id}/quotas", response_model=ProjectResponse)
async def update_project_quota(
    project_id: str,
    data: QuotaUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Update project quota"""
    repo = ProjectRepository(db)
    project = await repo.get(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    update_data = data.model_dump(exclude_unset=True)
    project = await repo.update(project, **update_data)
    return project
