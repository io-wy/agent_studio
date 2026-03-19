"""Dataset schemas"""
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


# Dataset
class DatasetBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    data_format: str = Field(..., pattern="^(jsonl|parquet|csv|text|json)$")
    schema_: Optional[str] = None


class DatasetCreate(DatasetBase):
    project_id: str


class DatasetUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = None


class DatasetResponse(DatasetBase):
    id: str
    project_id: str
    status: str
    storage_prefix: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# DatasetVersion
class DatasetVersionBase(BaseModel):
    description: Optional[str] = None


class DatasetVersionCreate(DatasetVersionBase):
    dataset_id: str


class DatasetVersionUpdate(BaseModel):
    description: Optional[str] = None
    status: Optional[str] = None


class DatasetVersionResponse(DatasetVersionBase):
    id: str
    dataset_id: str
    version: str
    status: str
    storage_prefix: str
    row_count: Optional[int]
    file_size_bytes: Optional[int]
    checksum: Optional[str]
    lakefs_commit: Optional[str]
    validation_errors: Optional[str]
    created_at: datetime
    created_by: Optional[str]

    model_config = {"from_attributes": True}


# Dataset import
class DatasetImportRequest(BaseModel):
    source_uri: str = Field(..., description="S3 URI or local path to import")
    import_mode: str = Field(default="copy", pattern="^(copy|link|move)$")


class DatasetValidateRequest(BaseModel):
    validation_rules: Optional[str] = None  # JSON schema or validation config


class DatasetSplitRequest(BaseModel):
    train_ratio: float = Field(default=0.8, ge=0.0, le=1.0)
    val_ratio: float = Field(default=0.1, ge=0.0, le=1.0)
    test_ratio: float = Field(default=0.1, ge=0.0, le=1.0)
    split_method: str = Field(default="random", pattern="^(random|sequential|stratified)$")
