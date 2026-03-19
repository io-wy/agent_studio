"""Tenant isolation and authorization"""
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import Tenant, Project
from app.security.auth import get_current_user, TokenPayload


class TenantContext:
    """Current tenant context"""
    def __init__(self, tenant_id: Optional[str], project_id: Optional[str]):
        self.tenant_id = tenant_id
        self.project_id = project_id


async def get_tenant_context(
    current_user: TokenPayload = Depends(get_current_user),
) -> TenantContext:
    """Get tenant context from current user"""
    return TenantContext(
        tenant_id=current_user.tenant_id,
        project_id=current_user.project_id,
    )


async def get_tenant(
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
) -> Tenant:
    """Get tenant with ownership verification"""
    if ctx.tenant_id and ctx.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this tenant",
        )

    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    return tenant


async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
) -> Project:
    """Get project with tenant ownership verification"""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Verify tenant access
    if ctx.tenant_id and ctx.tenant_id != project.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this project",
        )

    return project


def require_tenant(f):
    """Decorator to require tenant context"""
    async def wrapper(
        ctx: TenantContext = Depends(get_tenant_context),
        *args,
        **kwargs,
    ):
        if not ctx.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant context required",
            )
        return await f(*args, **kwargs)
    return wrapper
