"""Dataset models: Dataset, DatasetVersion"""
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DatasetStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[DatasetStatus] = mapped_column(SQLEnum(DatasetStatus), default=DatasetStatus.DRAFT)
    data_format: Mapped[str] = mapped_column(String(50))  # jsonl, parquet, csv, etc.
    schema_: Mapped[Optional[str]] = mapped_column("schema", Text, nullable=True)  # JSON schema
    storage_prefix: Mapped[str] = mapped_column(String(500))  # S3 prefix
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project: Mapped["Project"] = relationship("Project", back_populates="datasets")
    versions: Mapped[list["DatasetVersion"]] = relationship(
        "DatasetVersion", back_populates="dataset", cascade="all, delete-orphan"
    )


class DatasetVersionStatus(str, Enum):
    CREATED = "created"
    VALIDATING = "validating"
    VALIDATED = "validated"
    FAILED = "failed"


class DatasetVersion(Base):
    __tablename__ = "dataset_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(String(36), ForeignKey("datasets.id"), index=True)
    version: Mapped[int] = mapped_column(String(50))  # e.g., "v1", "v2", or "1", "2"
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[DatasetVersionStatus] = mapped_column(SQLEnum(DatasetVersionStatus), default=DatasetVersionStatus.CREATED)
    storage_prefix: Mapped[str] = mapped_column(String(500))  # S3 prefix for this version
    row_count: Mapped[Optional[int]] = mapped_column(nullable=True)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(nullable=True)
    checksum: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # SHA256
    lakefs_commit: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # lakeFS commit hash
    validation_errors: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON errors
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    dataset: Mapped["Dataset"] = relationship("Dataset", back_populates="versions")
