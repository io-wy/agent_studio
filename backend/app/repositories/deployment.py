"""Deployment repositories"""
import uuid
from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Deployment, DeploymentStatus


class DeploymentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        project_id: str,
        name: str,
        deployment_type: str,
        model_version_id: Optional[str] = None,
        agent_revision_id: Optional[str] = None,
        description: Optional[str] = None,
        model_format: Optional[str] = None,
        replicas: int = 1,
        min_replicas: int = 0,
        max_replicas: int = 3,
        gpu_count: int = 1,
        created_by: Optional[str] = None,
    ) -> Deployment:
        deployment = Deployment(
            id=str(uuid.uuid4()),
            project_id=project_id,
            name=name,
            description=description,
            deployment_type=deployment_type,
            model_format=model_format,
            model_version_id=model_version_id,
            agent_revision_id=agent_revision_id,
            replicas=replicas,
            min_replicas=min_replicas,
            max_replicas=max_replicas,
            gpu_count=gpu_count,
            status=DeploymentStatus.PENDING,
            created_by=created_by,
        )
        self.db.add(deployment)
        await self.db.commit()
        await self.db.refresh(deployment)
        return deployment

    async def get(self, deployment_id: str) -> Optional[Deployment]:
        result = await self.db.execute(
            select(Deployment).where(Deployment.id == deployment_id)
        )
        return result.scalar_one_or_none()

    async def list_by_project(self, project_id: str, skip: int = 0, limit: int = 100) -> List[Deployment]:
        result = await self.db.execute(
            select(Deployment)
            .where(Deployment.project_id == project_id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_by_model_version(self, model_version_id: str) -> List[Deployment]:
        result = await self.db.execute(
            select(Deployment)
            .where(Deployment.model_version_id == model_version_id)
        )
        return list(result.scalars().all())

    async def update(self, deployment: Deployment, **kwargs) -> Deployment:
        for key, value in kwargs.items():
            if value is not None and hasattr(deployment, key):
                setattr(deployment, key, value)
        await self.db.commit()
        await self.db.refresh(deployment)
        return deployment

    async def delete(self, deployment: Deployment) -> None:
        await self.db.delete(deployment)
        await self.db.commit()
