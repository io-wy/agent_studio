"""Training and Model Registry schemas"""
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


# TrainingJob
class TrainingJobBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class TrainingJobCreate(TrainingJobBase):
    project_id: str
    dataset_version_id: Optional[str] = None
    base_model: str
    training_type: str = Field(..., pattern="^(lora|qlora|full|sft|dpo)$")
    config_yaml: Optional[str] = None


class TrainingJobUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class TrainingJobResponse(TrainingJobBase):
    id: str
    project_id: str
    dataset_version_id: Optional[str]
    model_id: Optional[str]
    status: str
    base_model: str
    training_type: str
    config_yaml: Optional[str]
    k8s_job_name: Optional[str]
    k8s_namespace: Optional[str]
    gpu_hours: Optional[float]
    metrics: Optional[str]
    queued_at: Optional[datetime]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    created_at: datetime
    created_by: Optional[str]

    model_config = {"from_attributes": True}


class TrainingJobCancelRequest(BaseModel):
    reason: Optional[str] = None


# Model
class ModelBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    base_model: str


class ModelCreate(ModelBase):
    project_id: str


class ModelUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class ModelResponse(ModelBase):
    id: str
    project_id: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ModelVersion
class ModelVersionResponse(BaseModel):
    id: str
    model_id: str
    version: str
    status: str
    storage_prefix: str
    mlflow_run_id: Optional[str]
    mlflow_model_uri: Optional[str]
    training_metrics: Optional[str]
    dataset_version_id: Optional[str]
    training_job_id: Optional[str]
    created_at: datetime
    created_by: Optional[str]

    model_config = {"from_attributes": True}


class ModelVersionPromoteRequest(BaseModel):
    target_status: str = Field(..., pattern="^(validated|staged|production|deprecated)$")


class ModelVersionLineageResponse(BaseModel):
    model_version_id: str
    dataset_version: Optional[dict] = None
    training_job: Optional[dict] = None
    parent_model: Optional[dict] = None
