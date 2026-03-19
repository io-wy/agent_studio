"""Training repositories"""
import uuid
from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import TrainingJob, TrainingJobStatus, Model, ModelStatus, ModelVersion, ModelVersionStatus


class TrainingJobRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        project_id: str,
        name: str,
        base_model: str,
        training_type: str,
        dataset_version_id: Optional[str] = None,
        description: Optional[str] = None,
        config_yaml: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> TrainingJob:
        job = TrainingJob(
            id=str(uuid.uuid4()),
            project_id=project_id,
            name=name,
            description=description,
            base_model=base_model,
            training_type=training_type,
            dataset_version_id=dataset_version_id,
            config_yaml=config_yaml,
            status=TrainingJobStatus.DRAFT,
            created_by=created_by,
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def get(self, job_id: str) -> Optional[TrainingJob]:
        result = await self.db.execute(
            select(TrainingJob).where(TrainingJob.id == job_id)
        )
        return result.scalar_one_or_none()

    async def list_by_project(self, project_id: str, skip: int = 0, limit: int = 100) -> List[TrainingJob]:
        result = await self.db.execute(
            select(TrainingJob)
            .where(TrainingJob.project_id == project_id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update(self, job: TrainingJob, **kwargs) -> TrainingJob:
        for key, value in kwargs.items():
            if value is not None and hasattr(job, key):
                setattr(job, key, value)
        await self.db.commit()
        await self.db.refresh(job)
        return job


class ModelRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        project_id: str,
        name: str,
        base_model: str,
        description: Optional[str] = None,
    ) -> Model:
        model = Model(
            id=str(uuid.uuid4()),
            project_id=project_id,
            name=name,
            description=description,
            base_model=base_model,
            status=ModelStatus.DRAFT,
        )
        self.db.add(model)
        await self.db.commit()
        await self.db.refresh(model)
        return model

    async def get(self, model_id: str) -> Optional[Model]:
        result = await self.db.execute(
            select(Model).where(Model.id == model_id)
        )
        return result.scalar_one_or_none()

    async def list_by_project(self, project_id: str, skip: int = 0, limit: int = 100) -> List[Model]:
        result = await self.db.execute(
            select(Model)
            .where(Model.project_id == project_id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update(self, model: Model, **kwargs) -> Model:
        for key, value in kwargs.items():
            if value is not None and hasattr(model, key):
                setattr(model, key, value)
        await self.db.commit()
        await self.db.refresh(model)
        return model


class ModelVersionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        model_id: str,
        version: str,
        storage_prefix: str,
        training_job_id: Optional[str] = None,
        dataset_version_id: Optional[str] = None,
        mlflow_run_id: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> ModelVersion:
        model_version = ModelVersion(
            id=str(uuid.uuid4()),
            model_id=model_id,
            version=version,
            storage_prefix=storage_prefix,
            training_job_id=training_job_id,
            dataset_version_id=dataset_version_id,
            mlflow_run_id=mlflow_run_id,
            status=ModelVersionStatus.REGISTERED,
            created_by=created_by,
        )
        self.db.add(model_version)
        await self.db.commit()
        await self.db.refresh(model_version)
        return model_version

    async def get(self, version_id: str) -> Optional[ModelVersion]:
        result = await self.db.execute(
            select(ModelVersion).where(ModelVersion.id == version_id)
        )
        return result.scalar_one_or_none()

    async def list_by_model(self, model_id: str) -> List[ModelVersion]:
        result = await self.db.execute(
            select(ModelVersion)
            .where(ModelVersion.model_id == model_id)
            .order_by(ModelVersion.created_at.desc())
        )
        return list(result.scalars().all())

    async def update(self, model_version: ModelVersion, **kwargs) -> ModelVersion:
        for key, value in kwargs.items():
            if value is not None and hasattr(model_version, key):
                setattr(model_version, key, value)
        await self.db.commit()
        await self.db.refresh(model_version)
        return model_version
