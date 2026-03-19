"""Dataset repositories"""
import uuid
from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Dataset, DatasetVersion, DatasetStatus, DatasetVersionStatus


class DatasetRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        project_id: str,
        name: str,
        data_format: str,
        storage_prefix: str,
        description: Optional[str] = None,
        schema: Optional[str] = None,
    ) -> Dataset:
        dataset = Dataset(
            id=str(uuid.uuid4()),
            project_id=project_id,
            name=name,
            description=description,
            data_format=data_format,
            schema_=schema,
            storage_prefix=storage_prefix,
            status=DatasetStatus.DRAFT,
        )
        self.db.add(dataset)
        await self.db.commit()
        await self.db.refresh(dataset)
        return dataset

    async def get(self, dataset_id: str) -> Optional[Dataset]:
        result = await self.db.execute(
            select(Dataset).where(Dataset.id == dataset_id)
        )
        return result.scalar_one_or_none()

    async def get_by_project(self, project_id: str, skip: int = 0, limit: int = 100) -> List[Dataset]:
        result = await self.db.execute(
            select(Dataset)
            .where(Dataset.project_id == project_id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update(self, dataset: Dataset, **kwargs) -> Dataset:
        for key, value in kwargs.items():
            if value is not None and hasattr(dataset, key):
                setattr(dataset, key, value)
        await self.db.commit()
        await self.db.refresh(dataset)
        return dataset

    async def delete(self, dataset: Dataset) -> None:
        await self.db.delete(dataset)
        await self.db.commit()


class DatasetVersionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        dataset_id: str,
        version: str,
        storage_prefix: str,
        description: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> DatasetVersion:
        dataset_version = DatasetVersion(
            id=str(uuid.uuid4()),
            dataset_id=dataset_id,
            version=version,
            description=description,
            storage_prefix=storage_prefix,
            status=DatasetVersionStatus.CREATED,
            created_by=created_by,
        )
        self.db.add(dataset_version)
        await self.db.commit()
        await self.db.refresh(dataset_version)
        return dataset_version

    async def get(self, version_id: str) -> Optional[DatasetVersion]:
        result = await self.db.execute(
            select(DatasetVersion).where(DatasetVersion.id == version_id)
        )
        return result.scalar_one_or_none()

    async def get_by_dataset(self, dataset_id: str) -> List[DatasetVersion]:
        result = await self.db.execute(
            select(DatasetVersion)
            .where(DatasetVersion.dataset_id == dataset_id)
            .order_by(DatasetVersion.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_latest(self, dataset_id: str) -> Optional[DatasetVersion]:
        result = await self.db.execute(
            select(DatasetVersion)
            .where(DatasetVersion.dataset_id == dataset_id)
            .order_by(DatasetVersion.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def update(self, dataset_version: DatasetVersion, **kwargs) -> DatasetVersion:
        for key, value in kwargs.items():
            if value is not None and hasattr(dataset_version, key):
                setattr(dataset_version, key, value)
        await self.db.commit()
        await self.db.refresh(dataset_version)
        return dataset_version
