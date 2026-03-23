"""Dataset service - business logic for dataset management"""
import hashlib
import json
import re
import uuid
from typing import Optional, List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Dataset, DatasetVersion, DatasetStatus, DatasetVersionStatus
from app.repositories.dataset import DatasetRepository, DatasetVersionRepository
from app.integrations.object_store import object_store
from app.integrations.lakefs import lakefs_client


class DatasetService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = DatasetRepository(db)
        self.version_repo = DatasetVersionRepository(db)
        self.lakefs = lakefs_client

    async def create_dataset(
        self,
        project_id: str,
        name: str,
        data_format: str,
        description: Optional[str] = None,
        schema: Optional[str] = None,
    ) -> Dataset:
        """Create a new dataset"""
        # Generate storage prefix: projects/{project_id}/datasets/{dataset_name}
        storage_prefix = f"projects/{project_id}/datasets/{name}"

        dataset = await self.repo.create(
            project_id=project_id,
            name=name,
            data_format=data_format,
            storage_prefix=storage_prefix,
            description=description,
            schema=schema,
        )

        return dataset

    async def get_dataset(self, dataset_id: str) -> Optional[Dataset]:
        """Get dataset by ID"""
        return await self.repo.get(dataset_id)

    async def list_datasets(self, project_id: str, skip: int = 0, limit: int = 100) -> List[Dataset]:
        """List datasets in project"""
        return await self.repo.get_by_project(project_id, skip, limit)

    async def upload_file(
        self,
        dataset_id: str,
        file_content: bytes,
        filename: str,
        version: Optional[str] = None,
    ) -> DatasetVersion:
        """Upload file to dataset"""
        dataset = await self.repo.get(dataset_id)
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")

        # Generate version if not provided
        if version is None:
            latest = await self.version_repo.get_latest(dataset_id)
            version = f"v{(int(latest.version.lstrip('v')) + 1) if latest else 1}"

        # Generate storage path: {prefix}/versions/{version}/{filename}
        storage_path = f"{dataset.storage_prefix}/versions/{version}/{filename}"

        # Upload to object store
        result = object_store.upload_file(
            key=storage_path,
            file_data=file_content,
            content_type=self._get_content_type(filename),
        )

        # Create dataset version record
        dataset_version = await self.version_repo.create(
            dataset_id=dataset_id,
            version=version,
            storage_prefix=storage_path,
            description=f"Uploaded {filename}",
        )

        # Update version with file info
        dataset_version = await self.version_repo.update(
            dataset_version,
            file_size_bytes=result["size"],
            checksum=result["checksum"],
            status=DatasetVersionStatus.CREATED,
        )

        return dataset_version

    async def get_presigned_upload_url(
        self,
        dataset_id: str,
        filename: str,
        content_type: str,
        version: Optional[str] = None,
    ) -> Dict[str, str]:
        """Get presigned URL for direct upload"""
        dataset = await self.repo.get(dataset_id)
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")

        # Generate version if not provided
        if version is None:
            latest = await self.version_repo.get_latest(dataset_id)
            version = f"v{(int(latest.version.lstrip('v')) + 1) if latest else 1}"

        storage_path = f"{dataset.storage_prefix}/versions/{version}/{filename}"

        upload_url = object_store.get_presigned_upload_url(storage_path, content_type)

        return {
            "version": version,
            "upload_url": upload_url,
            "storage_path": storage_path,
        }

    async def create_version(
        self,
        dataset_id: str,
        source_version: str,
        new_version: str,
        description: Optional[str] = None,
    ) -> DatasetVersion:
        """Create new version from existing version"""
        dataset = await self.repo.get(dataset_id)
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")

        # Find source version
        source_files = object_store.list_files(
            prefix=f"{dataset.storage_prefix}/versions/{source_version}/"
        )

        if not source_files:
            raise ValueError(f"Source version {source_version} not found")

        # Copy files to new version path
        new_prefix = f"{dataset.storage_prefix}/versions/{new_version}"
        for file_info in source_files:
            old_key = file_info["key"]
            new_key = old_key.replace(f"/versions/{source_version}/", f"/versions/{new_version}/")
            object_store.copy_file(old_key, new_key)

        # Create version record
        dataset_version = await self.version_repo.create(
            dataset_id=dataset_id,
            version=new_version,
            storage_prefix=new_prefix,
            description=description or f"Copied from {source_version}",
        )

        return dataset_version

    async def list_versions(self, dataset_id: str) -> List[DatasetVersion]:
        """List all versions of a dataset"""
        return await self.version_repo.get_by_dataset(dataset_id)

    async def get_version(self, version_id: str) -> Optional[DatasetVersion]:
        """Get specific version"""
        return await self.version_repo.get(version_id)

    async def validate_version(self, version_id: str, rules: Optional[str] = None) -> Dict[str, Any]:
        """Validate dataset version"""
        version = await self.version_repo.get(version_id)
        if not version:
            raise ValueError(f"Version {version_id} not found")

        # Update status to validating
        await self.version_repo.update(version, status=DatasetVersionStatus.VALIDATING)

        errors = []

        # Basic validation: check files exist
        files = object_store.list_files(prefix=version.storage_prefix)
        if not files:
            errors.append("No files found in version")

        # Check file size
        total_size = sum(f["size"] for f in files)
        if total_size == 0:
            errors.append("Files are empty")

        # Validate against schema if provided
        if rules:
            try:
                dataset = await self.repo.get(version.dataset_id)
                if dataset and dataset.schema_:
                    # TODO: Implement schema validation
                    pass
            except Exception as e:
                errors.append(f"Schema validation failed: {str(e)}")

        # Update status based on validation result
        if errors:
            await self.version_repo.update(
                version,
                status=DatasetVersionStatus.FAILED,
                validation_errors=json.dumps(errors),
            )
        else:
            await self.version_repo.update(
                version,
                status=DatasetVersionStatus.VALIDATED,
            )

        return {
            "version_id": version_id,
            "status": version.status.value if hasattr(version.status, 'value') else str(version.status),
            "errors": errors,
            "file_count": len(files),
            "total_size": total_size,
        }

    async def delete_dataset(self, dataset_id: str) -> bool:
        """Delete dataset and all its versions"""
        dataset = await self.repo.get(dataset_id)
        if not dataset:
            return False

        # Delete all files in object store
        files = object_store.list_files(prefix=dataset.storage_prefix)
        for file_info in files:
            object_store.delete_file(file_info["key"])

        # Delete from database (cascade will handle versions)
        await self.repo.delete(dataset)
        return True

    def _get_content_type(self, filename: str) -> str:
        """Get content type from filename"""
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        content_types = {
            "jsonl": "application/jsonl",
            "json": "application/json",
            "parquet": "application/parquet",
            "csv": "text/csv",
            "txt": "text/plain",
        }
        return content_types.get(ext, "application/octet-stream")

    # === lakeFS Operations ===

    def create_lakefs_repo(
        self,
        dataset_id: str,
        project_id: str,
        storage_namespace: str,
    ) -> Dict[str, Any]:
        """Create lakeFS repository for dataset"""
        repo_name = f"dataset-{dataset_id}"
        try:
            return self.lakefs.create_repository(
                name=repo_name,
                storage_namespace=storage_namespace,
                description=f"Dataset {dataset_id}",
            )
        except Exception as e:
            # Repository might already exist
            return {"name": repo_name, "error": str(e)}

    def create_dataset_branch(
        self,
        dataset_id: str,
        version: str,
        source_branch: str = "main",
    ) -> Dict[str, Any]:
        """Create a branch for dataset version"""
        repo_name = f"dataset-{dataset_id}"
        branch_name = f"v{version}"
        try:
            return self.lakefs.create_branch(repo_name, branch_name, source_branch)
        except Exception as e:
            return {"error": str(e)}

    def upload_to_lakefs(
        self,
        dataset_id: str,
        version: str,
        path: str,
        content: bytes,
    ) -> Dict[str, Any]:
        """Upload file to lakeFS branch"""
        repo_name = f"dataset-{dataset_id}"
        branch_name = f"v{version}"
        try:
            return self.lakefs.upload_file(repo_name, branch_name, path, content)
        except Exception as e:
            return {"error": str(e)}

    def commit_lakefs_version(
        self,
        dataset_id: str,
        version: str,
        message: str,
    ) -> Dict[str, Any]:
        """Commit changes to lakeFS branch"""
        repo_name = f"dataset-{dataset_id}"
        branch_name = f"v{version}"
        try:
            return self.lakefs.commit(repo_name, branch_name, message)
        except Exception as e:
            return {"error": str(e)}

    def create_lakefs_tag(
        self,
        dataset_id: str,
        version: str,
        tag_name: str,
    ) -> Dict[str, Any]:
        """Create tag for dataset version"""
        repo_name = f"dataset-{dataset_id}"
        # Get latest commit
        commits = self.lakefs.log_commits(repo_name, f"v{version}", limit=1)
        if not commits:
            return {"error": "No commits found"}
        commit_id = commits[0]["id"]
        try:
            return self.lakefs.create_tag(repo_name, tag_name, commit_id)
        except Exception as e:
            return {"error": str(e)}

    def list_lakefs_files(
        self,
        dataset_id: str,
        version: str,
        path: str = "",
    ) -> List[Dict[str, Any]]:
        """List files in lakeFS branch"""
        repo_name = f"dataset-{dataset_id}"
        branch_name = f"v{version}"
        try:
            return self.lakefs.list_files(repo_name, branch_name, path)
        except Exception:
            return []
