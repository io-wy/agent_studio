"""Agent schemas"""
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


# AgentSpec
class AgentSpecBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class AgentSpecCreate(AgentSpecBase):
    project_id: str
    system_prompt: Optional[str] = None
    tools: Optional[str] = None  # JSON array
    model_binding: Optional[str] = None


class AgentSpecUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    tools: Optional[str] = None
    model_binding: Optional[str] = None
    status: Optional[str] = None


class AgentSpecResponse(AgentSpecBase):
    id: str
    project_id: str
    status: str
    system_prompt: Optional[str]
    tools: Optional[str]
    model_binding: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# AgentRevision
class AgentRevisionBase(BaseModel):
    pass


class AgentRevisionCreate(AgentRevisionBase):
    agent_spec_id: str
    system_prompt: str
    tools: str  # JSON
    model_binding: str
    workflow_definition: Optional[str] = None


class AgentRevisionUpdate(BaseModel):
    status: Optional[str] = None
    eval_score: Optional[float] = None
    eval_report: Optional[str] = None


class AgentRevisionResponse(BaseModel):
    id: str
    agent_spec_id: str
    revision: int
    status: str
    system_prompt: str
    tools: str
    model_binding: str
    workflow_definition: Optional[str]
    bundle_path: Optional[str]
    eval_score: Optional[float]
    eval_report: Optional[str]
    created_at: datetime
    created_by: Optional[str]
    published_at: Optional[datetime]

    model_config = {"from_attributes": True}


class AgentRevisionPublishRequest(BaseModel):
    pass  # No body needed, just publish current revision


# AgentRun
class AgentRunCreate(BaseModel):
    revision_id: str
    input_data: Optional[str] = None  # JSON input


class AgentRunUpdate(BaseModel):
    status: Optional[str] = None
    output_data: Optional[str] = None
    error_message: Optional[str] = None


class AgentRunResponse(BaseModel):
    id: str
    revision_id: str
    status: str
    input_data: Optional[str]
    k8s_job_name: Optional[str]
    k8s_namespace: Optional[str]
    output_data: Optional[str]
    error_message: Optional[str]
    tokens_used: Optional[int]
    tool_calls: Optional[int]
    duration_seconds: Optional[int]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentRunInterruptRequest(BaseModel):
    reason: Optional[str] = None
