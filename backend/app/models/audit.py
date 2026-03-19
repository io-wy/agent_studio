"""Audit, Operation, and Event models"""
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Actor
    actor_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    actor_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # "user", "system", "service"

    # Resource
    tenant_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    project_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    resource_type: Mapped[str] = mapped_column(String(50))  # "tenant", "project", "dataset", "training_job", etc.
    resource_id: Mapped[str] = mapped_column(String(36))

    # Action
    action: Mapped[str] = mapped_column(String(100))  # "create", "update", "delete", "deploy", etc.
    before_state: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)
    after_state: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)

    # Request context
    request_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)  # IPv6 compatible
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Additional
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class OperationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


class Operation(Base):
    __tablename__ = "operations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Operation info
    name: Mapped[str] = mapped_column(String(255))
    operation_type: Mapped[str] = mapped_column(String(50))  # "training", "deployment", "evaluation", "publish"
    status: Mapped[OperationStatus] = mapped_column(SQLEnum(OperationStatus), default=OperationStatus.PENDING)

    # Resource reference
    resource_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    # Request/Response
    request: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)
    response: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)

    # Progress
    progress: Mapped[int] = mapped_column(Integer, default=0)  # 0-100
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Creator
    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)


class Event(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Event info
    event_type: Mapped[str] = mapped_column(String(100))  # "training_job.status_changed", "deployment.ready", etc.
    tenant_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    project_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    resource_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    # Payload
    payload: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
