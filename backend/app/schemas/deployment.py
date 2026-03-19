"""Deployment schemas"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DeploymentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class DeploymentCreate(DeploymentBase):
    project_id: str
    model_version_id: Optional[str] = None
    agent_revision_id: Optional[str] = None
    deployment_type: str = Field(..., pattern="^(kserve|ray)$")
    model_format: Optional[str] = Field(None, pattern="^(pytorch|vllm|triton|llamafile)$")
    replicas: int = Field(default=1, ge=1)
    min_replicas: int = Field(default=0, ge=0)
    max_replicas: int = Field(default=3, ge=1)
    gpu_count: int = Field(default=1, ge=0)


class DeploymentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    replicas: Optional[int] = Field(None, ge=1)
    min_replicas: Optional[int] = Field(None, ge=0)
    max_replicas: Optional[int] = Field(None, ge=1)
    gpu_count: Optional[int] = Field(None, ge=0)


class DeploymentResponse(DeploymentBase):
    id: str
    project_id: str
    model_version_id: Optional[str]
    agent_revision_id: Optional[str]
    status: str
    deployment_type: str
    model_format: Optional[str]
    replicas: int
    min_replicas: int
    max_replicas: int
    gpu_count: int
    endpoint_url: Optional[str]
    service_url: Optional[str]
    k8s_service_name: Optional[str]
    k8s_ingress_name: Optional[str]
    traffic_percentage: int
    metrics: Optional[str]
    created_at: datetime
    updated_at: datetime
    ready_at: Optional[datetime]
    created_by: Optional[str]

    model_config = {"from_attributes": True}


class DeploymentScaleRequest(BaseModel):
    replicas: int = Field(..., ge=0)
    min_replicas: Optional[int] = Field(None, ge=0)
    max_replicas: Optional[int] = Field(None, ge=1)


class DeploymentTrafficShiftRequest(BaseModel):
    target_revision_id: Optional[str] = None
    target_percentage: int = Field(..., ge=0, le=100)


class DeploymentRollbackRequest(BaseModel):
    revision_id: Optional[str] = None  # If not specified, rollback to previous


class DeploymentHealthResponse(BaseModel):
    deployment_id: str
    status: str
    replicas_ready: int
    replicas_total: int
    gpu_utilization: Optional[float]
    avg_latency_ms: Optional[float]
    last_check: datetime
