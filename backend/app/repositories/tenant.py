"""Tenant and Project repositories"""
import uuid
from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Tenant, Project, TenantStatus, ProjectStatus


class TenantRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, name: str, **kwargs) -> Tenant:
        tenant = Tenant(
            id=str(uuid.uuid4()),
            name=name,
            **kwargs,
        )
        self.db.add(tenant)
        await self.db.commit()
        await self.db.refresh(tenant)
        return tenant

    async def get(self, tenant_id: str) -> Optional[Tenant]:
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[Tenant]:
        result = await self.db.execute(
            select(Tenant).where(Tenant.name == name)
        )
        return result.scalar_one_or_none()

    async def list_(self, skip: int = 0, limit: int = 100) -> List[Tenant]:
        result = await self.db.execute(
            select(Tenant).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def count(self) -> int:
        result = await self.db.execute(select(Tenant))
        return len(list(result.scalars().all()))

    async def update(self, tenant: Tenant, **kwargs) -> Tenant:
        for key, value in kwargs.items():
            if value is not None and hasattr(tenant, key):
                setattr(tenant, key, value)
        await self.db.commit()
        await self.db.refresh(tenant)
        return tenant

    async def delete(self, tenant: Tenant) -> None:
        await self.db.delete(tenant)
        await self.db.commit()


class ProjectRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, tenant_id: str, name: str, namespace: str, **kwargs) -> Project:
        project = Project(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            name=name,
            namespace=namespace,
            **kwargs,
        )
        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def get(self, project_id: str) -> Optional[Project]:
        result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        return result.scalar_one_or_none()

    async def list_by_tenant(self, tenant_id: str, skip: int = 0, limit: int = 100) -> List[Project]:
        result = await self.db.execute(
            select(Project)
            .where(Project.tenant_id == tenant_id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_by_tenant(self, tenant_id: str) -> int:
        result = await self.db.execute(
            select(Project).where(Project.tenant_id == tenant_id)
        )
        return len(list(result.scalars().all()))

    async def update(self, project: Project, **kwargs) -> Project:
        for key, value in kwargs.items():
            if value is not None and hasattr(project, key):
                setattr(project, key, value)
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def delete(self, project: Project) -> None:
        await self.db.delete(project)
        await self.db.commit()
