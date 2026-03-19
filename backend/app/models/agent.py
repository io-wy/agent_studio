"""Deployment and Agent models"""
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DeploymentStatus(str, Enum):
    PENDING = "pending"
    PROVISIONING = "provisioning"
    READY = "ready"
    SCALING = "scaling"
    DEGRADED = "degraded"
    FAILED = "failed"
    DELETING = "deleting"


class Deployment(Base):
    __tablename__ = "deployments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True)
    model_version_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("model_versions.id"), nullable=True)
    agent_revision_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("agent_revisions.id"), nullable=True)

    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[DeploymentStatus] = mapped_column(SQLEnum(DeploymentStatus), default=DeploymentStatus.PENDING)

    # Deployment config
    deployment_type: Mapped[str] = mapped_column(String(50))  # "kserve", "ray"
    model_format: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # "pytorch", "vllm", "triton"

    # Scaling
    replicas: Mapped[int] = mapped_column(Integer, default=1)
    min_replicas: Mapped[int] = mapped_column(Integer, default=0)
    max_replicas: Mapped[int] = mapped_column(Integer, default=3)
    gpu_count: Mapped[int] = mapped_column(Integer, default=1)

    # Endpoint
    endpoint_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    service_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # K8s resources
    k8s_service_name: Mapped[Optional[str]] = mapped_column(String(253), nullable=True)
    k8s_ingress_name: Mapped[Optional[str]] = mapped_column(String(253), nullable=True)

    # Traffic management
    traffic_percentage: Mapped[int] = mapped_column(Integer, default=100)  # 0-100

    # Metrics
    metrics: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON metrics

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    ready_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    project: Mapped["Project"] = relationship("Project", back_populates="deployments")
    model_version: Mapped[Optional["ModelVersion"]] = relationship("ModelVersion", back_populates="deployments")
    agent_revision: Mapped[Optional["AgentRevision"]] = relationship("AgentRevision")


class AgentSpecStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class AgentSpec(Base):
    __tablename__ = "agent_specs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[AgentSpecStatus] = mapped_column(SQLEnum(AgentSpecStatus), default=AgentSpecStatus.DRAFT)

    # Agent definition
    system_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tools: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array of tool definitions
    model_binding: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Which model to use

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project: Mapped["Project"] = relationship("Project", back_populates="agents")
    revisions: Mapped[list["AgentRevision"]] = relationship("AgentRevision", back_populates="agent_spec", cascade="all, delete-orphan")


class AgentRevisionStatus(str, Enum):
    DRAFT = "draft"
    TESTED = "tested"
    APPROVED = "approved"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"


class AgentRevision(Base):
    __tablename__ = "agent_revisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    agent_spec_id: Mapped[str] = mapped_column(String(36), ForeignKey("agent_specs.id"), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    status: Mapped[AgentRevisionStatus] = mapped_column(SQLEnum(AgentRevisionStatus), default=AgentRevisionStatus.DRAFT)

    # Revision content (snapshot)
    system_prompt: Mapped[str] = mapped_column(Text)
    tools: Mapped[str] = mapped_column(Text)  # JSON
    model_binding: Mapped[str] = mapped_column(String(255))
    workflow_definition: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # LangGraph definition

    # Bundle info
    bundle_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Eval results
    eval_score: Mapped[Optional[float]] = mapped_column(nullable=True)
    eval_report: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    agent_spec: Mapped["AgentSpec"] = relationship("AgentSpec", back_populates="revisions")
    runs: Mapped[list["AgentRun"]] = relationship("AgentRun", back_populates="revision", cascade="all, delete-orphan")
    deployments: Mapped[list["Deployment"]] = relationship("Deployment", back_populates="agent_revision")


class AgentRunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_TOOL = "waiting_tool"
    WAITING_HUMAN = "waiting_human"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    ABORTED = "aborted"


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    revision_id: Mapped[str] = mapped_column(String(36), ForeignKey("agent_revisions.id"), index=True)

    status: Mapped[AgentRunStatus] = mapped_column(SQLEnum(AgentRunStatus), default=AgentRunStatus.QUEUED)

    # Input
    input_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON input

    # Execution
    k8s_job_name: Mapped[Optional[str]] = mapped_column(String(253), nullable=True)
    k8s_namespace: Mapped[Optional[str]] = mapped_column(String(253), nullable=True)

    # Output
    output_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON output
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Metrics
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tool_calls: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    revision: Mapped["AgentRevision"] = relationship("AgentRevision", back_populates="runs")
