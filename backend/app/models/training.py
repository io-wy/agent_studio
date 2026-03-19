"""Training and Model Registry models"""
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Float
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TrainingJobStatus(str, Enum):
    DRAFT = "draft"
    QUEUED = "queued"
    ADMITTED = "admitted"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


class TrainingJob(Base):
    __tablename__ = "training_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True)
    dataset_version_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("dataset_versions.id"), nullable=True)
    model_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("models.id"), nullable=True)

    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[TrainingJobStatus] = mapped_column(SQLEnum(TrainingJobStatus), default=TrainingJobStatus.DRAFT)

    # Training config
    base_model: Mapped[str] = mapped_column(String(255))  # e.g., "meta-llama/Llama-3-8b"
    training_type: Mapped[str] = mapped_column(String(50))  # "lora", "qlora", "full"
    config_yaml: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Axolotl config

    # K8s job tracking
    k8s_job_name: Mapped[Optional[str]] = mapped_column(String(253), nullable=True)
    k8s_namespace: Mapped[Optional[str]] = mapped_column(String(253), nullable=True)

    # Metrics
    gpu_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    metrics: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON metrics

    # Timestamps
    queued_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    project: Mapped["Project"] = relationship("Project", back_populates="training_jobs")
    dataset_version: Mapped[Optional["DatasetVersion"]] = relationship("DatasetVersion")
    model: Mapped[Optional["Model"]] = relationship("Model")
    model_version: Mapped[Optional["ModelVersion"]] = relationship("ModelVersion", back_populates="training_job")


class ModelStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class Model(Base):
    __tablename__ = "models"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[ModelStatus] = mapped_column(SQLEnum(ModelStatus), default=ModelStatus.DRAFT)
    base_model: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project: Mapped["Project"] = relationship("Project", back_populates="models")
    versions: Mapped[list["ModelVersion"]] = relationship("ModelVersion", back_populates="model", cascade="all, delete-orphan")


class ModelVersionStatus(str, Enum):
    REGISTERED = "registered"
    VALIDATED = "validated"
    STAGED = "staged"
    PRODUCTION = "production"
    DEPRECATED = "deprecated"


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    model_id: Mapped[str] = mapped_column(String(36), ForeignKey("models.id"), index=True)
    version: Mapped[str] = mapped_column(String(50))  # e.g., "v1", "1"
    status: Mapped[ModelVersionStatus] = mapped_column(SQLEnum(ModelVersionStatus), default=ModelVersionStatus.REGISTERED)

    # Artifacts
    storage_prefix: Mapped[str] = mapped_column(String(500))  # S3 prefix
    mlflow_run_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    mlflow_model_uri: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Metrics
    training_metrics: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON

    # Lineage
    dataset_version_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("dataset_versions.id"), nullable=True)
    training_job_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("training_jobs.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    model: Mapped["Model"] = relationship("Model", back_populates="versions")
    training_job: Mapped[Optional["TrainingJob"]] = relationship("TrainingJob", back_populates="model_version")
    dataset_version: Mapped[Optional["DatasetVersion"]] = relationship("DatasetVersion")
    deployments: Mapped[list["Deployment"]] = relationship("Deployment", back_populates="model_version")
