"""Core models: Tenant, Project, User, etc."""
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TenantStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    status: Mapped[TenantStatus] = mapped_column(SQLEnum(TenantStatus), default=TenantStatus.ACTIVE)
    quota_gpuHours: Mapped[int] = mapped_column(default=1000)  # GPU hours quota
    quota_storage_gb: Mapped[int] = mapped_column(default=100)  # Storage in GB
    quota_deployments: Mapped[int] = mapped_column(default=5)  # Max concurrent deployments
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    projects: Mapped[list["Project"]] = relationship("Project", back_populates="tenant", cascade="all, delete-orphan")


class ProjectStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(SQLEnum(ProjectStatus), default=ProjectStatus.ACTIVE)
    namespace: Mapped[str] = mapped_column(String(253), unique=True)  # K8s namespace
    quota_gpuHours: Mapped[int] = mapped_column(default=100)  # Project-level GPU hours
    quota_storage_gb: Mapped[int] = mapped_column(default=10)
    quota_deployments: Mapped[int] = mapped_column(default=2)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="projects")
    datasets: Mapped[list["Dataset"]] = relationship("Dataset", back_populates="project", cascade="all, delete-orphan")
    models: Mapped[list["Model"]] = relationship("Model", back_populates="project", cascade="all, delete-orphan")
    agents: Mapped[list["AgentSpec"]] = relationship("AgentSpec", back_populates="project", cascade="all, delete-orphan")
    training_jobs: Mapped[list["TrainingJob"]] = relationship("TrainingJob", back_populates="project", cascade="all, delete-orphan")
    deployments: Mapped[list["Deployment"]] = relationship("Deployment", back_populates="project", cascade="all, delete-orphan")
