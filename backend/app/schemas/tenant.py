"""Tenant and Project schemas"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# Tenant
class TenantBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    quota_gpuHours: int = Field(default=1000, ge=0)
    quota_storage_gb: int = Field(default=100, ge=0)
    quota_deployments: int = Field(default=5, ge=0)


class TenantCreate(TenantBase):
    pass


class TenantUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    quota_gpuHours: Optional[int] = Field(None, ge=0)
    quota_storage_gb: Optional[int] = Field(None, ge=0)
    quota_deployments: Optional[int] = Field(None, ge=0)
    status: Optional[str] = None


class TenantResponse(TenantBase):
    id: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# Project
class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    quota_gpuHours: int = Field(default=100, ge=0)
    quota_storage_gb: int = Field(default=10, ge=0)
    quota_deployments: int = Field(default=2, ge=0)


class ProjectCreate(ProjectBase):
    tenant_id: str


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    quota_gpuHours: Optional[int] = Field(None, ge=0)
    quota_storage_gb: Optional[int] = Field(None, ge=0)
    quota_deployments: Optional[int] = Field(None, ge=0)
    status: Optional[str] = None


class ProjectResponse(ProjectBase):
    id: str
    tenant_id: str
    status: str
    namespace: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# Quota
class QuotaInfo(BaseModel):
    gpu_hours: int
    gpu_hours_used: int
    storage_gb: int
    storage_gb_used: int
    deployments: int
    deployments_used: int


class QuotaUpdate(BaseModel):
    quota_gpuHours: Optional[int] = Field(None, ge=0)
    quota_storage_gb: Optional[int] = Field(None, ge=0)
    quota_deployments: Optional[int] = Field(None, ge=0)
