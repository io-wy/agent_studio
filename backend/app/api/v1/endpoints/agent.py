"""Agent endpoints"""
import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.agent import AgentService
from app.schemas import (
    AgentSpecCreate, AgentSpecUpdate, AgentSpecResponse,
    AgentRevisionCreate, AgentRevisionUpdate, AgentRevisionResponse, AgentRevisionPublishRequest,
    AgentRunCreate, AgentRunUpdate, AgentRunResponse, AgentRunInterruptRequest,
)
from app.security import get_current_user, TokenPayload

router = APIRouter(prefix="/agents", tags=["agents"])


# === AgentSpec ===

@router.post("", response_model=AgentSpecResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    data: AgentSpecCreate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Create a new agent"""
    service = AgentService(db)
    agent = await service.create_agent(
        project_id=data.project_id,
        name=data.name,
        description=data.description,
        system_prompt=data.system_prompt,
        tools=data.tools,
        model_binding=data.model_binding,
    )
    return agent


@router.get("/{agent_id}", response_model=AgentSpecResponse)
async def get_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Get agent by ID"""
    service = AgentService(db)
    agent = await service.get_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )
    return agent


@router.get("", response_model=List[AgentSpecResponse])
async def list_agents(
    project_id: str,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """List agents in project"""
    service = AgentService(db)
    agents = await service.list_agents(project_id, skip, limit)
    return agents


@router.patch("/{agent_id}", response_model=AgentSpecResponse)
async def update_agent(
    agent_id: str,
    data: AgentSpecUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Update agent"""
    service = AgentService(db)
    update_data = data.model_dump(exclude_unset=True)
    agent = await service.update_agent(agent_id, **update_data)
    return agent


# === AgentRevision ===

@router.post("/{agent_id}/revisions", response_model=AgentRevisionResponse, status_code=status.HTTP_201_CREATED)
async def create_revision(
    agent_id: str,
    data: AgentRevisionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Create new agent revision"""
    service = AgentService(db)
    revision = await service.create_revision(
        agent_spec_id=data.agent_spec_id or agent_id,
        system_prompt=data.system_prompt,
        tools=data.tools,
        model_binding=data.model_binding,
        workflow_definition=data.workflow_definition,
        created_by=current_user.sub,
    )
    return revision


@router.get("/{agent_id}/revisions", response_model=List[AgentRevisionResponse])
async def list_revisions(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """List all revisions of an agent"""
    service = AgentService(db)
    revisions = await service.list_revisions(agent_id)
    return revisions


# === AgentRevision specific endpoints ===
revision_router = APIRouter(prefix="/agent-revisions", tags=["agent-revisions"])


@revision_router.get("/{revision_id}", response_model=AgentRevisionResponse)
async def get_revision(
    revision_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Get revision by ID"""
    service = AgentService(db)
    revision = await service.get_revision(revision_id)
    if not revision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Revision not found",
        )
    return revision


@revision_router.post("/{revision_id}/publish")
async def publish_revision(
    revision_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Publish agent revision"""
    service = AgentService(db)
    revision = await service.publish_revision(revision_id)
    return {
        "revision_id": revision.id,
        "status": revision.status.value if hasattr(revision.status, 'value') else str(revision.status),
        "published_at": revision.published_at.isoformat() if revision.published_at else None,
    }


# === AgentRun ===

run_router = APIRouter(prefix="/agent-runs", tags=["agent-runs"])


@run_router.post("", response_model=AgentRunResponse, status_code=status.HTTP_201_CREATED)
async def create_agent_run(
    data: AgentRunCreate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Create and start a new agent run"""
    service = AgentService(db)
    run = await service.start_run(
        revision_id=data.revision_id,
        input_data=data.input_data,
    )
    return run


@run_router.get("/{run_id}", response_model=AgentRunResponse)
async def get_agent_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Get agent run by ID"""
    service = AgentService(db)
    run = await service.get_run(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )
    return run


@run_router.get("", response_model=List[AgentRunResponse])
async def list_agent_runs(
    revision_id: str,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """List runs for a revision"""
    service = AgentService(db)
    runs = await service.list_runs(revision_id, skip, limit)
    return runs


@run_router.post("/{run_id}/interrupt")
async def interrupt_agent_run(
    run_id: str,
    data: AgentRunInterruptRequest = None,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Interrupt a running agent"""
    service = AgentService(db)
    reason = data.reason if data else None
    run = await service.interrupt_run(run_id, reason)
    return {
        "run_id": run.id,
        "status": run.status.value if hasattr(run.status, 'value') else str(run.status),
    }
