"""Agent repositories"""
import uuid
from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AgentSpec, AgentSpecStatus,
    AgentRevision, AgentRevisionStatus,
    AgentRun, AgentRunStatus,
)


class AgentSpecRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        project_id: str,
        name: str,
        description: Optional[str] = None,
        system_prompt: Optional[str] = None,
        tools: Optional[str] = None,
        model_binding: Optional[str] = None,
    ) -> AgentSpec:
        spec = AgentSpec(
            id=str(uuid.uuid4()),
            project_id=project_id,
            name=name,
            description=description,
            system_prompt=system_prompt,
            tools=tools,
            model_binding=model_binding,
            status=AgentSpecStatus.DRAFT,
        )
        self.db.add(spec)
        await self.db.commit()
        await self.db.refresh(spec)
        return spec

    async def get(self, spec_id: str) -> Optional[AgentSpec]:
        result = await self.db.execute(
            select(AgentSpec).where(AgentSpec.id == spec_id)
        )
        return result.scalar_one_or_none()

    async def list_by_project(self, project_id: str, skip: int = 0, limit: int = 100) -> List[AgentSpec]:
        result = await self.db.execute(
            select(AgentSpec)
            .where(AgentSpec.project_id == project_id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_by_project(self, project_id: str) -> int:
        result = await self.db.execute(
            select(AgentSpec).where(AgentSpec.project_id == project_id)
        )
        return len(list(result.scalars().all()))

    async def update(self, spec: AgentSpec, **kwargs) -> AgentSpec:
        for key, value in kwargs.items():
            if value is not None and hasattr(spec, key):
                setattr(spec, key, value)
        await self.db.commit()
        await self.db.refresh(spec)
        return spec


class AgentRevisionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        agent_spec_id: str,
        revision: int,
        system_prompt: str,
        tools: str,
        model_binding: str,
        workflow_definition: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> AgentRevision:
        rev = AgentRevision(
            id=str(uuid.uuid4()),
            agent_spec_id=agent_spec_id,
            revision=revision,
            system_prompt=system_prompt,
            tools=tools,
            model_binding=model_binding,
            workflow_definition=workflow_definition,
            status=AgentRevisionStatus.DRAFT,
            created_by=created_by,
        )
        self.db.add(rev)
        await self.db.commit()
        await self.db.refresh(rev)
        return rev

    async def get(self, revision_id: str) -> Optional[AgentRevision]:
        result = await self.db.execute(
            select(AgentRevision).where(AgentRevision.id == revision_id)
        )
        return result.scalar_one_or_none()

    async def list_by_spec(self, agent_spec_id: str, skip: int = 0, limit: int = 100) -> List[AgentRevision]:
        result = await self.db.execute(
            select(AgentRevision)
            .where(AgentRevision.agent_spec_id == agent_spec_id)
            .order_by(AgentRevision.revision.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_by_spec(self, agent_spec_id: str) -> int:
        result = await self.db.execute(
            select(AgentRevision).where(AgentRevision.agent_spec_id == agent_spec_id)
        )
        return len(list(result.scalars().all()))

    async def get_latest(self, agent_spec_id: str) -> Optional[AgentRevision]:
        result = await self.db.execute(
            select(AgentRevision)
            .where(AgentRevision.agent_spec_id == agent_spec_id)
            .order_by(AgentRevision.revision.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def update(self, revision: AgentRevision, **kwargs) -> AgentRevision:
        for key, value in kwargs.items():
            if value is not None and hasattr(revision, key):
                setattr(revision, key, value)
        await self.db.commit()
        await self.db.refresh(revision)
        return revision


class AgentRunRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        revision_id: str,
        input_data: Optional[str] = None,
    ) -> AgentRun:
        run = AgentRun(
            id=str(uuid.uuid4()),
            revision_id=revision_id,
            input_data=input_data,
            status=AgentRunStatus.QUEUED,
        )
        self.db.add(run)
        await self.db.commit()
        await self.db.refresh(run)
        return run

    async def get(self, run_id: str) -> Optional[AgentRun]:
        result = await self.db.execute(
            select(AgentRun).where(AgentRun.id == run_id)
        )
        return result.scalar_one_or_none()

    async def list_by_revision(self, revision_id: str, skip: int = 0, limit: int = 100) -> List[AgentRun]:
        result = await self.db.execute(
            select(AgentRun)
            .where(AgentRun.revision_id == revision_id)
            .order_by(AgentRun.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_by_revision(self, revision_id: str) -> int:
        result = await self.db.execute(
            select(AgentRun).where(AgentRun.revision_id == revision_id)
        )
        return len(list(result.scalars().all()))

    async def update(self, run: AgentRun, **kwargs) -> AgentRun:
        for key, value in kwargs.items():
            if value is not None and hasattr(run, key):
                setattr(run, key, value)
        await self.db.commit()
        await self.db.refresh(run)
        return run
